# HX-CCD22 Fleet Counter Architecture

## 1. Overview

The HX-CCD22 fleet counter system uses camera-side passenger counting and backend-side aggregation. Each camera sends heartbeat and count data to a central backend. The backend stores raw payloads, normalizes count records, maps cameras to buses and doors, and serves analytics to the fleet dashboard.

Recommended production architecture:

```text
HX-CCD22 cameras
  -> bus LAN / router / mobile network
  -> public HTTPS ingestion API
  -> raw and normalized storage
  -> fleet analytics API
  -> dashboard and reports
```

This architecture avoids continuous video processing for passenger counting. The camera performs the counting locally and sends structured count metadata to the backend.

## 2. Production Data Flow

### 2.1 Camera To Backend

The camera is configured with the backend host, port, and API paths:

```text
POST /api/camera/heartBeat
POST /api/camera/dataUpload
```

The heartbeat endpoint is used for device connectivity and status monitoring. The data upload endpoint carries count windows, movement counts, adult/child category counts when enabled, and per-person attributes when enabled.

### 2.2 Backend Processing

The ingestion backend should:

- Accept JSON heartbeat and count upload requests.
- Store the original raw payload.
- Normalize heartbeat and upload rows.
- Normalize per-person attribute rows when included.
- Register and resolve the camera serial number to bus and door context.
- Deduplicate retry payloads.
- Detect missing or delayed upload windows.
- Expose dashboard and reporting APIs.

### 2.3 Dashboard And Reporting

The dashboard should query backend APIs rather than polling camera LAN addresses directly. This is important because deployed buses are typically behind private mobile routers.

Recommended dashboard views:

- Fleet overview.
- Bus detail.
- Camera/device detail.
- Count trends by hour, day, route, and bus.
- Adult/child split when enabled.
- Height and stay-time analytics when attributes are enabled.
- Device health and upload freshness.
- Export and reporting.

## 3. Camera Registry And Bus Mapping

The camera payload identifies the device using the serial number field `sn`. The backend should use this value to map each camera to operational context.

Recommended registry relationship:

```text
camera_sn -> bus_id -> door_position -> route/trip/dashboard grouping
```

Recommended camera registry fields:

| Field | Purpose |
| --- | --- |
| `camera_sn` | Serial number from the camera payload. |
| `bus_id` | Bus assigned to the camera. |
| `door_position` | Front, rear, middle, or custom door label. |
| `installation_height_cm` | Configured installation height. |
| `network_mode` | Wired, WiFi, or bus-router network mode. |
| `include_in_aggregation` | Whether the camera contributes to bus totals. |
| `status` | Active, inactive, maintenance, or retired. |
| `installed_at` | Installation date/time. |

The camera payload should not be expected to contain bus ID, route ID, stop ID, or door position. Those values belong in the backend registry or an external fleet/route system.

## 4. Aggregation Model

For a bus with multiple cameras, aggregate counts from all active cameras assigned to that bus.

Example:

```text
bus_in = sum(camera_in for active cameras on the bus)
bus_out = sum(camera_out for active cameras on the bus)
bus_passby = sum(camera_passby for active cameras on the bus)
bus_turnback = sum(camera_turnback for active cameras on the bus)
```

Fleet totals are calculated by aggregating bus totals:

```text
fleet_in = sum(bus_in for active buses)
fleet_out = sum(bus_out for active buses)
```

Occupancy can be estimated as:

```text
estimated_occupancy = max(0, bus_in - bus_out)
```

Occupancy should be treated as an operational estimate. Accurate occupancy reporting depends on installation quality, complete door coverage, trip start rules, reset behavior, and handling of missed or delayed uploads.

## 5. Storage Architecture

Production storage should keep both raw and normalized data.

Recommended storage categories:

