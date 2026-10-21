#!/usr/bin/env python3
"""Capture complete HX-CCD22 push data for integration validation.

This server is for the lab/pilot question: what does the camera really send
when Address1 points to our backend instead of Foorir's backend?
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


PC_IP = os.getenv("PC_IP", "172.16.16.118")
BIND_HOST = os.getenv("BIND_HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8088"))
DB_PATH = Path(os.getenv("DB_PATH", "hx_camera_audit.db"))
UPLOAD_INTERVAL_MINUTES = int(os.getenv("UPLOAD_INTERVAL_MINUTES", "1"))
DATA_MODE = os.getenv("DATA_MODE", "Add")
TIMEZONE_OFFSET = float(os.getenv("TIMEZONE_OFFSET", "5.5"))
CHILD_HEIGHT_CM = int(os.getenv("CHILD_HEIGHT_CM", "140"))
MAX_BODY_BYTES = 10_000_000
ONLINE_SECONDS = 90
DELAYED_SECONDS = 180

COUNT_UPLOAD_MIGRATIONS = {
    "passby_adult": "INTEGER",
    "passby_child": "INTEGER",
    "turnback_adult": "INTEGER",
    "turnback_child": "INTEGER",
}

CAMERA_PUSH_FIELD_CATALOG = {
    "heartbeat": {
        "sn": ("string", "Camera serial number."),
        "hostName": ("string", "Camera hostname."),
        "macAddress": ("string", "Camera MAC address."),
        "hwPlatform": ("string", "Hardware platform."),
        "swRelease": ("string", "Firmware/software version."),
        "connectionType": ("string", "Network connection type, for example Wired."),
        "ipAddress": ("string", "Camera-reported IP address."),
        "ipAddressMethod": ("string", "IP assignment method, for example DHCP."),
        "time": ("integer", "Camera timestamp."),
        "timeZone": ("number", "Camera timezone offset."),
    },
    "data_upload": {
        "sn": ("string", "Camera serial number."),
        "startTime": ("integer", "Start of the upload/counting window."),
        "endTime": ("integer", "End of the upload/counting window."),
        "time": ("integer", "Camera event/upload timestamp."),
        "in": ("integer", "People counted entering during this upload window."),
        "out": ("integer", "People counted leaving during this upload window."),
        "passby": ("integer", "People detected passing by without crossing."),
        "turnback": ("integer", "People detected turning back."),
        "avgStayTime": ("integer", "Average stay/dwell time in milliseconds."),
        "len": ("integer", "Number of person-event records in attributes[]."),
        "inAdult": ("integer", "Adult-height in count when child mode is enabled."),
        "outAdult": ("integer", "Adult-height out count when child mode is enabled."),
        "inChild": ("integer", "Child-height in count when child mode is enabled."),
        "outChild": ("integer", "Child-height out count when child mode is enabled."),
        "passbyAdult": ("integer", "Adult-height passby count when child mode is enabled."),
        "passbyChild": ("integer", "Child-height passby count when child mode is enabled."),
        "turnbackAdult": ("integer", "Adult-height turnback count when child mode is enabled."),
        "turnbackChild": ("integer", "Child-height turnback count when child mode is enabled."),
        "attributes": ("array<object>", "Firmware person-event list."),
        "eventList": ("array<object>", "Documented person-event list, if firmware uses it."),
    },
    "person_event": {
        "attributes[].eventType": ("integer", "Person event type. Observed value: 0."),
        "attributes[].height": ("integer", "Detected person height in centimeters."),
        "attributes[].idIndex": ("integer", "Firmware event/person identifier."),
        "attributes[].lineId": ("integer", "Counting line identifier."),
        "attributes[].personId": ("integer", "Firmware person identifier."),
        "attributes[].stayTime": ("integer", "Per-person stay time in milliseconds."),
        "attributes[].timeStamp": ("integer", "Per-person timestamp in microseconds."),
    },
    "camera_web_api": {
        "enter": ("integer", "Camera website cumulative/preview enter count."),
        "leave": ("integer", "Camera website cumulative/preview leave count."),
        "pass": ("integer", "Camera website pass count."),
        "return": ("integer", "Camera website return/turnback count."),
        "stay": ("integer", "Camera website current stay count."),
        "stayTimePerPerson": ("number", "Camera website average stay time per person."),
        "age": ("object", "Camera website age bucket summary."),
        "gender": ("object", "Camera website gender bucket summary."),
        "workcard": ("integer", "Camera website workcard count."),
    },
}

db_lock = threading.Lock()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def unix_now() -> int:
    return int(time.time())


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json_dumps(payload).encode()).hexdigest()


def parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def upload_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Support both live payloads and historical {sn, len, data: [...]} batches."""
    records = payload.get("data")
    if isinstance(records, list):
        sn = payload.get("sn")
        normalized: list[dict[str, Any]] = []
        for item in records:
            if isinstance(item, dict):
                normalized.append({"sn": item.get("sn", sn), **item})
        return normalized
    return [payload]


