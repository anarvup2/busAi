# HX-CCD22 API Documentation

## 1. Overview

The HX-CCD22 is an on-device people-counting camera. It performs passenger counting on the device and sends count metadata to a configured backend using HTTP or HTTPS JSON push requests.

For a production bus dashboard, the recommended integration is:

```text
HX-CCD22 camera
  -> HTTPS ingestion API
  -> backend storage and aggregation
  -> fleet dashboard
```

The primary integration uses two HTTP push endpoints:

```text
POST /api/camera/heartBeat
POST /api/camera/dataUpload
```

The camera web interface also exposes local diagnostic APIs that can be useful during installation and support. These local APIs require direct access to the camera network and should not be used as the primary production ingestion path.

## 2. API Conventions

### Base URL

For production, configure the camera to use a public HTTPS backend:

```text
https://api.example.com
```

For local installation testing, the same paths can be hosted on a local receiver.

### Content Type

Camera push requests use JSON:

```http
Content-Type: application/json
```

### Authentication And Access Control

The camera push payload identifies the device using the `sn` serial number field. Production systems should combine this with:

- HTTPS with a valid certificate.
- A registered camera inventory.
- Rejection or quarantine of unknown serial numbers.
- Network controls or allowlisting where appropriate.
- Authentication for dashboards, admin tools, and debug/support endpoints.

If project-specific request authorization or token authentication is required, it should be added at the backend or confirmed with the final camera firmware and configuration tool.

## 3. Heartbeat API

The heartbeat endpoint lets the backend track camera connectivity and return basic reporting configuration.

```http
POST /api/camera/heartBeat
Content-Type: application/json
```

### Request Body

Example:

```json
{
  "sn": "HXCCD22-SERIAL-001",
  "time": 1783067673,
  "hostName": "CAMERA-001",
  "macAddress": "CAMERA-MAC-001",
  "hwPlatform": "HX-CCD22",
  "swRelease": "FIRMWARE-VERSION",
  "connectionType": "Wired",
  "ipAddress": "192.0.2.10",
  "ipAddressMethod": "DHCP",
  "timeZone": 5.5
}
```

### Request Fields

| Field | Type | Description |
| --- | --- | --- |
| `sn` | string | Camera serial number. Use this as the stable device identifier. |
| `time` | number | Camera timestamp. |
| `hostName` | string | Camera host name. |
| `macAddress` | string | Camera network MAC address. |
| `hwPlatform` | string | Hardware platform reported by the camera. |
| `swRelease` | string | Camera firmware/software release string. |
| `connectionType` | string | Network connection type, such as wired or wireless. |
| `ipAddress` | string | Camera-reported IP address. |
| `ipAddressMethod` | string | Addressing mode, such as DHCP or static. |
| `timeZone` | number | Camera timezone offset. |

### Success Response

Example:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "sn": "HXCCD22-SERIAL-001",
    "time": 1783067721,
    "uploadInterval": 1,
    "timezone": 5.5,
    "dataMode": "Add"
  }
}
```

### Response Fields

| Field | Type | Description |
| --- | --- | --- |
| `code` | number | `0` indicates success. Non-zero values should be treated as failed or rejected requests. |
| `msg` | string | Human-readable response message. |
| `data.sn` | string | Serial number acknowledged by the backend. |
| `data.time` | number | Backend timestamp returned to the camera. |
| `data.uploadInterval` | number | Requested upload interval in minutes. |
| `data.timezone` | number | Backend timezone offset. |
| `data.dataMode` | string | Recommended reporting mode. Use `Add` for incremental upload windows. |

### Usage Notes

- Use heartbeat freshness to determine whether a camera is online, delayed, or offline.
- Store the latest heartbeat separately from count uploads.
- Do not use heartbeat alone as proof that passenger count data is being received; monitor both heartbeat and upload freshness.

## 4. Data Upload API

The data upload endpoint receives passenger-counting records from the camera.

```http
POST /api/camera/dataUpload
Content-Type: application/json
```

### Request Body

Example:

```json
{
  "sn": "HXCCD22-SERIAL-001",
  "startTime": 1782742320,
  "endTime": 1782742380,
  "time": 1782742331,
  "in": 1,
  "out": 0,
  "passby": 1,
  "turnback": 0,
  "avgStayTime": 940,
  "len": 1,
  "inAdult": 1,
  "outAdult": 0,
  "inChild": 0,
  "outChild": 0,
  "passbyAdult": 1,
  "passbyChild": 0,
  "turnbackAdult": 0,
  "turnbackChild": 0,
  "connectionType": "Wired",
  "hostName": "CAMERA-001",
  "hwPlatform": "HX-CCD22",
  "swRelease": "FIRMWARE-VERSION",
  "ipAddress": "192.0.2.10",
  "ipAddressMethod": "DHCP",
  "macAddress": "CAMERA-MAC-001",
  "timeZone": 5.5,
  "attributes": [
    {
      "eventType": 0,
      "height": 167,
      "idIndex": 180588,
      "lineId": 0,
      "personId": 180588,
      "stayTime": 1200,
      "timeStamp": 1782742331000000
    }
  ]
}
```

### Count Fields

| Field | Type | Description |
| --- | --- | --- |
| `sn` | string | Camera serial number. |
| `startTime` | number | Start of the upload/statistics window. |
| `endTime` | number | End of the upload/statistics window. |
| `time` | number | Camera event or report timestamp. |
| `in` | number | Number of people entering during the window. |
| `out` | number | Number of people exiting during the window. |
| `passby` | number | Pass-by count. |
| `turnback` | number | Turnback count. |
| `avgStayTime` | number | Average dwell/stay time in milliseconds. |
| `len` | number | Number of per-person records included in `attributes`. |

### Adult And Child Count Fields

When adult/child classification is enabled, the upload can include aggregate category fields:

| Field | Type | Description |
| --- | --- | --- |
| `inAdult` | number | Adult-height entries. |
| `outAdult` | number | Adult-height exits. |
| `inChild` | number | Child-height entries. |
| `outChild` | number | Child-height exits. |
| `passbyAdult` | number | Adult-height pass-by count. |
| `passbyChild` | number | Child-height pass-by count. |
| `turnbackAdult` | number | Adult-height turnback count. |
| `turnbackChild` | number | Child-height turnback count. |

Adult/child analytics should be presented as height-based classification, not age detection.

### Device Fields

The upload can include the same device and network fields used by heartbeat:

| Field | Type | Description |
| --- | --- | --- |
| `hostName` | string | Camera host name. |
| `macAddress` | string | Camera MAC address. |
| `hwPlatform` | string | Hardware platform. |
| `swRelease` | string | Firmware/software release string. |
| `connectionType` | string | Network connection type. |
| `ipAddress` | string | Camera-reported IP address. |
| `ipAddressMethod` | string | DHCP/static addressing mode. |
| `timeZone` | number | Camera timezone offset. |

### Per-Person Attribute Fields

When supplementary/person attributes are enabled, the camera can include an `attributes` array:

| Field | Type | Description |
| --- | --- | --- |
| `attributes[].eventType` | number | Event type reported by the camera. |
| `attributes[].height` | number | Estimated person height in centimeters. |
| `attributes[].idIndex` | number | Event/person index. |
| `attributes[].lineId` | number | Counting line identifier. |
| `attributes[].personId` | number | Person identifier assigned by the device. |
| `attributes[].stayTime` | number | Stay/dwell time in milliseconds. |
| `attributes[].timeStamp` | number | Event timestamp. |

### Success Response

Example:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "sn": "HXCCD22-SERIAL-001",
    "time": 1783067721
  }
}
```

