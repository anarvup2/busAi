# Architecture brief for builders

Condensed from *VV-Co Part A — Technical architecture* (Apurva Oza, 9 Oct 2026), now a Basecamp Doc: <https://app.basecamp.com/4531610/buckets/49226321/documents/10399548939>. That doc is the source of truth. Business requirements (pricing, KPIs, DPDP roles, risks) are in `docs/business-brief.md`. All figures are estimates the spikes must confirm.

## Chosen option per phase

| Phase | Build | Fallback |
| --- | --- | --- |
| 1 Manual video-vs-ticket | Stop-window clip store: server pulls the camera substream during stops; app plays clips with ticket and stop markers | SDK-direct playback from SD card if no substream and no gateway |
| 2 Nightly AI count | Server-side pull during stop windows + nightly GPU batch | On-bus clip gateway (Pi 5 / RK3568) for fleets whose SDK cannot serve a substream |
| 3 Dedicated counters | 2× FOORIR HX-CCD22 per bus pushing JSON to VV-Co's own ingest | Other sensors (Milesight VS133, Hikvision/Dahua/Streamax) behind the same counter contract |
| 4 Edge vision | RK3588 or Pi 5 + Hailo-8L box on existing cameras, Phase 2 model, MQTT out | Jetson Orin Nano Super where attributes are sold (out of scope here) |

## Components

| Component | Responsibility | Tech | Scale note (1,000 buses) |
| --- | --- | --- | --- |
| Katch events adapter | Ticket events + GPS from Katch in real time | Webhook or Kafka/Redpanda topic | 2–4 M tickets/day, ~50 M GPS points/day |
| Camera SDK adapter | One per vendor: substream, resolution/fps, SD playback, health | Python wrapping vendor SDK (RTSP where possible); creds in vault | 2,000 cameras; connect only during stop windows |
| Stop-window gate | GPS speed 0 for > 5 s + POS events → record windows | Stateless stream service; 3 s pre/post padding | Doors open 15–30% of the day |
| Clip recorder | Pull substream per window, write MP4, index by bus/trip/stop | FFmpeg workers; S3-compatible store, 30-day lifecycle | ~0.6 GB per bus-day; ~18 GB held per bus |
| Batch inference | Nightly detect, track, line-cross per clip → crossing events | PyTorch train; TensorRT/ONNX Runtime infer; ByteTrack; Celery/RabbitMQ or Argo | 1–2.5 GPU-min per bus-day; 3–5 L4-class GPUs for 8 h |
| Counter ingest | FOORIR heartbeat + dataUpload JSON; MQTT from edge boxes | HTTPS endpoints implementing the FOORIR API; EMQX/Mosquitto | Same crossing_event table |
| Reconciliation | Join crossings, tickets, stops; gaps per stop/trip/conductor; rank; flag | Python over Postgres; rules first, learned thresholds after pilot | Runs after inference, report by 07:00 |
| API and auth | REST, operator and manager roles, audit log of every clip view | FastAPI; Keycloak or Katch SSO | — |
| Reporting | Dashboard + one-page PDF per operator | React console; server-rendered PDF | — |
| Model registry and evaluation | Versioned models, ground-truth sets, accuracy per camera view | MLflow or object-storage versioning | Re-run on every model change |
| Observability | Device health, SDK availability, data per bus, job success | Prometheus, Grafana, alert on buses with no clips | — |
| Stores | Events and reconciliation in Postgres; clips in object storage | Postgres 16 (partition by day); S3-compatible (AWS Mumbai or MinIO) | TimescaleDB only if GPS queries get heavy |

Everything runs in an Indian cloud region (DPDP residency). GPU nodes are rented only at night.

## Data model

| Entity | Key fields | Notes |
| --- | --- | --- |
| operator | id, name, katch_operator_id, processor_agreement_ref, training_permitted, audit_policy_announced_on, plan, trial_ends_on | The DPDP data fiduciary; every operator-owned row carries operator_id under row-level security |
| vehicle | id, registration, operator_id, door_count, camera_layout | One row per bus |
| device | id, vehicle_id, kind (camera, counter, edge), vendor, model, door, credentials_ref, firmware, origin_country, certification_ref | Credentials only in the vault; origin and BIS R-number for tender reports |
| trip | id, vehicle_id, route_id, conductor_id, start_ts, end_ts | From Katch |
| stop_event | id, trip_id, stop_id, arrive_ts, depart_ts, dwell_s, lat, lon | From GPS; unit of reconciliation |
| ticket_event | id, trip_id, ts, stop_id, fare, count, conductor_id, source | From Katch POS, one row per ticket |
| clip | id, vehicle_id, device_id, stop_event_id, start_ts, end_ts, uri, fps, bytes | Object-storage key; 30-day lifecycle |
| crossing_event | id, vehicle_id, door, ts, direction (in/out), height_cm, track_id, confidence, source (ai_batch, counter, edge), model_version | Shared by all phases |
| stop_reconciliation | stop_event_id, boardings, alightings, tickets, gap, gap_pct, onboard_after | Recomputed nightly |
| flag | id, trip_id, reason, score, status, reviewer_id, decision, decided_at, clip_ids, est_leakage_inr, recovered_inr | Worked in the review screen; confirmed only by a human reviewer |
| ground_truth_count | stop_event_id, boardings, alightings, counter_id or annotator, method | Pilot only; feeds the harness |

Add `audit_log` (actor, action, object, ts) for clip access, and `review_session` (reviewer_id, operator_id, trip_id, started_at, ended_at) for the review-effort KPI.