def event_records(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Support documented eventList and firmware attributes payloads."""
    events: list[dict[str, Any]] = []
    for key in ("eventList", "attributes"):
        value = record.get(key, [])
        if isinstance(value, list):
            events.extend(item for item in value if isinstance(item, dict))
    return events


def event_id(event: dict[str, Any]) -> int:
    return as_int(
        event.get(
            "id",
            event.get("idIndex", event.get("personId")),
        )
    )


def event_timestamp(event: dict[str, Any]) -> int:
    return as_int(event.get("timestamp", event.get("timeStamp")))


def upload_row_matches_record(
    upload: sqlite3.Row | dict[str, Any], record: dict[str, Any]
) -> bool:
    return (
        str(upload["sn"]) == str(record.get("sn"))
        and as_int(upload["camera_time"]) == as_int(record.get("time"))
        and as_int(upload["start_time"]) == as_int(record.get("startTime"))
        and as_int(upload["end_time"]) == as_int(record.get("endTime"))
        and as_int(upload["in_count"]) == as_int(record.get("in"))
        and as_int(upload["out_count"]) == as_int(record.get("out"))
        and as_int(upload["passby_count"]) == as_int(record.get("passby"))
        and as_int(upload["turnback_count"]) == as_int(record.get("turnback"))
    )


def insert_person_event(
    conn: sqlite3.Connection,
    upload_id: int,
    event: dict[str, Any],
) -> None:
    conn.execute(
        """
        INSERT INTO person_events (
            upload_id, event_id, event_timestamp, event_type,
            height_cm, stay_time_ms, raw_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            upload_id,
            event_id(event),
            event_timestamp(event),
            as_int(event.get("eventType")),
            as_int(event.get("height")),
            as_int(event.get("stayTime")),
            json_dumps(event),
        ),
    )


def backfill_person_events(conn: sqlite3.Connection) -> None:
    """Populate events for existing raw captures after parser upgrades."""
    conn.row_factory = sqlite3.Row
    uploads = conn.execute(
        """
        SELECT count_uploads.*, raw_requests.payload_json
        FROM count_uploads
        JOIN raw_requests ON raw_requests.id = count_uploads.raw_request_id
        WHERE NOT EXISTS (
            SELECT 1 FROM person_events
            WHERE person_events.upload_id = count_uploads.id
        )
        ORDER BY count_uploads.id
        """
    ).fetchall()
    for upload in uploads:
        payload = json.loads(upload["payload_json"])
        for record in upload_records(payload):
            if not upload_row_matches_record(upload, record):
                continue
            for event in event_records(record):
                insert_person_event(conn, int(upload["id"]), event)


def migrate_db(conn: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(count_uploads)").fetchall()
    }
    for column, definition in COUNT_UPLOAD_MIGRATIONS.items():
        if column not in columns:
            conn.execute(f"ALTER TABLE count_uploads ADD COLUMN {column} {definition}")


def init_db() -> None:
    with db_lock, sqlite3.connect(DB_PATH) as conn:
        conn.executescript(
            """
            PRAGMA journal_mode = WAL;

            CREATE TABLE IF NOT EXISTS devices (
                sn TEXT PRIMARY KEY,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                last_client_ip TEXT,
                heartbeat_count INTEGER NOT NULL DEFAULT 0,
                upload_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS raw_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                received_at TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                client_ip TEXT NOT NULL,
                sn TEXT,
                payload_hash TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS heartbeats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                received_at TEXT NOT NULL,
                client_ip TEXT NOT NULL,
                sn TEXT NOT NULL,
                camera_time INTEGER,
                raw_request_id INTEGER NOT NULL,
                FOREIGN KEY(raw_request_id) REFERENCES raw_requests(id)
            );

            CREATE TABLE IF NOT EXISTS count_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                received_at TEXT NOT NULL,
                client_ip TEXT NOT NULL,
                sn TEXT NOT NULL,
                camera_time INTEGER,
                start_time INTEGER,
                end_time INTEGER,
                in_count INTEGER NOT NULL DEFAULT 0,
                out_count INTEGER NOT NULL DEFAULT 0,
                passby_count INTEGER NOT NULL DEFAULT 0,
                turnback_count INTEGER NOT NULL DEFAULT 0,
                avg_stay_time_ms INTEGER,
                in_adult INTEGER,
                out_adult INTEGER,
                in_child INTEGER,
                out_child INTEGER,
                passby_adult INTEGER,
                passby_child INTEGER,
                turnback_adult INTEGER,
                turnback_child INTEGER,
                total INTEGER,
                payload_hash TEXT NOT NULL UNIQUE,
                raw_request_id INTEGER NOT NULL,
                FOREIGN KEY(raw_request_id) REFERENCES raw_requests(id)
            );

            CREATE TABLE IF NOT EXISTS person_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_id INTEGER NOT NULL,
                event_id INTEGER,
                event_timestamp INTEGER,
                event_type INTEGER,
                height_cm INTEGER,
                stay_time_ms INTEGER,
                raw_json TEXT NOT NULL,
                FOREIGN KEY(upload_id) REFERENCES count_uploads(id)
            );

            CREATE TABLE IF NOT EXISTS receiver_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                baseline_upload_id INTEGER NOT NULL DEFAULT 0,
                baseline_raw_request_id INTEGER NOT NULL DEFAULT 0,
                note TEXT
            );
            """
        )
        migrate_db(conn)
        backfill_person_events(conn)


