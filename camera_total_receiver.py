#!/usr/bin/env python3
"""Mirror cumulative totals from the HX-CCD22 camera web interface."""

from __future__ import annotations

import hashlib
import csv
import io
import json
import os
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


PC_IP = os.getenv("PC_IP", "172.16.16.118")
CAMERA_IP = os.getenv("CAMERA_IP", "192.168.4.10")
BIND_HOST = "0.0.0.0"
PORT = 8086
POLL_SECONDS = 1
CAMERA_TIMEOUT_SECONDS = 5
DISPLAY_ENDPOINT = (
    f"http://{CAMERA_IP}/api/passengerFlow/"
    "passengerFlowData/DisplayDataGet"
)
RESET_ENDPOINT = (
    f"http://{CAMERA_IP}/api/passengerFlow/"
    "deviceManage/passengerFlowDataReset"
)
WEBRTC_URL = (
    f"http://{CAMERA_IP}/media/webrtc?"
    "app=live&stream=camera&type=play"
)
RTC_CLIENT_URL = f"http://{CAMERA_IP}/js/rtcClient.js"
SIGN_SECRET = "1096931dc28e4ecc9ddcb14e8760d53c"
DISPLAY_SIGN = hashlib.md5(SIGN_SECRET.encode()).hexdigest().upper()
DASHBOARD_REQUEST_HEADER = "X-Dashboard-Request"
DASHBOARD_REQUEST_VALUE = "HX-CCD22"
DASHBOARD_PATH = Path(__file__).with_name("camera_total_dashboard.html")

# Prototype mapping: both logical door cards intentionally point to the same
# physical HX-CCD22. Rear is display-only and must not contribute to aggregates.
# Replace this structure with database-backed bus/device assignments in production.
FLEET_CONFIG = {
    "buses": [
        {
            "id": "B-101",
            "number": "101",
            "name": "Prototype Bus",
            "route": "Prototype route",
            "path": "Lab validation",
            # Prototype fleet metadata only. The HX-CCD22 does not report bus
            # capacity; replace this with the assigned vehicle capacity later.
            "capacity": 65,
            "cameras": [
                {
                    "id": "B-101-front",
                    "label": "Front door",
                    "door_position": "FRONT",
                    "physical_source_id": "hx-primary",
                    "include_in_aggregation": True,
                    "prototype_mirror": False,
                },
                {
                    "id": "B-101-rear",
                    "label": "Rear door",
                    "door_position": "REAR",
                    "physical_source_id": "hx-primary",
                    "include_in_aggregation": False,
                    "prototype_mirror": True,
                },
            ],
        }
    ]
}
ONLINE_SECONDS = 90
DELAYED_SECONDS = 180

lock = threading.Lock()
camera_operation_lock = threading.Lock()
state: dict[str, Any] = {
    "in": 0,
    "out": 0,
    "passby": 0,
    "turnback": 0,
    "current_stay": 0,
    "avg_stay_time_seconds": 0.0,
    "last_sn": None,
    "last_client_ip": None,
    "last_heartbeat": None,
    "last_heartbeat_device_time": None,
    "last_push_upload": None,
    "last_camera_poll": None,
    "last_poll_error": None,
    "poll_successes": 0,
    "push_messages": 0,
    "latest_push_payload": None,
    "session_samples": [],
    "last_sample_minute": None,
}


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def record_push(path: str, client_ip: str, payload: dict[str, Any]) -> None:
    """Record push health only; pushed values are not camera website totals."""
    with lock:
        state["last_sn"] = str(payload.get("sn", state["last_sn"] or ""))
        state["last_client_ip"] = client_ip
        state["push_messages"] += 1
        state["latest_push_payload"] = payload
        if path.endswith("/heartBeat"):
            state["last_heartbeat"] = now_iso()
            state["last_heartbeat_device_time"] = payload.get("time")
        elif path.endswith("/dataUpload"):
            state["last_push_upload"] = now_iso()


def apply_display_response(payload: dict[str, Any]) -> None:
    result = payload.get("result")
    if isinstance(result, dict) and str(result.get("code")) != "0":
        raise ValueError(result.get("message") or "camera returned an error")

    required = ("enter", "leave", "pass", "return", "stay")
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(f"camera response missing: {', '.join(missing)}")

    with lock:
        state["in"] = as_int(payload["enter"])
        state["out"] = as_int(payload["leave"])
        state["passby"] = as_int(payload["pass"])
        state["turnback"] = as_int(payload["return"])
        state["current_stay"] = as_int(payload["stay"])
        state["avg_stay_time_seconds"] = as_float(
            payload.get("stayTimePerPerson")
        )
        state["last_camera_poll"] = now_iso()
        state["last_poll_error"] = None
        state["poll_successes"] += 1
        minute = datetime.now().replace(second=0, microsecond=0).isoformat()
        if state["last_sample_minute"] != minute:
            state["session_samples"].append(
                {
                    "time": minute,
                    "in": state["in"],
                    "out": state["out"],
                    "onboard": max(0, state["in"] - state["out"]),
                }
            )
            state["session_samples"] = state["session_samples"][-1440:]
            state["last_sample_minute"] = minute


