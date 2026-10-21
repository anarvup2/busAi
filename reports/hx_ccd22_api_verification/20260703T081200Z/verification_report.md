# HX-CCD22 API Verification Report

Generated UTC: `2026-07-03T08:12:00+00:00`

## Inputs

| Setting | Value |
| --- | --- |
| camera_base | http://172.16.17.50 |
| receiver_base | http://172.16.16.118:8088 |
| dashboard_base | http://172.16.16.118:8089 |
| observe_seconds | 0 |
| include_private_camera_apis | True |
| allow_reset | False |
| redact | True |

## Endpoint Results

| Name | Classification | Method | Status | OK | ms | Body | JSON keys | Saved response | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| receiver_health | receiver prototype/debug | GET | no response | no | 1 | none |  |  | <urlopen error [Errno 111] Connection refused> |
| receiver_api_config | receiver prototype/debug | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 111] Connection refused> |
| receiver_api_status_current | receiver prototype/debug | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 111] Connection refused> |
| receiver_api_dashboard | receiver prototype/debug | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 111] Connection refused> |
| receiver_api_debug_report | receiver prototype/debug | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 111] Connection refused> |
| receiver_api_debug_requests | receiver prototype/debug | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 111] Connection refused> |
| receiver_api_debug_uploads | receiver prototype/debug | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 111] Connection refused> |
| receiver_api_debug_events | receiver prototype/debug | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 111] Connection refused> |
| receiver_api_debug_fields | receiver prototype/debug | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 111] Connection refused> |
| receiver_api_debug_child-mode | receiver prototype/debug | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 111] Connection refused> |
| dashboard_health | dashboard mirror/prototype | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 111] Connection refused> |
| dashboard_api_camera-total | dashboard mirror/prototype | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 111] Connection refused> |
| dashboard_api_dashboard_fleet | dashboard mirror/prototype | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 111] Connection refused> |
| dashboard_api_dashboard_buses_B-101 | dashboard mirror/prototype | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 111] Connection refused> |
| dashboard_api_dashboard_export.csv | dashboard mirror/prototype | GET | no response | no | 0 | none |  |  | <urlopen error [Errno 111] Connection refused> |
| camera_display_data_get | lab-only/private diagnostic | POST | 200 | yes | 19 | json | age, enter, gender, leave, pass, result, return, stay, stayTimePerPerson, workcard | responses/camera_display_data_get.json |  |
| camera_webrtc_probe | lab-only/private diagnostic | GET | 200 | yes | 12 | json | code, msg | responses/camera_webrtc_probe.json |  |
| camera_rtc_client_js | lab-only/private diagnostic | GET | 200 | yes | 34 | text |  | responses/camera_rtc_client_js.txt |  |
| camera_private_reset | lab-only/private reset control | POST | no response | no | 0 | skipped |  |  |  |

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
| private_display_response | enter | verified live |
| private_display_response | leave | verified live |
| private_display_response | pass | verified live |
| private_display_response | return | verified live |
| private_display_response | stay | verified live |
| private_display_response | stayTimePerPerson | verified live |
| unsupported_without_future_evidence | age | unexpectedly observed; review docs before publishing |
| unsupported_without_future_evidence | gender | unexpectedly observed; review docs before publishing |
| unsupported_without_future_evidence | workcard | unexpectedly observed; review docs before publishing |
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