def upsert_device(conn: sqlite3.Connection, sn: str, client_ip: str, kind: str) -> None:
    now = utc_now_iso()
    heartbeat_inc = 1 if kind == "heartbeat" else 0
    upload_inc = 1 if kind == "upload" else 0
    conn.execute(
        """
        INSERT INTO devices (
            sn, first_seen_at, last_seen_at, last_client_ip,
            heartbeat_count, upload_count
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(sn) DO UPDATE SET
            last_seen_at = excluded.last_seen_at,
            last_client_ip = excluded.last_client_ip,
            heartbeat_count = heartbeat_count + ?,
            upload_count = upload_count + ?
        """,
        (sn, now, now, client_ip, heartbeat_inc, upload_inc, heartbeat_inc, upload_inc),
    )


def insert_raw_request(
    conn: sqlite3.Connection,
    endpoint: str,
    client_ip: str,
    payload: dict[str, Any],
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO raw_requests (
            received_at, endpoint, client_ip, sn, payload_hash, payload_json
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            utc_now_iso(),
            endpoint,
            client_ip,
            str(payload.get("sn", "")),
            payload_hash(payload),
            json_dumps(payload),
        ),
    )
    return int(cursor.lastrowid)


def record_heartbeat(
    endpoint: str,
    client_ip: str,
    payload: dict[str, Any],
) -> None:
    sn = str(payload.get("sn", "")).strip()
    if not sn:
        raise ValueError("sn is required")

    with db_lock, sqlite3.connect(DB_PATH) as conn:
        raw_request_id = insert_raw_request(conn, endpoint, client_ip, payload)
        upsert_device(conn, sn, client_ip, "heartbeat")
        conn.execute(
            """
            INSERT INTO heartbeats (
                received_at, client_ip, sn, camera_time, raw_request_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (utc_now_iso(), client_ip, sn, as_int(payload.get("time")), raw_request_id),
        )


def record_upload(
    endpoint: str,
    client_ip: str,
    payload: dict[str, Any],
) -> int:
    sn = str(payload.get("sn", "")).strip()
    if not sn:
        raise ValueError("sn is required")

    inserted = 0
    with db_lock, sqlite3.connect(DB_PATH) as conn:
        raw_request_id = insert_raw_request(conn, endpoint, client_ip, payload)
        for record in upload_records(payload):
            record_sn = str(record.get("sn") or sn).strip()
            if not record_sn:
                raise ValueError("record sn is required")
            fingerprint = payload_hash(
                {
                    "sn": record_sn,
                    "time": record.get("time"),
                    "startTime": record.get("startTime"),
                    "endTime": record.get("endTime"),
                    "in": record.get("in"),
                    "out": record.get("out"),
                    "passby": record.get("passby"),
                    "turnback": record.get("turnback"),
                    "eventList": record.get("eventList", []),
                    "attributes": record.get("attributes", []),
                }
            )
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO count_uploads (
                    received_at, client_ip, sn, camera_time, start_time, end_time,
                    in_count, out_count, passby_count, turnback_count,
                    avg_stay_time_ms, in_adult, out_adult, in_child, out_child,
                    passby_adult, passby_child, turnback_adult, turnback_child,
                    total, payload_hash, raw_request_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    utc_now_iso(),
                    client_ip,
                    record_sn,
                    as_int(record.get("time")),
                    as_int(record.get("startTime")),
                    as_int(record.get("endTime")),
                    as_int(record.get("in")),
                    as_int(record.get("out")),
                    as_int(record.get("passby")),
                    as_int(record.get("turnback")),
                    as_int(record.get("avgStayTime")),
                    as_int(record.get("inAdult")) if "inAdult" in record else None,
                    as_int(record.get("outAdult")) if "outAdult" in record else None,
                    as_int(record.get("inChild")) if "inChild" in record else None,
                    as_int(record.get("outChild")) if "outChild" in record else None,
                    as_int(record.get("passbyAdult"))
                    if "passbyAdult" in record
                    else None,
                    as_int(record.get("passbyChild"))
                    if "passbyChild" in record
                    else None,
                    as_int(record.get("turnbackAdult"))
                    if "turnbackAdult" in record
                    else None,
                    as_int(record.get("turnbackChild"))
                    if "turnbackChild" in record
                    else None,
                    as_int(record.get("total")) if "total" in record else None,
                    fingerprint,
                    raw_request_id,
                ),
            )
            if cursor.rowcount == 0:
                continue

            inserted += 1
            upload_id = int(cursor.lastrowid)
            for event in event_records(record):
                conn.execute(
                    """
                    INSERT INTO person_events (
                        upload_id, event_id, event_timestamp, event_type,
                        height_cm, stay_time_ms, raw_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        upload_id,
                        event_id(event),
                        event_timestamp(event),
                        as_int(event.get("eventType")),
                        as_int(event.get("height")),
                        as_int(event.get("stayTime")),
                        json_dumps(event),
                    ),
                )
            upsert_device(conn, record_sn, client_ip, "upload")
    return inserted


