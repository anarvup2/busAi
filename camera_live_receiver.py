#!/usr/bin/env python3
"""Receive and display live HX-CCD22 passenger-count data."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


# Camera HTTP Address1 must point to this PC address and port.
PC_IP = "172.16.16.118"
BIND_HOST = "0.0.0.0"
PORT = 8088

# The HX-CCD22 API defines 0 as real-time. This firmware sends short-window
# increments, so totals are accumulated for the lifetime of this process.
UPLOAD_INTERVAL = 0
DATA_MODE = "Add"
REFRESH_SECONDS = 1
DASHBOARD_PATH = Path(__file__).with_name("live_dashboard.html")


lock = threading.Lock()
state: dict[str, Any] = {
    "in": 0,
    "out": 0,
    "passby": 0,
    "turnback": 0,
    "messages": 0,
    "uploads": 0,
    "last_heartbeat": None,
    "last_upload": None,
    "last_client_ip": None,
    "last_sn": None,
    "latest_payload": None,
    "seen_uploads": set(),
}


def as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def upload_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Support both real-time payloads and historical {data: [...]} batches."""
    if isinstance(payload.get("data"), list):
        return [record for record in payload["data"] if isinstance(record, dict)]
    return [payload]


def snapshot_state() -> dict[str, Any]:
    with lock:
        snapshot = {
            key: value
            for key, value in state.items()
            if key != "seen_uploads"
        }

    snapshot["net_flow"] = snapshot["in"] - snapshot["out"]
    snapshot["occupancy"] = max(0, snapshot["net_flow"])
    last_seen = snapshot["last_heartbeat"] or snapshot["last_upload"]
    if snapshot["last_heartbeat"] and snapshot["last_upload"]:
        last_seen = max(snapshot["last_heartbeat"], snapshot["last_upload"])
    snapshot["online"] = bool(
        last_seen
        and time.time() - datetime.fromisoformat(last_seen).timestamp() <= 180
    )
    snapshot["server_time"] = datetime.now().isoformat(timespec="seconds")
    return snapshot


def record_message(path: str, client_ip: str, payload: dict[str, Any]) -> None:
    now = datetime.now().isoformat(timespec="seconds")

    with lock:
        state["messages"] += 1
        state["last_client_ip"] = client_ip
        state["last_sn"] = str(payload.get("sn", state["last_sn"] or ""))

        if path.endswith("/heartBeat"):
            state["last_heartbeat"] = now
            return

        if not path.endswith("/dataUpload"):
            return

        records = upload_records(payload)
        accepted_records = 0
        for record in records:
            fingerprint_data = {
                "sn": record.get("sn", payload.get("sn")),
                "time": record.get("time"),
                "startTime": record.get("startTime"),
                "endTime": record.get("endTime"),
                "in": as_int(record.get("in")),
                "out": as_int(record.get("out")),
                "passby": as_int(record.get("passby")),
                "turnback": as_int(record.get("turnback")),
                "eventList": record.get("eventList", payload.get("eventList", [])),
            }
            fingerprint = hashlib.sha256(
                json.dumps(fingerprint_data, sort_keys=True).encode()
            ).hexdigest()
            if fingerprint in state["seen_uploads"]:
                continue

            state["seen_uploads"].add(fingerprint)
            accepted_records += 1
            state["in"] += fingerprint_data["in"]
            state["out"] += fingerprint_data["out"]
            state["passby"] += fingerprint_data["passby"]
            state["turnback"] += fingerprint_data["turnback"]

        if accepted_records:
            state["uploads"] += accepted_records
            state["last_upload"] = now
            state["latest_payload"] = payload


class CameraReceiver(BaseHTTPRequestHandler):
    def log_message(self, *_: Any) -> None:
        return

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path, content_type: str) -> None:
        try:
            body = path.read_bytes()
        except OSError:
            self.send_json({"error": f"missing file: {path.name}"}, 500)
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self.send_file(DASHBOARD_PATH, "text/html; charset=utf-8")
        elif path == "/api/live":
            self.send_json(snapshot_state())
        elif path == "/health":
            self.send_json(
                {
                    "status": "HX-CCD22 receiver running",
                    "time": int(time.time()),
                }
            )
        else:
            self.send_json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in (
            "/api/camera/heartBeat",
            "/api/camera/dataUpload",
        ):
            self.send_json({"code": 2, "msg": "unknown endpoint"}, 404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0 or content_length > 5_000_000:
                raise ValueError("invalid request size")

            payload = json.loads(self.rfile.read(content_length))
            if not isinstance(payload, dict):
                raise ValueError("JSON body must be an object")
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json({"code": 2, "msg": str(error)}, 400)
            return

        record_message(path, self.client_address[0], payload)

        sn = str(payload.get("sn", ""))
        response_data: dict[str, Any] = {
            "sn": sn,
            "time": int(time.time()),
        }
        if path.endswith("/heartBeat"):
            response_data.update(
                {
                    "uploadInterval": UPLOAD_INTERVAL,
                    "dataMode": DATA_MODE,
                }
            )

        self.send_json({"code": 0, "msg": "success", "data": response_data})


def clear_terminal() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def display_dashboard() -> None:
    snapshot = snapshot_state()
    clear_terminal()
    print("HX-CCD22 LIVE PASSENGER COUNTS")
    print("=" * 58)
    print(f"IN                 : {snapshot['in']}")
    print(f"OUT                : {snapshot['out']}")
    print(f"NET FLOW           : {snapshot['net_flow']:+d}")
    print(f"EST. ONBOARD       : {snapshot['occupancy']} (this session)")
    print(f"PASS BY            : {snapshot['passby']}")
    print(f"TURN BACK          : {snapshot['turnback']}")
    print("-" * 58)
    print(f"Camera SN          : {snapshot['last_sn'] or 'Waiting...'}")
    print(f"Camera client IP   : {snapshot['last_client_ip'] or 'Waiting...'}")
    print(f"Last heartbeat     : {snapshot['last_heartbeat'] or 'Waiting...'}")
    print(f"Last count upload  : {snapshot['last_upload'] or 'Waiting...'}")
    print(f"Messages received  : {snapshot['messages']}")
    print(f"Unique uploads     : {snapshot['uploads']}")
    print("-" * 58)
    print(f"Listening on       : {BIND_HOST}:{PORT}")
    print(f"Camera Address1    : {PC_IP}:{PORT}")
    print(f"Browser dashboard  : http://{PC_IP}:{PORT}")
    print("Stop with Ctrl+C")

    if snapshot["latest_payload"]:
        print("\nLATEST REAL dataUpload JSON")
        print(json.dumps(snapshot["latest_payload"], indent=2, ensure_ascii=False))


def main() -> None:
    try:
        server = ThreadingHTTPServer((BIND_HOST, PORT), CameraReceiver)
    except OSError as error:
        raise SystemExit(
            f"Could not listen on port {PORT}: {error}\n"
            "Stop any previous notebook receiver or process using this port."
        ) from error

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        while True:
            display_dashboard()
            time.sleep(REFRESH_SECONDS)
    except KeyboardInterrupt:
        print("\nStopping receiver...")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    main()