| Category | Purpose |
| --- | --- |
| Raw heartbeat payloads | Audit trail and firmware-difference analysis. |
| Raw data upload payloads | Replay, debugging, and support. |
| Camera/device records | Latest known device metadata and heartbeat status. |
| Count upload rows | Normalized reporting windows. |
| Attribute rows | Per-person height, stay-time, and event metadata when enabled. |
| Camera registry | Camera-to-bus and camera-to-door mapping. |
| Aggregates | Hourly, daily, route, and fleet summaries. |
| Audit logs | Support and administrative traceability. |

PostgreSQL or an equivalent production database is recommended for fleet deployments. SQLite is suitable for prototypes but is not recommended for a multi-bus production system.

## 6. Backend API Layers

The production backend should separate ingestion APIs from dashboard APIs.

### 6.1 Ingestion APIs

These endpoints receive data from cameras:

```text
POST /api/camera/heartBeat
POST /api/camera/dataUpload
```

They should be optimized for reliability, idempotency, low latency, and safe retry handling.

### 6.2 Dashboard APIs

Dashboard APIs should be designed around fleet operations rather than raw camera payload shape.

Recommended API groups:

```text
GET /api/dashboard/fleet
GET /api/dashboard/buses/{bus_id}
GET /api/dashboard/cameras/{camera_sn}
GET /api/dashboard/reports
GET /api/dashboard/export.csv
```

These are recommended backend API shapes. They can be adapted to the final application framework and client reporting requirements.

### 6.3 Administrative APIs

Administrative APIs should be protected and limited to authorized users.

Recommended capabilities:

- Register camera.
- Assign camera to bus and door.
- Mark camera active/inactive.
- Update installation metadata.
- Review raw payloads for support.
- Export reports.

## 7. Health Monitoring

The dashboard should separate the following health states:

| Health signal | Description |
| --- | --- |
| Heartbeat status | Whether the camera is regularly reaching the backend. |
| Upload status | Whether count data is arriving on schedule. |
| Device metadata | Latest camera-reported network and firmware details. |
| Backend ingestion status | Whether the ingestion service is accepting requests. |
| Stream status | Optional, only if a separate video feature is implemented. |

Recommended status model:

- **Online**: recent heartbeat and recent upload.
- **Delayed**: heartbeat or upload is stale but not yet considered offline.
- **Offline**: heartbeat and upload are missing beyond the configured threshold.
- **Misconfigured**: camera serial number is unknown or not assigned to a bus.

## 8. Local Diagnostic Access

During installation and support, technicians may use the camera web interface or local diagnostic tools to compare camera website totals with backend totals.

Local diagnostic access can include:

- Camera web dashboard.
- Display-data API exposed by the camera web interface.
- Local stream or ONVIF checks when video troubleshooting is required.

These local diagnostics require access to the camera network and should not replace backend push ingestion for production fleet reporting.

## 9. Deployment Boundaries

The HTTP push integration provides passenger-count metadata. It should not be treated as a source for:

- Live video.
- Images.
- GPS location.
- Passenger identity.
- Ticketing or payment records.
- Route, stop, or trip assignment.

Those capabilities should come from separate systems or separately confirmed camera features.

## 10. Production Security Recommendations

Production deployment should include:

- HTTPS with a valid certificate.
- Camera serial-number registry.
- Unknown-camera rejection or quarantine.
- Dashboard user authentication.
- Administrative role separation.
- Restricted access to raw payload and support tools.
- Database backups.
- Monitoring and alerting for ingestion failures.
- Firewall rules for public services.

If stronger camera authentication is required, confirm the final authentication mechanism with the selected firmware, backend, and deployment network.

## 11. Rollout Sequence

Recommended rollout approach:

1. Configure and confirm one camera in a controlled environment.
2. Confirm heartbeat and data upload through the backend.
3. Confirm camera-to-bus mapping and dashboard totals.
4. Install and confirm both doors on one pilot bus.
5. Define trip/reset rules with operations.
6. Run a pilot period with raw payload retention enabled.
7. Review accuracy, network reliability, and dashboard behavior.
8. Roll out to the remaining fleet in batches.