def query_one(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with db_lock, sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def query_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with db_lock, sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def count_totals(where_clause: str = "", params: tuple[Any, ...] = ()) -> dict[str, Any]:
    query = f"""
        SELECT
            COUNT(*) AS upload_rows,
            COALESCE(SUM(in_count), 0) AS in_total,
            COALESCE(SUM(out_count), 0) AS out_total,
            COALESCE(SUM(passby_count), 0) AS passby_total,
            COALESCE(SUM(turnback_count), 0) AS turnback_total,
            MAX(received_at) AS last_upload_at
        FROM count_uploads
        {where_clause}
        """
    totals = query_one(query, params) or {}
    in_total = as_int(totals.get("in_total"))
    out_total = as_int(totals.get("out_total"))
    return {
        "upload_rows": as_int(totals.get("upload_rows")),
        "in": in_total,
        "out": out_total,
        "passby": as_int(totals.get("passby_total")),
        "turnback": as_int(totals.get("turnback_total")),
        "estimated_onboard": max(0, in_total - out_total),
        "last_upload_at": totals.get("last_upload_at"),
    }


def latest_session() -> dict[str, Any] | None:
    return query_one(
        """
        SELECT id, started_at, baseline_upload_id, baseline_raw_request_id, note
        FROM receiver_sessions
        ORDER BY id DESC
        LIMIT 1
        """
    )


def session_totals(session: dict[str, Any] | None = None) -> dict[str, Any]:
    active_session = session if session is not None else latest_session()
    baseline_upload_id = (
        as_int(active_session.get("baseline_upload_id")) if active_session else 0
    )
    return count_totals("WHERE id > ?", (baseline_upload_id,))


def create_session_reset(note: str | None = None) -> dict[str, Any]:
    latest_upload = query_one("SELECT COALESCE(MAX(id), 0) AS id FROM count_uploads")
    latest_raw = query_one("SELECT COALESCE(MAX(id), 0) AS id FROM raw_requests")
    baseline_upload_id = as_int(latest_upload.get("id") if latest_upload else 0)
    baseline_raw_request_id = as_int(latest_raw.get("id") if latest_raw else 0)
    started_at = utc_now_iso()
    with db_lock, sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO receiver_sessions (
                started_at, baseline_upload_id, baseline_raw_request_id, note
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                started_at,
                baseline_upload_id,
                baseline_raw_request_id,
                note or "Manual receiver session reset.",
            ),
        )
        session_id = int(cursor.lastrowid)
    session = {
        "id": session_id,
        "started_at": started_at,
        "baseline_upload_id": baseline_upload_id,
        "baseline_raw_request_id": baseline_raw_request_id,
        "note": note or "Manual receiver session reset.",
    }
    return {
        "server_time": utc_now_iso(),
        "session": session,
        "session_totals": session_totals(session),
        "instructions": (
            "Compare the camera website against session_totals. All raw JSON and "
            "all-time upload rows are still preserved."
        ),
    }


def session_report() -> dict[str, Any]:
    session = latest_session()
    recent_window_rows = query_all(
        """
        SELECT id, received_at, start_time, end_time, camera_time,
               in_count, out_count, passby_count, turnback_count
        FROM count_uploads
        ORDER BY id DESC
        LIMIT 20
        """
    )
    return {
        "server_time": utc_now_iso(),
        "db_path": str(DB_PATH),
        "active_session": session,
        "all_time_totals": count_totals(),
        "session_totals": session_totals(session),
        "recent_upload_windows": recent_window_rows,
        "comparison_note": (
            "Use session_totals after POST /api/debug/session-reset when matching "
            "the camera website after pressing Clearing."
        ),
    }


def dashboard_summary() -> dict[str, Any]:
    totals = count_totals()
    devices = query_all(
        """
        SELECT sn, first_seen_at, last_seen_at, last_client_ip,
               heartbeat_count, upload_count
        FROM devices
        ORDER BY last_seen_at DESC
        """
    )
    return {
        "server_time": utc_now_iso(),
        "db_path": str(DB_PATH),
        "totals": {
            "upload_rows": totals["upload_rows"],
            "in_total": totals["in"],
            "out_total": totals["out"],
            "passby_total": totals["passby"],
            "turnback_total": totals["turnback"],
            "estimated_onboard": totals["estimated_onboard"],
        },
        "devices": devices,
        "latest_payload": latest_payload(),
    }


def latest_payload() -> dict[str, Any] | None:
    row = query_one(
        """
        SELECT received_at, endpoint, client_ip, payload_json
        FROM raw_requests
        ORDER BY id DESC
        LIMIT 1
        """
    )
    if not row:
        return None
    return {
        "received_at": row["received_at"],
        "endpoint": row["endpoint"],
        "client_ip": row["client_ip"],
        "payload": json.loads(row["payload_json"]),
    }


def observed_fields() -> dict[str, Any]:
    rows = query_all("SELECT endpoint, payload_json FROM raw_requests ORDER BY id DESC")
    by_endpoint: dict[str, set[str]] = {}
    upload_record_fields: set[str] = set()
    event_list_fields: set[str] = set()
    attribute_fields: set[str] = set()
    for row in rows:
        payload = json.loads(row["payload_json"])
        endpoint = row["endpoint"]
        by_endpoint.setdefault(endpoint, set()).update(payload.keys())
        for record in upload_records(payload):
            upload_record_fields.update(record.keys())
            event_list = record.get("eventList", [])
            if isinstance(event_list, list):
                for event in event_list:
                    if isinstance(event, dict):
                        event_list_fields.update(event.keys())
            attributes = record.get("attributes", [])
            if isinstance(attributes, list):
                for event in attributes:
                    if isinstance(event, dict):
                        attribute_fields.update(event.keys())

    return {
        "by_endpoint": {
            endpoint: sorted(fields)
            for endpoint, fields in sorted(by_endpoint.items())
        },
        "upload_records": sorted(upload_record_fields),
        "eventList": sorted(event_list_fields),
        "attributes": sorted(attribute_fields),
    }