### Response Fields

| Field | Type | Description |
| --- | --- | --- |
| `code` | number | `0` indicates success. Non-zero values should be handled as failures. |
| `msg` | string | Human-readable response message. |
| `data.sn` | string | Serial number acknowledged by the backend. |
| `data.time` | number | Backend timestamp returned to the camera. |

### Usage Notes

- Use Increment/Add mode for production analytics so each upload represents a time window.
- Store the original JSON payload before normalization. This helps with support, audit, and firmware differences.
- Deduplicate retries using a payload hash or equivalent unique event strategy.
- Treat missing windows, delayed uploads, and duplicate requests as normal operating cases in mobile-network deployments.

## 5. Local Display Diagnostic API

The camera web interface exposes a local display-data API that can be useful during installation, calibration, and support. This API is intended for same-network diagnostics and should not be used as the main fleet ingestion path.

```http
POST /api/passengerFlow/passengerFlowData/DisplayDataGet
Content-Type: application/json;charset=utf-8
```

The request uses camera web-interface authorization headers generated by the camera UI or local diagnostic tool.

### Response Example

```json
{
  "enter": 225,
  "leave": 223,
  "pass": 15,
  "return": 115,
  "stay": 0,
  "stayTimePerPerson": 1.8070430755615234,
  "result": {
    "code": "0",
    "isError": "false",
    "message": "Display data retrieved successfully"
  }
}
```

### Display Fields

| Field | Description |
| --- | --- |
| `enter` | Camera website IN total. |
| `leave` | Camera website OUT total. |
| `pass` | Camera website pass-by total. |
| `return` | Camera website turnback total. |
| `stay` | Current stay/in-frame count. |
| `stayTimePerPerson` | Average stay time displayed by the camera website. |
| `result.*` | Request status object. |

The local display API is intended for installation and support comparison only. Production dashboards should use the backend-ingested push data described in Sections 3 and 4.

## 6. Backend Data Model Guidance

At minimum, the backend should store:

- Raw heartbeat payloads.
- Raw data upload payloads.
- Normalized camera/device records.
- Normalized count upload rows.
- Per-person attribute rows when `attributes` is enabled.
- Camera-to-bus mapping.
- Door position mapping.
- Aggregated hourly/daily summaries for reporting.

The camera payload includes the serial number `sn`, but it does not include bus ID, route ID, stop ID, or door position. Those values should be added by the backend using a camera registry.

Example mapping:

```text
camera_sn -> bus_id -> door_position -> route/trip/dashboard grouping
```

## 7. Limitations And Implementation Notes

- The HTTP push payload provides count metadata, not a live video stream.
- GPS, ticketing/payment data, passenger identity, bus ID, route ID, stop ID, and door position are not included in the camera push payload.
- Adult/child reporting should be treated as height-based classification.
- The local display API is useful for diagnostics, but production dashboards should rely on backend-ingested push data.
- Occupancy calculated as `IN - OUT` is an estimate and can drift after missed counts, resets, network delays, or passengers already onboard at trip start.
- Production systems should define trip start/reset rules before using occupancy as an operational KPI.
