# HX-CCD22 API Verification Report

Generated UTC: `2026-07-03T08:09:15+00:00`

## Inputs

| Setting | Value |
| --- | --- |
| camera_base | http://172.16.17.50 |
| receiver_base | http://172.16.16.118:8088 |
| dashboard_base | http://172.16.16.118:8089 |
| observe_seconds | 0 |
| include_private_camera_apis | False |
| allow_reset | False |
| redact | True |

## Endpoint Results

| Name | Classification | Method | Status | OK | ms | Body | JSON keys | Saved response | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| receiver_health | receiver prototype/debug | GET | no response | no | 3 | none |  |  | <urlopen error [Errno 1] Operation not permitted> |
| receiver_api_config | receiver prototype/debug | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 1] Operation not permitted> |
| receiver_api_status_current | receiver prototype/debug | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 1] Operation not permitted> |
| receiver_api_dashboard | receiver prototype/debug | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 1] Operation not permitted> |
| receiver_api_debug_report | receiver prototype/debug | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 1] Operation not permitted> |
| receiver_api_debug_requests | receiver prototype/debug | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 1] Operation not permitted> |
| receiver_api_debug_uploads | receiver prototype/debug | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 1] Operation not permitted> |
| receiver_api_debug_events | receiver prototype/debug | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 1] Operation not permitted> |
| receiver_api_debug_fields | receiver prototype/debug | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 1] Operation not permitted> |
| receiver_api_debug_child-mode | receiver prototype/debug | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 1] Operation not permitted> |
| receiver_synthetic_heartbeat | receiver camera-push contract | POST | no response | no | 0 | none |  |  | <urlopen error [Errno 1] Operation not permitted> |
| receiver_synthetic_data_upload | receiver camera-push contract | POST | no response | no | 0 | none |  |  | <urlopen error [Errno 1] Operation not permitted> |
| dashboard_health | dashboard mirror/prototype | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 1] Operation not permitted> |
| dashboard_api_camera-total | dashboard mirror/prototype | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 1] Operation not permitted> |
| dashboard_api_dashboard_fleet | dashboard mirror/prototype | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 1] Operation not permitted> |
| dashboard_api_dashboard_buses_B-101 | dashboard mirror/prototype | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 1] Operation not permitted> |
| dashboard_api_dashboard_export.csv | dashboard mirror/prototype | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 1] Operation not permitted> |

## Field Verification

| Group | Field | Status |
| --- | --- | --- |
| heartbeat_push_payload | connectionType | not observed in this run |
| heartbeat_push_payload | hostName | not observed in this run |
| heartbeat_push_payload | hwPlatform | not observed in this run |
| heartbeat_push_payload | ipAddress | not observed in this run |
| heartbeat_push_payload | ipAddressMethod | not observed in this run |
| heartbeat_push_payload | macAddress | not observed in this run |
| heartbeat_push_payload | sn | not observed in this run |
| heartbeat_push_payload | swRelease | not observed in this run |
| heartbeat_push_payload | time | not observed in this run |
| heartbeat_push_payload | timeZone | not observed in this run |
| data_upload_payload | attributes | not observed in this run |
| data_upload_payload | avgStayTime | not observed in this run |
| data_upload_payload | endTime | not observed in this run |
| data_upload_payload | eventList | not observed in this run |
| data_upload_payload | in | not observed in this run |
| data_upload_payload | inAdult | not observed in this run |
| data_upload_payload | inChild | not observed in this run |
| data_upload_payload | len | not observed in this run |
| data_upload_payload | out | not observed in this run |
| data_upload_payload | outAdult | not observed in this run |
| data_upload_payload | outChild | not observed in this run |
| data_upload_payload | passby | not observed in this run |
| data_upload_payload | passbyAdult | not observed in this run |
| data_upload_payload | passbyChild | not observed in this run |
| data_upload_payload | sn | not observed in this run |
| data_upload_payload | startTime | not observed in this run |
| data_upload_payload | time | not observed in this run |
| data_upload_payload | total | not observed in this run |
| data_upload_payload | turnback | not observed in this run |
| data_upload_payload | turnbackAdult | not observed in this run |
| data_upload_payload | turnbackChild | not observed in this run |
| attributes_payload | eventType | not observed in this run |
| attributes_payload | height | not observed in this run |
| attributes_payload | idIndex | not observed in this run |
| attributes_payload | lineId | not observed in this run |
| attributes_payload | personId | not observed in this run |
| attributes_payload | stayTime | not observed in this run |
| attributes_payload | timeStamp | not observed in this run |
| event_list_payload | eventType | not observed in this run |
| event_list_payload | height | not observed in this run |
| event_list_payload | id | not observed in this run |
| event_list_payload | stayTime | not observed in this run |
| event_list_payload | timestamp | not observed in this run |
| private_display_response | enter | lab-only/private; not observed in this run |
| private_display_response | leave | lab-only/private; not observed in this run |
| private_display_response | pass | lab-only/private; not observed in this run |
| private_display_response | return | lab-only/private; not observed in this run |
| private_display_response | stay | lab-only/private; not observed in this run |
| private_display_response | stayTimePerPerson | lab-only/private; not observed in this run |
| unsupported_without_future_evidence | age | unsupported/removed |
| unsupported_without_future_evidence | gender | unsupported/removed |
| unsupported_without_future_evidence | workcard | unsupported/removed |
| vendor_documented_unobserved_payloads | currentStay | official vendor-documented but unobserved in this run |
| vendor_documented_unobserved_payloads | data | official vendor-documented but unobserved in this run |
| vendor_documented_unobserved_payloads | data.avgStayTime | official vendor-documented but unobserved in this run |
| vendor_documented_unobserved_payloads | data.endTime | official vendor-documented but unobserved in this run |
| vendor_documented_unobserved_payloads | data.in | official vendor-documented but unobserved in this run |
| vendor_documented_unobserved_payloads | data.out | official vendor-documented but unobserved in this run |
| vendor_documented_unobserved_payloads | data.passby | official vendor-documented but unobserved in this run |
| vendor_documented_unobserved_payloads | data.startTime | official vendor-documented but unobserved in this run |
| vendor_documented_unobserved_payloads | data.time | official vendor-documented but unobserved in this run |
| vendor_documented_unobserved_payloads | data.turnback | official vendor-documented but unobserved in this run |
| vendor_documented_unobserved_payloads | info | official vendor-documented but unobserved in this run |
| vendor_documented_unobserved_payloads | info.height | official vendor-documented but unobserved in this run |
| vendor_documented_unobserved_payloads | info.id | official vendor-documented but unobserved in this run |
| vendor_documented_unobserved_payloads | info.status | official vendor-documented but unobserved in this run |
| vendor_documented_unobserved_payloads | info.staytime | official vendor-documented but unobserved in this run |

## Observation Summary

```json
{
  "observe_seconds": 0,
  "ran": false
}
```

## Notes

- `/api/camera/heartBeat` and `/api/camera/dataUpload` are receiver endpoints. The camera normally calls these endpoints; this script can also send synthetic zero-count contract payloads to verify receiver behavior.
- Private camera APIs require same-LAN camera access and are not production ingestion APIs.
- Reset is skipped unless `--allow-reset` is provided.
- A failed endpoint is still evidence: it should be documented as unavailable or unverified for that run.