def camera_request(endpoint: str) -> dict[str, Any]:
    request = Request(
        endpoint,
        data=b"",
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json;charset=utf-8",
            "Sign": DISPLAY_SIGN,
        },
    )
    with urlopen(request, timeout=CAMERA_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read())
    if not isinstance(payload, dict):
        raise ValueError("camera response must be a JSON object")
    return payload


def fetch_camera_display() -> dict[str, Any]:
    return camera_request(DISPLAY_ENDPOINT)


def fetch_camera_reset() -> dict[str, Any]:
    return camera_request(RESET_ENDPOINT)


def refresh_camera() -> dict[str, Any]:
    with camera_operation_lock:
        apply_display_response(fetch_camera_display())
        return snapshot_state()


def poll_camera_once() -> bool:
    try:
        refresh_camera()
        return True
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as error:
        with lock:
            state["last_poll_error"] = str(error)
        return False


def clear_camera_totals() -> dict[str, Any]:
    with camera_operation_lock:
        response = fetch_camera_reset()
        result = response.get("result")
        if isinstance(result, dict) and str(result.get("code")) != "0":
            raise ValueError(result.get("message") or "camera reset failed")

        deadline = time.monotonic() + 3
        latest: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            latest = fetch_camera_display()
            required = ("enter", "leave", "pass", "return", "stay")
            if all(as_int(latest.get(field)) == 0 for field in required):
                apply_display_response(latest)
                return snapshot_state()
            time.sleep(0.2)

        raise ValueError(
            "camera accepted reset but totals did not become zero"
        )


def validate_clear_request(
    dashboard_header: str | None, payload: dict[str, Any]
) -> None:
    if dashboard_header != DASHBOARD_REQUEST_VALUE:
        raise PermissionError("dashboard request header required")
    if payload.get("confirm") != "CLEAR":
        raise ValueError("explicit CLEAR confirmation required")