def table_schema(table_name: str) -> list[dict[str, Any]]:
    rows = query_all(f"PRAGMA table_info({table_name})")
    return [
        {
            "name": row["name"],
            "type": row["type"],
            "not_null": bool(row["notnull"]),
            "default": row["dflt_value"],
            "primary_key": bool(row["pk"]),
        }
        for row in rows
    ]


def schema_report() -> dict[str, Any]:
    tables = [
        "devices",
        "raw_requests",
        "heartbeats",
        "count_uploads",
        "person_events",
        "receiver_sessions",
    ]
    return {
        "server_time": utc_now_iso(),
        "db_path": str(DB_PATH),
        "schema_owner": "custom_receiver",
        "important_note": (
            "The camera sends JSON payloads. The SQLite database schema is custom "
            "and was built by our receiver to preserve raw JSON and normalize "
            "dashboard/reporting fields."
        ),
        "tables": {table: table_schema(table) for table in tables},
        "source_of_truth": {
            "raw_json_table": "raw_requests",
            "raw_json_column": "payload_json",
            "reason": "All received camera fields are preserved here, even if a future firmware field is not normalized yet.",
        },
    }


def field_catalog_section(fields: dict[str, tuple[str, str]]) -> list[dict[str, str]]:
    return [
        {"field": field, "type": field_type, "meaning": meaning}
        for field, (field_type, meaning) in fields.items()
    ]


def data_catalog() -> dict[str, Any]:
    return {
        "server_time": utc_now_iso(),
        "db_path": str(DB_PATH),
        "camera_payload_format": "JSON",
        "camera_database_schema": None,
        "camera_database_schema_note": (
            "The camera does not send a database schema. It sends JSON objects to "
            "the configured HTTP endpoints."
        ),
        "observed_fields": observed_fields(),
        "field_catalog": {
            section: field_catalog_section(fields)
            for section, fields in CAMERA_PUSH_FIELD_CATALOG.items()
        },
        "storage_mapping": {
            "full_payload": "raw_requests.payload_json",
            "heartbeat_state": "heartbeats and devices",
            "count_windows": "count_uploads",
            "person_events": "person_events",
            "unknown_or_future_fields": "raw_requests.payload_json",
        },
    }


def integration_proof() -> dict[str, Any]:
    return {
        "server_time": utc_now_iso(),
        "result": "Camera push to our own server was validated.",
        "local_receiver": {
            "bind": f"{BIND_HOST}:{PORT}",
            "advertised": f"http://{PC_IP}:{PORT}",
            "db_path": str(DB_PATH),
            "demo_db_command": (
                "DB_PATH=hx_camera_demo.db DATA_MODE=Add CHILD_HEIGHT_CM=140 "
                "python3 camera_data_audit_receiver.py"
            ),
        },
        "camera_configuration": {
            "protocol": "HTTP locally, HTTPS for ngrok/public test",
            "format": "JSON",
            "data_api": "/api/camera/dataUpload",
            "heartbeat_api": "/api/camera/heartBeat",
            "data_scale": "Increment recommended",
            "supplement": "Enabled for per-person attributes[] data",
            "device_info": "Enabled for SN/MAC/firmware/network fields",
        },
        "ngrok_example": {
            "public_url_tested": "https://passivism-dimness-gigabyte.ngrok-free.dev",
            "forwarding": "public HTTPS -> local http://localhost:8088",
            "camera_server_address": "passivism-dimness-gigabyte.ngrok-free.dev",
            "camera_server_port": 443,
            "validation_endpoints": [
                "/health",
                "/api/status/current",
                "/api/debug/report",
                "/api/debug/requests",
                "/api/debug/uploads",
                "/api/debug/events",
            ],
        },
        "foorir_replacement_note": (
            "To stop sending data to Foorir, configure Address1 to our backend "
            "instead of the Foorir server. Use Address2 only for our own backup "
            "receiver if needed."
        ),
        "production_recommendation": {
            "backend": "Public HTTPS API with a stable domain.",
            "database": "PostgreSQL for production; SQLite is acceptable for lab/demo.",
            "security": "Restrict allowed devices by serial number and add network/API controls.",
        },
    }


def recent_raw_requests(limit: int = 20) -> list[dict[str, Any]]:
    rows = query_all(
        """
        SELECT id, received_at, endpoint, client_ip, sn, payload_hash, payload_json
        FROM raw_requests
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [
        {
            **{key: value for key, value in row.items() if key != "payload_json"},
            "payload": json.loads(row["payload_json"]),
        }
        for row in rows
    ]


def recent_uploads(limit: int = 20) -> list[dict[str, Any]]:
    return query_all(
        """
        SELECT id, received_at, client_ip, sn, camera_time, start_time, end_time,
               in_count, out_count, passby_count, turnback_count,
               avg_stay_time_ms, in_adult, out_adult, in_child, out_child,
               passby_adult, passby_child, turnback_adult, turnback_child,
               total, payload_hash, raw_request_id
        FROM count_uploads
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )


def recent_events(limit: int = 50) -> list[dict[str, Any]]:
    return query_all(
        """
        SELECT person_events.id, person_events.upload_id, count_uploads.sn,
               person_events.event_id, person_events.event_timestamp,
               person_events.event_type, person_events.height_cm,
               person_events.stay_time_ms, person_events.raw_json
        FROM person_events
        JOIN count_uploads ON count_uploads.id = person_events.upload_id
        ORDER BY person_events.id DESC
        LIMIT ?
        """,
        (limit,),
    )


