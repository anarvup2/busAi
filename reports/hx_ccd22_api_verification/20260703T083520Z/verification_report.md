# HX-CCD22 API Verification Report

Generated UTC: `2026-07-03T08:37:21+00:00`

## Inputs

| Setting | Value |
| --- | --- |
| camera_base | http://<redacted-ip> |
| receiver_base | http://<redacted-ip>:8088 |
| dashboard_base | http://<redacted-ip>:8089 |
| observe_seconds | 120 |
| include_private_camera_apis | True |
| allow_reset | False |
| redact | True |

## Endpoint Results

| Name | Classification | Method | Status | OK | ms | Body | JSON keys | Saved response | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| receiver_health | receiver prototype/debug | GET | 200 | yes | 3 | json | receiver_config, server_time, status | responses/receiver_health.json |  |
| receiver_api_config | receiver prototype/debug | GET | 200 | yes | 0 | json | advertised_ip, bind_host, camera_endpoints, child_height_threshold_cm, data_mode, db_path, debug_endpoints, delayed_seconds, online_seconds, port, timezone_offset, upload_interval_minutes | responses/receiver_api_config.json |  |
| receiver_api_status_current | receiver prototype/debug | GET | 200 | yes | 3 | json | all_time_totals, device, last_heartbeat_age_seconds, last_heartbeat_at, last_heartbeat_camera_time, last_upload_age_seconds, last_upload_at, latest_payload_summary, receiver_config, server_time, session, session_totals, status, totals | responses/receiver_api_status_current.json |  |
| receiver_api_dashboard | receiver prototype/debug | GET | 200 | yes | 1 | json | db_path, devices, latest_payload, server_time, totals | responses/receiver_api_dashboard.json |  |
| receiver_api_debug_report | receiver prototype/debug | GET | 200 | yes | 3 | json | capabilities_seen, latest_payload, observed_fields, server_time, summary | responses/receiver_api_debug_report.json |  |
| receiver_api_debug_requests | receiver prototype/debug | GET | 200 | yes | 1 | json | requests | responses/receiver_api_debug_requests.json |  |
| receiver_api_debug_uploads | receiver prototype/debug | GET | 200 | yes | 1 | json | uploads | responses/receiver_api_debug_uploads.json |  |
| receiver_api_debug_events | receiver prototype/debug | GET | 200 | yes | 1 | json | events | responses/receiver_api_debug_events.json |  |
| receiver_api_debug_fields | receiver prototype/debug | GET | 200 | yes | 1 | json | attributes, by_endpoint, eventList, upload_records | responses/receiver_api_debug_fields.json |  |
| receiver_api_debug_child-mode | receiver prototype/debug | GET | 200 | yes | 3 | json | camera_explicit_adult_child_counts_seen, child_height_threshold_cm, db_path, event_type_distribution, explicit_adult_child_totals, height_based_child_classification_possible, height_summary, observed_child_mode_fields, recent_height_events, recommendation, server_time | responses/receiver_api_debug_child-mode.json |  |
| receiver_synthetic_heartbeat | receiver camera-push contract | POST | 200 | yes | 6 | json | code, data, msg | responses/receiver_synthetic_heartbeat.json |  |
| receiver_synthetic_data_upload | receiver camera-push contract | POST | 200 | yes | 10 | json | code, data, msg | responses/receiver_synthetic_data_upload.json |  |
| dashboard_health | dashboard mirror/prototype | GET | 200 | yes | 0 | json | camera_online, last_camera_poll, poll_error, status | responses/dashboard_health.json |  |
| dashboard_api_camera-total | dashboard mirror/prototype | GET | 200 | yes | 0 | json | avg_stay_time_seconds, camera_ip, current_stay, display_endpoint, estimated_onboard, in, last_camera_poll, last_client_ip, last_heartbeat, last_heartbeat_device_time, last_poll_error, last_push_upload, last_sample_minute, last_sn, latest_push_payload, net_count, online, out, passby, poll_successes, push_messages, rtc_client_url, server_time, session_samples, source, stream_available, turnback, webrtc_url | responses/dashboard_api_camera-total.json |  |
| dashboard_api_dashboard_fleet | dashboard mirror/prototype | GET | 200 | yes | 0 | json | buses, totals | responses/dashboard_api_dashboard_fleet.json |  |
| dashboard_api_dashboard_buses_B-101 | dashboard mirror/prototype | GET | 200 | yes | 0 | json | cameras, capacity, id, name, number, path, route, session_samples, status, totals | responses/dashboard_api_dashboard_buses_B-101.json |  |
| dashboard_api_dashboard_export.csv | dashboard mirror/prototype | GET | 200 | yes | 0 | text |  | responses/dashboard_api_dashboard_export.csv.txt |  |
| camera_display_data_get | lab-only/private diagnostic | POST | 200 | yes | 8 | json | age, enter, gender, leave, pass, result, return, stay, stayTimePerPerson, workcard | responses/camera_display_data_get.json |  |
| camera_webrtc_probe | lab-only/private diagnostic | GET | 200 | yes | 17 | json | code, msg | responses/camera_webrtc_probe.json |  |
| camera_rtc_client_js | lab-only/private diagnostic | GET | 200 | yes | 35 | text |  | responses/camera_rtc_client_js.txt |  |
| camera_private_reset | lab-only/private reset control | POST | no response | no | 0 | skipped |  |  |  |
| observation_before_fields | receiver observation | GET | 200 | yes | 2 | json | attributes, by_endpoint, eventList, upload_records | responses/observation_before_fields.json |  |
| observation_after_fields | receiver observation | GET | 200 | yes | 32 | json | attributes, by_endpoint, eventList, upload_records | responses/observation_after_fields.json |  |
| observation_after_recent_requests | receiver observation | GET | 200 | yes | 1 | json | requests | responses/observation_after_recent_requests.json |  |