def poll_camera(stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        started = time.monotonic()
        poll_camera_once()
        remaining = POLL_SECONDS - (time.monotonic() - started)
        stop_event.wait(max(0, remaining))


def snapshot_state() -> dict[str, Any]:
    with lock:
        result = dict(state)

    last_poll = result["last_camera_poll"]
    result["online"] = bool(
        last_poll
        and time.time() - datetime.fromisoformat(last_poll).timestamp()
        <= max(5, POLL_SECONDS * 3)
        and not result["last_poll_error"]
    )
    result["net_count"] = result["in"] - result["out"]
    result["estimated_onboard"] = max(0, result["net_count"])
    result["camera_ip"] = CAMERA_IP
    result["source"] = "camera_web_display_api"
    result["display_endpoint"] = DISPLAY_ENDPOINT
    result["webrtc_url"] = WEBRTC_URL
    result["rtc_client_url"] = RTC_CLIENT_URL
    result["stream_available"] = result["online"]
    result["server_time"] = now_iso()
    return result


def heartbeat_status(last_heartbeat: str | None, now: float | None = None) -> tuple[str, int | None]:
    if not last_heartbeat:
        return "offline", None
    reference = time.time() if now is None else now
    age = max(0, int(reference - datetime.fromisoformat(last_heartbeat).timestamp()))
    if age <= ONLINE_SECONDS:
        return "online", age
    if age <= DELAYED_SECONDS:
        return "delayed", age
    return "offline", age


def logical_camera(camera: dict[str, Any], physical: dict[str, Any]) -> dict[str, Any]:
    status, heartbeat_age = heartbeat_status(physical["last_heartbeat"])
    return {
        **camera,
        "sn": physical["last_sn"],
        "ip": physical["camera_ip"],
        "status": status,
        "heartbeat_age_seconds": heartbeat_age,
        "last_heartbeat": physical["last_heartbeat"],
        "last_count_update": physical["last_camera_poll"],
        "in": physical["in"],
        "out": physical["out"],
        "passby": physical["passby"],
        "turnback": physical["turnback"],
        "stay": physical["current_stay"],
        "net": physical["net_count"],
        "onboard": physical["estimated_onboard"],
        "webrtc_url": physical["webrtc_url"],
        "rtc_client_url": physical["rtc_client_url"],
        "stream_available": physical["stream_available"],
    }


def aggregate_cameras(cameras: list[dict[str, Any]]) -> dict[str, int]:
    included = [camera for camera in cameras if camera["include_in_aggregation"]]
    total_in = sum(camera["in"] for camera in included)
    total_out = sum(camera["out"] for camera in included)
    return {
        "in": total_in,
        "out": total_out,
        "passby": sum(camera["passby"] for camera in included),
        "turnback": sum(camera["turnback"] for camera in included),
        "onboard": max(0, total_in - total_out),
    }


def bus_snapshot(bus_id: str) -> dict[str, Any]:
    bus = next((item for item in FLEET_CONFIG["buses"] if item["id"] == bus_id), None)
    if not bus:
        raise KeyError(f"unknown bus: {bus_id}")
    physical = snapshot_state()
    cameras = [logical_camera(camera, physical) for camera in bus["cameras"]]
    status_order = {"online": 0, "delayed": 1, "offline": 2}
    status = max((camera["status"] for camera in cameras), key=status_order.get)
    return {
        **{key: value for key, value in bus.items() if key != "cameras"},
        "status": status,
        "totals": aggregate_cameras(cameras),
        "cameras": cameras,
        "session_samples": list(physical["session_samples"]),
    }


def fleet_snapshot() -> dict[str, Any]:
    buses = [bus_snapshot(bus["id"]) for bus in FLEET_CONFIG["buses"]]
    unique_sources: dict[str, str] = {}
    logical_online = 0
    for bus in buses:
        for camera in bus["cameras"]:
            unique_sources[camera["physical_source_id"]] = camera["status"]
            if camera["status"] == "online":
                logical_online += 1
    return {
        "totals": {
            "onboard": sum(bus["totals"]["onboard"] for bus in buses),
            "in": sum(bus["totals"]["in"] for bus in buses),
            "out": sum(bus["totals"]["out"] for bus in buses),
            "logical_cameras_online": logical_online,
            "logical_cameras_total": sum(len(bus["cameras"]) for bus in buses),
            "physical_devices_online": sum(
                status == "online" for status in unique_sources.values()
            ),
            "physical_devices_total": len(unique_sources),
        },
        "buses": [
            {
                "id": bus["id"],
                "number": bus["number"],
                "name": bus["name"],
                "route": bus["route"],
                "path": bus["path"],
                "status": bus["status"],
                "totals": bus["totals"],
                "last_update": max(
                    (
                        camera["last_count_update"] or ""
                        for camera in bus["cameras"]
                    ),
                    default="",
                ),
            }
            for bus in buses
        ],
    }


def find_camera(camera_id: str) -> dict[str, Any]:
    for bus in FLEET_CONFIG["buses"]:
        for camera in bus["cameras"]:
            if camera["id"] == camera_id:
                return camera
    raise KeyError(f"unknown camera: {camera_id}")


def export_csv() -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["type", "bus_id", "camera_id", "time", "in", "out", "onboard", "status"])
    for bus in [bus_snapshot(item["id"]) for item in FLEET_CONFIG["buses"]]:
        writer.writerow(["bus", bus["id"], "", now_iso(), bus["totals"]["in"], bus["totals"]["out"], bus["totals"]["onboard"], bus["status"]])
        for camera in bus["cameras"]:
            writer.writerow(["camera", bus["id"], camera["id"], camera["last_count_update"], camera["in"], camera["out"], camera["onboard"], camera["status"]])
        for sample in bus["session_samples"]:
            writer.writerow(["sample", bus["id"], "", sample["time"], sample["in"], sample["out"], sample["onboard"], ""])
    return output.getvalue().encode()