def child_mode_report() -> dict[str, Any]:
    explicit = query_one(
        """
        SELECT
            COUNT(*) AS upload_rows,
            COALESCE(SUM(in_adult), 0) AS in_adult,
            COALESCE(SUM(out_adult), 0) AS out_adult,
            COALESCE(SUM(in_child), 0) AS in_child,
            COALESCE(SUM(out_child), 0) AS out_child,
            COALESCE(SUM(passby_adult), 0) AS passby_adult,
            COALESCE(SUM(passby_child), 0) AS passby_child,
            COALESCE(SUM(turnback_adult), 0) AS turnback_adult,
            COALESCE(SUM(turnback_child), 0) AS turnback_child,
            SUM(
                CASE
                    WHEN in_adult IS NOT NULL
                      OR out_adult IS NOT NULL
                      OR in_child IS NOT NULL
                      OR out_child IS NOT NULL
                      OR passby_adult IS NOT NULL
                      OR passby_child IS NOT NULL
                      OR turnback_adult IS NOT NULL
                      OR turnback_child IS NOT NULL
                    THEN 1 ELSE 0
                END
            ) AS rows_with_explicit_adult_child
        FROM count_uploads
        """
    ) or {}
    height_summary = query_one(
        """
        SELECT
            COUNT(*) AS person_event_rows,
            SUM(CASE WHEN height_cm > 0 THEN 1 ELSE 0 END) AS rows_with_height,
            MIN(NULLIF(height_cm, 0)) AS min_height_cm,
            MAX(NULLIF(height_cm, 0)) AS max_height_cm,
            ROUND(AVG(NULLIF(height_cm, 0)), 1) AS avg_height_cm,
            SUM(CASE WHEN height_cm > 0 AND height_cm < ? THEN 1 ELSE 0 END)
                AS inferred_child_events,
            SUM(CASE WHEN height_cm >= ? THEN 1 ELSE 0 END)
                AS inferred_adult_events
        FROM person_events
        """,
        (CHILD_HEIGHT_CM, CHILD_HEIGHT_CM),
    ) or {}
    event_types = query_all(
        """
        SELECT event_type, COUNT(*) AS rows
        FROM person_events
        GROUP BY event_type
        ORDER BY event_type
        """
    )
    recent_heights = query_all(
        """
        SELECT person_events.event_id, person_events.event_type,
               person_events.height_cm, person_events.stay_time_ms,
               count_uploads.received_at, count_uploads.sn
        FROM person_events
        JOIN count_uploads ON count_uploads.id = person_events.upload_id
        ORDER BY person_events.id DESC
        LIMIT 20
        """
    )
    fields = observed_fields()
    has_explicit = as_int(explicit.get("rows_with_explicit_adult_child")) > 0
    has_height = as_int(height_summary.get("rows_with_height")) > 0
    return {
        "server_time": utc_now_iso(),
        "db_path": str(DB_PATH),
        "child_height_threshold_cm": CHILD_HEIGHT_CM,
        "camera_explicit_adult_child_counts_seen": has_explicit,
        "height_based_child_classification_possible": has_height,
        "recommendation": (
            "Use camera-provided inAdult/outAdult/inChild/outChild fields."
            if has_explicit
            else (
                "Use attributes[].height with the configured threshold; this is height-based, not true age detection."
                if has_height
                else "Child mode is not proven yet; no explicit adult/child fields or height events have been captured."
            )
        ),
        "explicit_adult_child_totals": {
            "upload_rows": as_int(explicit.get("upload_rows")),
            "rows_with_explicit_adult_child": as_int(
                explicit.get("rows_with_explicit_adult_child")
            ),
            "in_adult": as_int(explicit.get("in_adult")),
            "out_adult": as_int(explicit.get("out_adult")),
            "in_child": as_int(explicit.get("in_child")),
            "out_child": as_int(explicit.get("out_child")),
            "passby_adult": as_int(explicit.get("passby_adult")),
            "passby_child": as_int(explicit.get("passby_child")),
            "turnback_adult": as_int(explicit.get("turnback_adult")),
            "turnback_child": as_int(explicit.get("turnback_child")),
        },
        "height_summary": {
            "person_event_rows": as_int(height_summary.get("person_event_rows")),
            "rows_with_height": as_int(height_summary.get("rows_with_height")),
            "min_height_cm": height_summary.get("min_height_cm"),
            "max_height_cm": height_summary.get("max_height_cm"),
            "avg_height_cm": height_summary.get("avg_height_cm"),
            "inferred_child_events": as_int(
                height_summary.get("inferred_child_events")
            ),
            "inferred_adult_events": as_int(
                height_summary.get("inferred_adult_events")
            ),
        },
        "event_type_distribution": event_types,
        "recent_height_events": recent_heights,
        "observed_child_mode_fields": {
            "upload_records": [
                field
                for field in fields["upload_records"]
                if field
                in (
                    "inAdult",
                    "outAdult",
                    "inChild",
                    "outChild",
                    "passbyAdult",
                    "passbyChild",
                    "turnbackAdult",
                    "turnbackChild",
                )
            ],
            "eventList": [
                field
                for field in fields["eventList"]
                if field in ("eventType", "height", "stayTime")
            ],
            "attributes": [
                field
                for field in fields["attributes"]
                if field in ("eventType", "height", "stayTime")
            ],
        },
    }


