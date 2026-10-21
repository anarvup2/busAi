#!/usr/bin/env python3
"""Verify documented HX-CCD22 APIs and generate an evidence report.

This script intentionally separates three kinds of endpoints:

1. Receiver endpoints hosted by our own prototype server.
2. Camera push endpoints, which the camera normally calls on our receiver.
3. Private same-LAN camera web APIs used only for lab diagnostics.

By default the script does not call any reset endpoint. Use --allow-reset only
when clearing the camera's internal totals is acceptable.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


DEFAULT_SIGN_SECRET = "1096931dc28e4ecc9ddcb14e8760d53c"
MAX_BODY_BYTES = 2_000_000

RECEIVER_GET_ENDPOINTS = [
    "/health",
    "/api/config",
    "/api/status/current",
    "/api/dashboard",
    "/api/debug/report",
    "/api/debug/requests",
    "/api/debug/uploads",
    "/api/debug/events",
    "/api/debug/fields",
    "/api/debug/child-mode",
]

DASHBOARD_GET_ENDPOINTS = [
    "/health",
    "/api/camera-total",
    "/api/dashboard/fleet",
    "/api/dashboard/buses/B-101",
    "/api/dashboard/export.csv",
]

PRIVATE_CAMERA_ENDPOINTS = [
    {
        "name": "camera_display_data_get",
        "method": "POST",
        "path": "/api/passengerFlow/passengerFlowData/DisplayDataGet",
        "json_body": {},
        "needs_sign": True,
        "classification": "lab-only/private diagnostic",
    },
    {
        "name": "camera_webrtc_probe",
        "method": "GET",
        "path": "/media/webrtc?app=live&stream=camera&type=play",
        "classification": "lab-only/private diagnostic",
    },
    {
        "name": "camera_rtc_client_js",
        "method": "GET",
        "path": "/js/rtcClient.js",
        "classification": "lab-only/private diagnostic",
    },
]

RESET_ENDPOINT = {
    "name": "camera_private_reset",
    "method": "POST",
    "path": "/api/passengerFlow/deviceManage/passengerFlowDataReset",
    "json_body": {},
    "needs_sign": True,
    "classification": "lab-only/private reset control",
}

DOCUMENTED_FIELD_GROUPS: dict[str, set[str]] = {
    "heartbeat_push_payload": {
        "sn",
        "time",
        "hostName",
        "macAddress",
        "hwPlatform",
        "swRelease",
        "connectionType",
        "ipAddress",
        "ipAddressMethod",
        "timeZone",
    },
    "data_upload_payload": {
        "sn",
        "startTime",
        "endTime",
        "time",
        "in",
        "out",
        "passby",
        "turnback",
        "avgStayTime",
        "len",
        "inAdult",
        "outAdult",
        "inChild",
        "outChild",
        "passbyAdult",
        "passbyChild",
        "turnbackAdult",
        "turnbackChild",
        "total",
        "attributes",
        "eventList",
    },
    "attributes_payload": {
        "eventType",
        "height",
        "idIndex",
        "lineId",
        "personId",
        "stayTime",
        "timeStamp",
    },
    "event_list_payload": {
        "id",
        "timestamp",
        "eventType",
        "height",
        "stayTime",
    },
    "private_display_response": {
        "age",
        "enter",
        "gender",
        "leave",
        "pass",
        "result",
        "return",
        "stay",
        "stayTimePerPerson",
        "workcard",
    },
    "vendor_documented_unobserved_payloads": {
        "currentStay",
        "info",
        "info.id",
        "info.height",
        "info.status",
        "info.staytime",
        "data",
        "data.time",
        "data.startTime",
        "data.endTime",
        "data.in",
        "data.out",
        "data.passby",
        "data.turnback",
        "data.avgStayTime",
    },
}

SENSITIVE_KEY_RE = re.compile(
    r"(sn|serial|mac|ipaddress|ip_address|sign|signature|key|token|secret)",
    re.IGNORECASE,
)
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
MAC_RE = re.compile(r"\b[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\b")
LONG_DIGIT_RE = re.compile(r"\b\d{14,}\b")


@dataclass
class EndpointResult:
    name: str
    classification: str
    method: str
    url: str
    status: int | None
    ok: bool
    elapsed_ms: int
    content_type: str | None = None
    body_kind: str = "none"
    json_keys: list[str] = field(default_factory=list)
    saved_response: str | None = None
    error: str | None = None
    note: str | None = None


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def unix_now() -> int:
    return int(time.time())


def normalize_base(url: str) -> str:
    return url.rstrip("/") + "/"


def full_url(base: str, path: str) -> str:
    return urljoin(normalize_base(base), path.lstrip("/"))


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned.strip("_") or "response"


def redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key, item in value.items():
            if SENSITIVE_KEY_RE.search(str(key)):
                output[key] = "<redacted>"
            else:
                output[key] = redact_value(item)
        return output
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, str):
        value = MAC_RE.sub("<redacted-mac>", value)
        value = IP_RE.sub("<redacted-ip>", value)
        value = LONG_DIGIT_RE.sub("<redacted-id>", value)
    return value


def redact_text(value: str) -> str:
    value = MAC_RE.sub("<redacted-mac>", value)
    value = IP_RE.sub("<redacted-ip>", value)
    value = LONG_DIGIT_RE.sub("<redacted-id>", value)
    return value


def response_json_keys(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        return sorted(str(key) for key in payload.keys())
    return []


def write_response_file(
    out_dir: Path,
    name: str,
    payload: Any,
    body_kind: str,
    redact: bool,
) -> str:
    responses_dir = out_dir / "responses"
    responses_dir.mkdir(parents=True, exist_ok=True)

    if body_kind == "json":
        data = redact_value(payload) if redact else payload
        path = responses_dir / f"{safe_name(name)}.json"
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        return str(path.relative_to(out_dir))

    if body_kind == "text":
        text = payload.decode("utf-8", errors="replace")
        if redact:
            text = redact_text(text)
        path = responses_dir / f"{safe_name(name)}.txt"
        path.write_text(text)
        return str(path.relative_to(out_dir))

    encoded = base64.b64encode(payload).decode("ascii")
    path = responses_dir / f"{safe_name(name)}.b64.txt"
    path.write_text(encoded)
    return str(path.relative_to(out_dir))


def parse_body(body: bytes, content_type: str | None) -> tuple[str, Any, list[str]]:
    lower_type = (content_type or "").lower()
    text = body.decode("utf-8", errors="replace")
    if "json" in lower_type or text.strip().startswith(("{", "[")):
        try:
            payload = json.loads(text)
            return "json", payload, response_json_keys(payload)
        except json.JSONDecodeError:
            pass
    if "text" in lower_type or "javascript" in lower_type or "html" in lower_type:
        return "text", body, []
    return "binary", body, []


def request_endpoint(
    *,
    name: str,
    classification: str,
    method: str,
    url: str,
    out_dir: Path,
    redact: bool,
    timeout: float,
    json_body: Any | None = None,
    headers: dict[str, str] | None = None,
    note: str | None = None,
) -> tuple[EndpointResult, Any | None]:
    request_headers = dict(headers or {})
    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
        request_headers.setdefault("Accept", "application/json")

    started = time.monotonic()
    status: int | None = None
    content_type: str | None = None
    raw_body = b""
    try:
        request = Request(url, data=data, method=method, headers=request_headers)
        with urlopen(request, timeout=timeout) as response:
            status = int(response.status)
            content_type = response.headers.get("Content-Type")
            raw_body = response.read(MAX_BODY_BYTES)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        body_kind, payload, keys = parse_body(raw_body, content_type)
        saved = write_response_file(out_dir, name, payload, body_kind, redact)
        return (
            EndpointResult(
                name=name,
                classification=classification,
                method=method,
                url=redact_text(url) if redact else url,
                status=status,
                ok=200 <= status < 300,
                elapsed_ms=elapsed_ms,
                content_type=content_type,
                body_kind=body_kind,
                json_keys=keys,
                saved_response=saved,
                note=note,
            ),
            payload if body_kind == "json" else None,
        )
    except HTTPError as error:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        status = int(error.code)
        content_type = error.headers.get("Content-Type")
        raw_body = error.read(MAX_BODY_BYTES)
        body_kind, payload, keys = parse_body(raw_body, content_type)
        saved = write_response_file(out_dir, name, payload, body_kind, redact)
        return (
            EndpointResult(
                name=name,
                classification=classification,
                method=method,
                url=redact_text(url) if redact else url,
                status=status,
                ok=False,
                elapsed_ms=elapsed_ms,
                content_type=content_type,
                body_kind=body_kind,
                json_keys=keys,
                saved_response=saved,
                error=f"HTTP {error.code}: {error.reason}",
                note=note,
            ),
            payload if body_kind == "json" else None,
        )
    except (OSError, URLError, TimeoutError) as error:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        return (
            EndpointResult(
                name=name,
                classification=classification,
                method=method,
                url=redact_text(url) if redact else url,
                status=None,
                ok=False,
                elapsed_ms=elapsed_ms,
                error=str(error),
                note=note,
            ),
            None,
        )


def synthetic_heartbeat_payload(sn: str) -> dict[str, Any]:
    return {"sn": sn, "time": unix_now()}


def synthetic_upload_payload(sn: str) -> dict[str, Any]:
    now = unix_now()
    return {
        "sn": sn,
        "startTime": now - 60,
        "endTime": now,
        "time": now,
        "in": 0,
        "out": 0,
        "passby": 0,
        "turnback": 0,
        "avgStayTime": 0,
        "len": 0,
    }


def extract_observed_fields(payload: Any) -> dict[str, set[str]]:
    result = {
        "heartbeat_push_payload": set(),
        "data_upload_payload": set(),
        "attributes_payload": set(),
        "event_list_payload": set(),
    }
    if not isinstance(payload, dict):
        return result

    by_endpoint = payload.get("by_endpoint")
    if isinstance(by_endpoint, dict):
        heartbeat = by_endpoint.get("/api/camera/heartBeat")
        upload = by_endpoint.get("/api/camera/dataUpload")
        if isinstance(heartbeat, list):
            result["heartbeat_push_payload"].update(str(item) for item in heartbeat)
        if isinstance(upload, list):
            result["data_upload_payload"].update(str(item) for item in upload)

    upload_records = payload.get("upload_records")
    if isinstance(upload_records, list):
        result["data_upload_payload"].update(str(item) for item in upload_records)

    attributes = payload.get("attributes")
    if isinstance(attributes, list):
        result["attributes_payload"].update(str(item) for item in attributes)

    event_list = payload.get("eventList")
    if isinstance(event_list, list):
        result["event_list_payload"].update(str(item) for item in event_list)

    return result


def classify_fields(
    observed_from_receiver: dict[str, set[str]],
    private_display_keys: set[str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for group, fields in DOCUMENTED_FIELD_GROUPS.items():
        for field_name in sorted(fields):
            if group == "private_display_response":
                status = (
                    "verified live"
                    if field_name in private_display_keys
                    else "lab-only/private; not observed in this run"
                )
            elif group == "vendor_documented_unobserved_payloads":
                status = "official vendor-documented but unobserved in this run"
            else:
                observed = field_name in observed_from_receiver.get(group, set())
                status = "observed in receiver payloads" if observed else "not observed in this run"
            rows.append({"group": group, "field": field_name, "status": status})
    return rows


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    output = ["| " + " | ".join(headers) + " |"]
    output.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        output.append("| " + " | ".join(str(item).replace("\n", " ") for item in row) + " |")
    return "\n".join(output)


def write_markdown_report(
    out_dir: Path,
    *,
    args: argparse.Namespace,
    endpoint_results: list[EndpointResult],
    field_rows: list[dict[str, str]],
    observation_summary: dict[str, Any],
) -> None:
    def display_value(value: Any) -> Any:
        if args.redact and isinstance(value, str):
            return redact_text(value)
        return value

    endpoint_rows = [
        [
            result.name,
            result.classification,
            result.method,
            result.status if result.status is not None else "no response",
            "yes" if result.ok else "no",
            result.elapsed_ms,
            result.body_kind,
            ", ".join(result.json_keys),
            result.saved_response or "",
            result.error or "",
        ]
        for result in endpoint_results
    ]
    field_table_rows = [
        [row["group"], row["field"], row["status"]] for row in field_rows
    ]

    content = [
        "# HX-CCD22 API Verification Report",
        "",
        f"Generated UTC: `{datetime.now(timezone.utc).isoformat(timespec='seconds')}`",
        "",
        "## Inputs",
        "",
        markdown_table(
            ["Setting", "Value"],
            [
                ["camera_base", display_value(args.camera_base)],
                ["receiver_base", display_value(args.receiver_base)],
                ["dashboard_base", display_value(args.dashboard_base)],
                ["observe_seconds", args.observe_seconds],
                ["include_private_camera_apis", args.include_private_camera_apis],
                ["allow_reset", args.allow_reset],
                ["redact", args.redact],
            ],
        ),
        "",
        "## Endpoint Results",
        "",
        markdown_table(
            [
                "Name",
                "Classification",
                "Method",
                "Status",
                "OK",
                "ms",
                "Body",
                "JSON keys",
                "Saved response",
                "Error",
            ],
            endpoint_rows,
        ),
        "",
        "## Field Verification",
        "",
        markdown_table(["Group", "Field", "Status"], field_table_rows),
        "",
        "## Observation Summary",
        "",
        "```json",
        json.dumps(redact_value(observation_summary), indent=2, sort_keys=True),
        "```",
        "",
        "## Notes",
        "",
        "- `/api/camera/heartBeat` and `/api/camera/dataUpload` are receiver endpoints. The camera normally calls these endpoints; this script can also send synthetic zero-count contract payloads to verify receiver behavior.",
        "- Private camera APIs require same-LAN camera access and are not production ingestion APIs.",
        "- Reset is skipped unless `--allow-reset` is provided.",
        "- A failed endpoint is still evidence: it should be documented as unavailable or unverified for that run.",
        "",
    ]
    (out_dir / "verification_report.md").write_text("\n".join(content))


def write_json_report(
    out_dir: Path,
    *,
    args: argparse.Namespace,
    endpoint_results: list[EndpointResult],
    field_rows: list[dict[str, str]],
    observation_summary: dict[str, Any],
) -> None:
    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "inputs": {
            "camera_base": redact_text(args.camera_base) if args.redact else args.camera_base,
            "receiver_base": redact_text(args.receiver_base)
            if args.redact
            else args.receiver_base,
            "dashboard_base": redact_text(args.dashboard_base)
            if args.redact
            else args.dashboard_base,
            "observe_seconds": args.observe_seconds,
            "include_private_camera_apis": args.include_private_camera_apis,
            "allow_reset": args.allow_reset,
            "redact": args.redact,
        },
        "endpoint_results": [asdict(result) for result in endpoint_results],
        "field_verification": field_rows,
        "observation_summary": redact_value(observation_summary)
        if args.redact
        else observation_summary,
    }
    (out_dir / "verification_report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )


def run_verification(args: argparse.Namespace) -> Path:
    out_dir = Path(args.output_dir) / utc_stamp()
    out_dir.mkdir(parents=True, exist_ok=True)

    endpoint_results: list[EndpointResult] = []
    json_payloads: dict[str, Any] = {}

    for path in RECEIVER_GET_ENDPOINTS:
        name = "receiver_" + safe_name(path)
        result, payload = request_endpoint(
            name=name,
            classification="receiver prototype/debug",
            method="GET",
            url=full_url(args.receiver_base, path),
            out_dir=out_dir,
            redact=args.redact,
            timeout=args.timeout,
        )
        endpoint_results.append(result)
        if payload is not None:
            json_payloads[name] = payload

    if not args.skip_synthetic_post:
        sn = args.synthetic_sn
        synthetic_calls = [
            (
                "receiver_synthetic_heartbeat",
                "/api/camera/heartBeat",
                synthetic_heartbeat_payload(sn),
                "synthetic receiver contract test; creates/updates a test heartbeat row",
            ),
            (
                "receiver_synthetic_data_upload",
                "/api/camera/dataUpload",
                synthetic_upload_payload(sn),
                "synthetic receiver contract test; sends zero counts to avoid changing totals",
            ),
        ]
        for name, path, body, note in synthetic_calls:
            result, payload = request_endpoint(
                name=name,
                classification="receiver camera-push contract",
                method="POST",
                url=full_url(args.receiver_base, path),
                out_dir=out_dir,
                redact=args.redact,
                timeout=args.timeout,
                json_body=body,
                note=note,
            )
            endpoint_results.append(result)
            if payload is not None:
                json_payloads[name] = payload

    for path in DASHBOARD_GET_ENDPOINTS:
        name = "dashboard_" + safe_name(path)
        result, payload = request_endpoint(
            name=name,
            classification="dashboard mirror/prototype",
            method="GET",
            url=full_url(args.dashboard_base, path),
            out_dir=out_dir,
            redact=args.redact,
            timeout=args.timeout,
        )
        endpoint_results.append(result)
        if payload is not None:
            json_payloads[name] = payload

    private_display_keys: set[str] = set()
    if args.include_private_camera_apis:
        display_sign = hashlib.md5(args.sign_secret.encode()).hexdigest().upper()
        for spec in PRIVATE_CAMERA_ENDPOINTS:
            headers = {}
            if spec.get("needs_sign"):
                headers["Sign"] = display_sign
            result, payload = request_endpoint(
                name=str(spec["name"]),
                classification=str(spec["classification"]),
                method=str(spec["method"]),
                url=full_url(args.camera_base, str(spec["path"])),
                out_dir=out_dir,
                redact=args.redact,
                timeout=args.timeout,
                json_body=spec.get("json_body"),
                headers=headers,
            )
            endpoint_results.append(result)
            if payload is not None:
                json_payloads[str(spec["name"])] = payload
                if spec["name"] == "camera_display_data_get":
                    private_display_keys.update(response_json_keys(payload))

        if args.allow_reset:
            result, payload = request_endpoint(
                name=str(RESET_ENDPOINT["name"]),
                classification=str(RESET_ENDPOINT["classification"]),
                method=str(RESET_ENDPOINT["method"]),
                url=full_url(args.camera_base, str(RESET_ENDPOINT["path"])),
                out_dir=out_dir,
                redact=args.redact,
                timeout=args.timeout,
                json_body=RESET_ENDPOINT.get("json_body"),
                headers={"Sign": display_sign},
                note="destructive: resets camera website totals",
            )
            endpoint_results.append(result)
            if payload is not None:
                json_payloads[str(RESET_ENDPOINT["name"])] = payload
        else:
            endpoint_results.append(
                EndpointResult(
                    name=str(RESET_ENDPOINT["name"]),
                    classification=str(RESET_ENDPOINT["classification"]),
                    method=str(RESET_ENDPOINT["method"]),
                    url=redact_text(full_url(args.camera_base, str(RESET_ENDPOINT["path"])))
                    if args.redact
                    else full_url(args.camera_base, str(RESET_ENDPOINT["path"])),
                    status=None,
                    ok=False,
                    elapsed_ms=0,
                    body_kind="skipped",
                    note="skipped because --allow-reset was not provided",
                )
            )

    observation_summary: dict[str, Any] = {
        "observe_seconds": args.observe_seconds,
        "ran": args.observe_seconds > 0,
    }
    if args.observe_seconds > 0:
        before_result, before_payload = request_endpoint(
            name="observation_before_fields",
            classification="receiver observation",
            method="GET",
            url=full_url(args.receiver_base, "/api/debug/fields"),
            out_dir=out_dir,
            redact=args.redact,
            timeout=args.timeout,
        )
        endpoint_results.append(before_result)
        time.sleep(args.observe_seconds)
        after_result, after_payload = request_endpoint(
            name="observation_after_fields",
            classification="receiver observation",
            method="GET",
            url=full_url(args.receiver_base, "/api/debug/fields"),
            out_dir=out_dir,
            redact=args.redact,
            timeout=args.timeout,
        )
        endpoint_results.append(after_result)
        latest_result, latest_payload = request_endpoint(
            name="observation_after_recent_requests",
            classification="receiver observation",
            method="GET",
            url=full_url(args.receiver_base, "/api/debug/requests"),
            out_dir=out_dir,
            redact=args.redact,
            timeout=args.timeout,
        )
        endpoint_results.append(latest_result)
        if after_payload is not None:
            json_payloads["observation_after_fields"] = after_payload
        observation_summary.update(
            {
                "before_fields_available": before_payload is not None,
                "after_fields_available": after_payload is not None,
                "recent_requests_available": latest_payload is not None,
                "before_keys": response_json_keys(before_payload),
                "after_keys": response_json_keys(after_payload),
            }
        )

    fields_payload = (
        json_payloads.get("receiver_api_debug_fields")
        or json_payloads.get("observation_after_fields")
    )
    observed_from_receiver = extract_observed_fields(fields_payload)
    field_rows = classify_fields(observed_from_receiver, private_display_keys)

    write_json_report(
        out_dir,
        args=args,
        endpoint_results=endpoint_results,
        field_rows=field_rows,
        observation_summary=observation_summary,
    )
    write_markdown_report(
        out_dir,
        args=args,
        endpoint_results=endpoint_results,
        field_rows=field_rows,
        observation_summary=observation_summary,
    )
    return out_dir


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify HX-CCD22 documented APIs and generate an evidence report."
    )
    parser.add_argument("--camera-base", default="http://172.16.17.50")
    parser.add_argument("--receiver-base", default="http://172.16.16.118:8088")
    parser.add_argument("--dashboard-base", default="http://172.16.16.118:8089")
    parser.add_argument("--observe-seconds", type=int, default=120)
    parser.add_argument("--include-private-camera-apis", action="store_true")
    parser.add_argument("--allow-reset", action="store_true")
    parser.add_argument("--redact", dest="redact", action="store_true", default=True)
    parser.add_argument("--no-redact", dest="redact", action="store_false")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument(
        "--output-dir",
        default="reports/hx_ccd22_api_verification",
        help="Base directory for timestamped verification reports.",
    )
    parser.add_argument(
        "--skip-synthetic-post",
        action="store_true",
        help="Do not send synthetic heartbeat/dataUpload payloads to the receiver.",
    )
    parser.add_argument(
        "--synthetic-sn",
        default="HX_CCD22_VERIFICATION_TEST",
        help="Serial number used for synthetic receiver contract posts.",
    )
    parser.add_argument(
        "--sign-secret",
        default=DEFAULT_SIGN_SECRET,
        help="Secret used to generate the private camera web API Sign header.",
    )
    args = parser.parse_args(argv)
    if args.observe_seconds < 0:
        parser.error("--observe-seconds must be 0 or greater")
    if args.allow_reset and not args.include_private_camera_apis:
        parser.error("--allow-reset requires --include-private-camera-apis")
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    out_dir = run_verification(args)
    print(f"Verification report written to: {out_dir}")
    print(f"Markdown: {out_dir / 'verification_report.md'}")
    print(f"JSON:     {out_dir / 'verification_report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