class TotalReceiverHandler(BaseHTTPRequestHandler):
    def log_message(self, *_: Any) -> None:
        return

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_dashboard(self) -> None:
        try:
            body = DASHBOARD_PATH.read_bytes()
        except OSError:
            self.send_json({"error": "camera_total_dashboard.html not found"}, 500)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_csv(self, body: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="fleet-counter.csv"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_payload(self) -> dict[str, Any]:
        length = as_int(self.headers.get("Content-Length"))
        if length <= 0 or length > 5_000_000:
            raise ValueError("invalid request size")
        payload = json.loads(self.rfile.read(length))
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self.send_dashboard()
        elif path == "/api/camera-total":
            self.send_json(snapshot_state())
        elif path == "/api/dashboard/fleet":
            self.send_json(fleet_snapshot())
        elif path.startswith("/api/dashboard/buses/"):
            try:
                self.send_json(bus_snapshot(path.rsplit("/", 1)[-1]))
            except KeyError as error:
                self.send_json({"error": str(error)}, 404)
        elif path == "/api/dashboard/export.csv":
            self.send_csv(export_csv())
        elif path == "/health":
            data = snapshot_state()
            self.send_json(
                {
                    "status": "ok" if data["online"] else "camera unavailable",
                    "camera_online": data["online"],
                    "last_camera_poll": data["last_camera_poll"],
                    "poll_error": data["last_poll_error"],
                },
                200 if data["online"] else 503,
            )
        else:
            self.send_json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path.startswith("/api/dashboard/cameras/"):
            parts = path.strip("/").split("/")
            if len(parts) != 5 or parts[4] not in ("refresh", "clear"):
                self.send_json({"ok": False, "error": "unknown camera action"}, 404)
                return
            try:
                find_camera(parts[3])
                if parts[4] == "refresh":
                    self.send_json({"ok": True, "data": refresh_camera()})
                else:
                    payload = self.read_payload()
                    validate_clear_request(
                        self.headers.get(DASHBOARD_REQUEST_HEADER), payload
                    )
                    self.send_json({"ok": True, "data": clear_camera_totals()})
            except KeyError as error:
                self.send_json({"ok": False, "error": str(error)}, 404)
            except PermissionError as error:
                self.send_json({"ok": False, "error": str(error)}, 403)
            except ValueError as error:
                self.send_json({"ok": False, "error": str(error)}, 409)
            except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
                self.send_json({"ok": False, "error": str(error)}, 502)
            return
        if path == "/api/camera-refresh":
            try:
                self.send_json({"ok": True, "data": refresh_camera()})
            except (
                HTTPError,
                URLError,
                TimeoutError,
                OSError,
                ValueError,
                json.JSONDecodeError,
            ) as error:
                self.send_json({"ok": False, "error": str(error)}, 502)
            return

        if path == "/api/camera-clear":
            try:
                payload = self.read_payload()
                validate_clear_request(
                    self.headers.get(DASHBOARD_REQUEST_HEADER), payload
                )
                self.send_json({"ok": True, "data": clear_camera_totals()})
            except PermissionError as error:
                self.send_json({"ok": False, "error": str(error)}, 403)
            except ValueError as error:
                self.send_json({"ok": False, "error": str(error)}, 409)
            except (
                HTTPError,
                URLError,
                TimeoutError,
                OSError,
                json.JSONDecodeError,
            ) as error:
                self.send_json({"ok": False, "error": str(error)}, 502)
            return

        if path not in (
            "/api/camera/heartBeat",
            "/api/camera/dataUpload",
        ):
            self.send_json({"code": 2, "msg": "unknown endpoint"}, 404)
            return

        try:
            payload = self.read_payload()
            sn = str(payload.get("sn", "")).strip()
            if not sn:
                raise ValueError("sn is required")
            record_push(path, self.client_address[0], payload)
            response_data: dict[str, Any] = {
                "sn": sn,
                "time": int(time.time()),
            }
            if path.endswith("/heartBeat"):
                response_data.update(
                    {
                        "uploadInterval": 0,
                        "dataMode": "total",
                    }
                )
            self.send_json(
                {"code": 0, "msg": "success", "data": response_data}
            )
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json({"code": 2, "msg": str(error)}, 400)


def log_snapshot(data: dict[str, Any]) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    if data["online"]:
        print(
            f"[{timestamp}] CAMERA TOTAL "
            f"IN={data['in']} OUT={data['out']} "
            f"STAY={data['current_stay']} PASS={data['passby']} "
            f"RETURN={data['turnback']} NET={data['net_count']:+d}"
        )
    else:
        print(
            f"[{timestamp}] CAMERA POLL ERROR: "
            f"{data['last_poll_error'] or 'waiting for first response'}"
        )


def main() -> None:
    try:
        server = ThreadingHTTPServer((BIND_HOST, PORT), TotalReceiverHandler)
    except OSError as error:
        raise SystemExit(
            f"Could not listen on port {PORT}: {error}\n"
            "Stop camera_live_receiver.py before starting this receiver."
        ) from error

    stop_event = threading.Event()
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    poll_thread = threading.Thread(
        target=poll_camera, args=(stop_event,), daemon=True
    )
    server_thread.start()
    poll_thread.start()

    print("HX-CCD22 CAMERA WEBSITE MIRROR")
    print(f"Camera source      : {DISPLAY_ENDPOINT}")
    print(f"Dashboard          : http://{PC_IP}:{PORT}")
    print("Push packets       : diagnostics only")
    print("Stop with Ctrl+C")

    previous: tuple[Any, ...] | None = None
    try:
        while True:
            data = snapshot_state()
            current = (
                data["online"],
                data["in"],
                data["out"],
                data["current_stay"],
                data["passby"],
                data["turnback"],
                data["last_poll_error"],
            )
            if current != previous:
                log_snapshot(data)
                previous = current
            time.sleep(0.25)
    except KeyboardInterrupt:
        print("\nStopping camera website mirror...")
    finally:
        stop_event.set()
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)
        poll_thread.join(timeout=2)


if __name__ == "__main__":
    main()