def capability_report() -> dict[str, Any]:
    fields = observed_fields()
    upload_fields = set(fields["upload_records"])
    event_list_fields = set(fields["eventList"])
    attribute_fields = set(fields["attributes"])
    per_person_fields = event_list_fields | attribute_fields
    return {
        "server_time": utc_now_iso(),
        "summary": dashboard_summary()["totals"],
        "observed_fields": fields,
        "capabilities_seen": {
            "heartbeat": "/api/camera/heartBeat" in fields["by_endpoint"],
            "data_upload": "/api/camera/dataUpload" in fields["by_endpoint"],
            "adult_child_counts": bool(
                {
                    "inAdult",
                    "outAdult",
                    "inChild",
                    "outChild",
                    "passbyAdult",
                    "passbyChild",
                    "turnbackAdult",
                    "turnbackChild",
                }
                & upload_fields
            ),
            "event_list": "eventList" in upload_fields,
            "attributes": "attributes" in upload_fields,
            "per_person_events": bool({"eventList", "attributes"} & upload_fields),
            "event_heights": "height" in per_person_fields,
            "event_stay_time": "stayTime" in per_person_fields,
            "event_types": "eventType" in per_person_fields,
            "historical_batch": "data" in fields["by_endpoint"].get(
                "/api/camera/dataUpload", []
            ),
        },
        "latest_payload": latest_payload(),
    }


def age_seconds(timestamp: str | None, now: datetime | None = None) -> int | None:
    parsed = parse_iso_timestamp(timestamp)
    if not parsed:
        return None
    reference = now or datetime.now(timezone.utc)
    return max(0, int((reference - parsed).total_seconds()))


def status_from_age(age: int | None) -> str:
    if age is None:
        return "offline"
    if age <= ONLINE_SECONDS:
        return "online"
    if age <= DELAYED_SECONDS:
        return "delayed"
    return "offline"


def current_status(now: datetime | None = None) -> dict[str, Any]:
    totals = count_totals()
    session = latest_session()
    active_session_totals = session_totals(session)
    latest_heartbeat = query_one(
        """
        SELECT received_at, camera_time
        FROM heartbeats
        ORDER BY id DESC
        LIMIT 1
        """
    )
    latest_device = query_one(
        """
        SELECT sn, first_seen_at, last_seen_at, last_client_ip,
               heartbeat_count, upload_count
        FROM devices
        ORDER BY last_seen_at DESC
        LIMIT 1
        """
    )
    latest = latest_payload()
    heartbeat_at = latest_heartbeat["received_at"] if latest_heartbeat else None
    heartbeat_age = age_seconds(heartbeat_at, now)
    upload_age = age_seconds(totals.get("last_upload_at"), now)
    latest_payload_body = latest["payload"] if latest else {}
    return {
        "server_time": utc_now_iso(),
        "receiver_config": receiver_config(),
        "device": latest_device,
        "status": status_from_age(heartbeat_age),
        "last_heartbeat_at": heartbeat_at,
        "last_heartbeat_age_seconds": heartbeat_age,
        "last_heartbeat_camera_time": (
            latest_heartbeat["camera_time"] if latest_heartbeat else None
        ),
        "last_upload_at": totals.get("last_upload_at"),
        "last_upload_age_seconds": upload_age,
        "totals": {
            "upload_rows": totals["upload_rows"],
            "in": totals["in"],
            "out": totals["out"],
            "passby": totals["passby"],
            "turnback": totals["turnback"],
            "estimated_onboard": totals["estimated_onboard"],
        },
        "all_time_totals": totals,
        "session": session,
        "session_totals": active_session_totals,
        "latest_payload_summary": {
            "received_at": latest["received_at"] if latest else None,
            "endpoint": latest["endpoint"] if latest else None,
            "client_ip": latest["client_ip"] if latest else None,
            "sn": latest_payload_body.get("sn"),
            "in": latest_payload_body.get("in"),
            "out": latest_payload_body.get("out"),
            "passby": latest_payload_body.get("passby"),
            "turnback": latest_payload_body.get("turnback"),
            "attributes_count": len(latest_payload_body.get("attributes", []) or []),
            "eventList_count": len(latest_payload_body.get("eventList", []) or []),
        },
    }


def receiver_config() -> dict[str, Any]:
    return {
        "bind_host": BIND_HOST,
        "advertised_ip": PC_IP,
        "port": PORT,
        "db_path": str(DB_PATH),
        "upload_interval_minutes": UPLOAD_INTERVAL_MINUTES,
        "data_mode": DATA_MODE,
        "timezone_offset": TIMEZONE_OFFSET,
        "child_height_threshold_cm": CHILD_HEIGHT_CM,
        "online_seconds": ONLINE_SECONDS,
        "delayed_seconds": DELAYED_SECONDS,
        "camera_endpoints": {
            "heartbeat": "/api/camera/heartBeat",
            "data_upload": "/api/camera/dataUpload",
        },
        "debug_endpoints": {
            "health": "/health",
            "current_status": "/api/status/current",
            "dashboard": "/api/dashboard",
            "report": "/api/debug/report",
            "requests": "/api/debug/requests",
            "uploads": "/api/debug/uploads",
            "events": "/api/debug/events",
            "fields": "/api/debug/fields",
            "child_mode": "/api/debug/child-mode",
            "session": "/api/debug/session",
            "session_reset": "/api/debug/session-reset",
            "schema": "/api/debug/schema",
            "data_catalog": "/api/debug/data-catalog",
            "integration_proof": "/api/debug/integration-proof",
        },
    }