## Katch → VV-Co event contract (JSON, webhook or topic)

| Event | Fields | Latency |
| --- | --- | --- |
| ticket.issued | ticket_id, vehicle, trip, conductor, ts (UTC, ms), stop_id or lat/lon, fare, pax_count, channel (cash, card, app) | ≤ 30 s for gating; batch fine for reconciliation |
| gps.position | vehicle, ts, lat, lon, speed_kmh, heading | 5–10 s interval; ≤ 30 s latency |
| trip.started / trip.ended | vehicle, trip, route, conductor, ts | Minutes |

## Camera adapter interface (one implementation per vendor SDK)

| Method | Returns | Used by |
| --- | --- | --- |
| get_live(device) | RTSP or SDK stream handle | Katch app live view |
| open_substream(device, w, h, fps) | Low-bitrate stream, or error if the SDK cannot set it | Clip recorder |
| fetch_playback(device, start, end) | MP4 of the SD-card recording, or unsupported | Clip recorder (night fetch) |
| set_time(device, ntp) / get_time(device) | Clock offset vs GPS | Health |
| health(device) | online, SD state, firmware, relay path (direct or vendor cloud) | Observability |

Target substream: 640×360 at 5–6 fps, ≤ 300 kbps.

**Fleet camera vendor: Warner.** Its H5 SDK is browser-only, reaches cameras through a vendor P2P relay, and cannot set sub-stream resolution or fps. We implement this interface through a headless-Chromium bridge; see `docs/vendor/warner-h5sdk.md`. `set_time` is an MQTT property write and is disabled unless approved.

## Counter-adapter contract (Phase 3 and 4 sources)

| Source | Transport | Mapped to |
| --- | --- | --- |
| FOORIR HX-CCD22 | HTTP POST `/api/camera/heartBeat` every minute and `/api/camera/dataUpload` with in, out, passby, turnback, avgStayTime and `eventList[]` (timestamp µs, eventType, height cm, stayTime) | One crossing_event per eventList item; door DI drives bus mode on the device |
| Other sensors (Milesight VS133/VS125, Hikvision, Dahua, Streamax) | MQTT or HTTP JSON per vendor | Same table; adapter normalises direction and timestamps |
| Phase 4 edge box | MQTT `vvco/{vehicle}/{door}/crossing`, QoS 1, offline buffer | Same table, source = edge |

FOORIR bus mode: DI takes a door-open contact (or a relay from the door solenoid), so counting runs only while the door is open. The device caches 90 days and resumes upload after an eSIM dropout. Rotate default credentials at commissioning, use HTTPS push, keep a device allow-list, disable "Map Collection".

## AI counting pipeline

| Stage | Design | Notes |
| --- | --- | --- |
| Input | 640×360 clips at 5–6 fps, one per stop per door camera | Crop to the door polygon (set once per bus layout); resize crop to 416 or 512 px |
| Detector | YOLO-nano class (YOLO11n / YOLOv8n / RT-DETR-tiny) for `head` and `person` on top-down and oblique door views | Start from COCO; fine-tune on 3–5k labelled pilot frames; label heads |
| Tracker | ByteTrack or OC-SORT on the head box centre | Tune for 5–6 fps: larger association window, lower second-pass confidence floor |
| Counting rule | Virtual line at the sill + inner zone; boarding when a track enters the inner zone after crossing from outside; alighting in reverse; cross-and-return within 3 s discarded | Door gating from the stop window stops counting while moving |
| Adult/child | Head-box size vs calibrated door geometry → height proxy; threshold ≈ 120 cm | Phase 3 counters give height for cross-checks |
| Drift control | Zero the onboard count at trip start and terminal stops; report per-stop balance, never accumulate blindly | |
| Output | crossing_event rows with ts, direction, height proxy, confidence, model_version, clip id | Deterministic re-runs for audits |
| Accuracy harness | Per-stop boarding and alighting error; VDV 457-style trip totals; split by camera view, crowding, day/night | Ground truth: manual counts of ≥ 100 stops + 2–4 FOORIR units |
| Throughput | ~150k frames per bus-day; 1,000–2,000 fps per L4 / RTX 4090 at 416 px with TensorRT and batching → 1.3–2.5 GPU-min per bus-day | CPU-only (OpenVINO, 16–32 cores) ≈ 10–15 min per bus-day; enough for a 10-bus pilot |
| Edge export (P4) | Same weights to RKNN (RK3588) or Hailo HEF (Hailo-8L), INT8 | Expect 1–2 points accuracy loss; re-check on the harness |

Targets before the pilot: ≥ 90% per-stop boardings on top-down views uncrowded, ≥ 80% crowded; flag threshold so ≥ 80% of flagged trips are confirmed.

## Gates

| Gate | Week | Pass condition | If it fails |
| --- | --- | --- | --- |
| G1 Access | 2 | SDK serves a 640×360 substream at ≤ 300 kbps; Katch events arrive within 30 s | Phase 1 ships with the clip gateway (option B) on the affected fleet |
| G2 First operator | 6 | One operator reviews flagged trips weekly on Phase 1 | Fix the ranking before building AI |
| G3 Accuracy | 18 | ≥ 85% per-stop boardings on top-down views; ≥ 80% flags confirmed | Add door cameras or move Phase 3 sensors to the lead |
| G4 Pricing | 22 | Pilot operator accepts ≥ ₹500 per bus-month or a success fee; recovered fares exceed price × 3 | Reposition as a tender-grade Phase 3 product |