## Field Verification

| Group | Field | Status |
| --- | --- | --- |
| heartbeat_push_payload | connectionType | observed in receiver payloads |
| heartbeat_push_payload | hostName | observed in receiver payloads |
| heartbeat_push_payload | hwPlatform | observed in receiver payloads |
| heartbeat_push_payload | ipAddress | observed in receiver payloads |
| heartbeat_push_payload | ipAddressMethod | observed in receiver payloads |
| heartbeat_push_payload | macAddress | observed in receiver payloads |
| heartbeat_push_payload | sn | observed in receiver payloads |
| heartbeat_push_payload | swRelease | observed in receiver payloads |
| heartbeat_push_payload | time | observed in receiver payloads |
| heartbeat_push_payload | timeZone | observed in receiver payloads |
| data_upload_payload | attributes | observed in receiver payloads |
| data_upload_payload | avgStayTime | observed in receiver payloads |
| data_upload_payload | endTime | observed in receiver payloads |
| data_upload_payload | eventList | not observed in this run |
| data_upload_payload | in | observed in receiver payloads |
| data_upload_payload | inAdult | observed in receiver payloads |
| data_upload_payload | inChild | observed in receiver payloads |
| data_upload_payload | len | observed in receiver payloads |
| data_upload_payload | out | observed in receiver payloads |
| data_upload_payload | outAdult | observed in receiver payloads |
| data_upload_payload | outChild | observed in receiver payloads |
| data_upload_payload | passby | observed in receiver payloads |
| data_upload_payload | passbyAdult | observed in receiver payloads |
| data_upload_payload | passbyChild | observed in receiver payloads |
| data_upload_payload | sn | observed in receiver payloads |
| data_upload_payload | startTime | observed in receiver payloads |
| data_upload_payload | time | observed in receiver payloads |
| data_upload_payload | total | not observed in this run |
| data_upload_payload | turnback | observed in receiver payloads |
| data_upload_payload | turnbackAdult | observed in receiver payloads |
| data_upload_payload | turnbackChild | observed in receiver payloads |
| attributes_payload | eventType | observed in receiver payloads |
| attributes_payload | height | observed in receiver payloads |
| attributes_payload | idIndex | observed in receiver payloads |
| attributes_payload | lineId | observed in receiver payloads |
| attributes_payload | personId | observed in receiver payloads |
| attributes_payload | stayTime | observed in receiver payloads |
| attributes_payload | timeStamp | observed in receiver payloads |
| event_list_payload | eventType | not observed in this run |
| event_list_payload | height | not observed in this run |
| event_list_payload | id | not observed in this run |
| event_list_payload | stayTime | not observed in this run |
| event_list_payload | timestamp | not observed in this run |
| private_display_response | age | verified live |
| private_display_response | enter | verified live |
| private_display_response | gender | verified live |
| private_display_response | leave | verified live |
| private_display_response | pass | verified live |
| private_display_response | result | verified live |
| private_display_response | return | verified live |
| private_display_response | stay | verified live |
| private_display_response | stayTimePerPerson | verified live |
| private_display_response | workcard | verified live |
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
  "after_fields_available": true,
  "after_keys": "<redacted>",
  "before_fields_available": true,
  "before_keys": "<redacted>",
  "observe_seconds": 120,
  "ran": true,
  "recent_requests_available": true
}
```

## Notes

- `/api/camera/heartBeat` and `/api/camera/dataUpload` are receiver endpoints. The camera normally calls these endpoints; this script can also send synthetic zero-count contract payloads to verify receiver behavior.
- Private camera APIs require same-LAN camera access and are not production ingestion APIs.
- Reset is skipped unless `--allow-reset` is provided.
- A failed endpoint is still evidence: it should be documented as unavailable or unverified for that run.