def parse_limit(query: str, default: int, maximum: int) -> int:
    if "limit=" not in query:
        return default
    raw = query.split("limit=", 1)[1].split("&", 1)[0]
    return max(1, min(maximum, as_int(raw, default)))


class AuditReceiver(BaseHTTPRequestHandler):
    def log_message(self, *_: Any) -> None:
        return

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_payload(self) -> dict[str, Any]:
        length = as_int(self.headers.get("Content-Length"))
        if length <= 0 or length > MAX_BODY_BYTES:
            raise ValueError("invalid request size")
        payload = json.loads(self.rfile.read(length))
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/", "/api/dashboard"):
            self.send_json(dashboard_summary())
        elif path in ("/api/debug/latest", "/api/debug/latest-payloads"):
            self.send_json({"latest": latest_payload()})
        elif path == "/api/debug/fields":
            self.send_json(observed_fields())
        elif path == "/api/debug/report":
            self.send_json(capability_report())
        elif path == "/api/debug/requests":
            self.send_json(
                {"requests": recent_raw_requests(parse_limit(parsed.query, 20, 200))}
            )
        elif path == "/api/debug/uploads":
            self.send_json(
                {"uploads": recent_uploads(parse_limit(parsed.query, 20, 200))}
            )
        elif path == "/api/debug/events":
            self.send_json(
                {"events": recent_events(parse_limit(parsed.query, 50, 500))}
            )
        elif path == "/api/debug/child-mode":
            self.send_json(child_mode_report())
        elif path == "/api/debug/session":
            self.send_json(session_report())
        elif path == "/api/debug/schema":
            self.send_json(schema_report())
        elif path == "/api/debug/data-catalog":
            self.send_json(data_catalog())
        elif path == "/api/debug/integration-proof":
            self.send_json(integration_proof())
        elif path == "/api/status/current":
            self.send_json(current_status())
        elif path == "/api/config":
            self.send_json(receiver_config())
        elif path == "/health":
            self.send_json(
                {
                    "status": "ok",
                    "server_time": utc_now_iso(),
                    "receiver_config": receiver_config(),
                }
            )
        else:
            self.send_json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/debug/session-reset":
            self.send_json(create_session_reset())
            return

        if path not in ("/api/camera/heartBeat", "/api/camera/dataUpload"):
            self.send_json({"code": 2, "msg": "unknown endpoint"}, 404)
            return

        try:
            payload = self.read_payload()
            if path.endswith("/heartBeat"):
                record_heartbeat(path, self.client_address[0], payload)
            else:
                record_upload(path, self.client_address[0], payload)
            sn = str(payload.get("sn", "")).strip()
            data: dict[str, Any] = {"sn": sn, "time": unix_now()}
            if path.endswith("/heartBeat"):
                data.update(
                    {
                        "uploadInterval": UPLOAD_INTERVAL_MINUTES,
                        "dataMode": DATA_MODE,
                        "timezone": TIMEZONE_OFFSET,
                    }
                )
            self.send_json({"code": 0, "msg": "success", "data": data})
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json({"code": 2, "msg": str(error)}, 400)
        except sqlite3.Error as error:
            self.send_json({"code": 2, "msg": f"database error: {error}"}, 500)


def main() -> None:
    init_db()
    try:
        server = ThreadingHTTPServer((BIND_HOST, PORT), AuditReceiver)
    except OSError as error:
        raise SystemExit(f"Could not listen on {BIND_HOST}:{PORT}: {error}") from error

    print("HX-CCD22 DATA AUDIT RECEIVER")
    print(f"Listening          : http://{PC_IP}:{PORT}")
    print(f"Heartbeat endpoint : http://{PC_IP}:{PORT}/api/camera/heartBeat")
    print(f"Upload endpoint    : http://{PC_IP}:{PORT}/api/camera/dataUpload")
    print(f"Debug summary      : http://{PC_IP}:{PORT}/api/dashboard")
    print(f"Capability report  : http://{PC_IP}:{PORT}/api/debug/report")
    print(f"Recent raw JSON    : http://{PC_IP}:{PORT}/api/debug/requests")
    print(f"SQLite DB          : {DB_PATH}")
    print(f"Data mode reply    : {DATA_MODE}")
    print(f"Upload interval    : {UPLOAD_INTERVAL_MINUTES} minute(s)")
    print(f"Child threshold    : {CHILD_HEIGHT_CM} cm")
    print(f"Receiver config    : http://{PC_IP}:{PORT}/api/config")
    print(f"Child mode report  : http://{PC_IP}:{PORT}/api/debug/child-mode")
    print(f"Session report     : http://{PC_IP}:{PORT}/api/debug/session")
    print(f"Session reset      : POST http://{PC_IP}:{PORT}/api/debug/session-reset")
    print(f"DB schema report   : http://{PC_IP}:{PORT}/api/debug/schema")
    print(f"Data catalog       : http://{PC_IP}:{PORT}/api/debug/data-catalog")
    print(f"Integration proof  : http://{PC_IP}:{PORT}/api/debug/integration-proof")
    print("Point camera Address1 here to capture raw payloads.")
    print("Stop with Ctrl+C")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping receiver...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
