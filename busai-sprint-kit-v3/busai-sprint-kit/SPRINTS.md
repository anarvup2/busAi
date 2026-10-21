# Sprints

> Generated from `backlog.yaml`. Human-facing plan: https://claude.ai/code/artifact/c6a73b2f-8fd0-4423-b280-ea61f11c69a1

## Human inputs

| ID | Needed by | Status | Input |
| --- | --- | --- | --- |
| H-01 | 2026-10-16 | todo | Order 2–4 FOORIR HX-CCD22 counters and 2 edge kits (Pi 5 + AI Kit or RK3588, 9–36 V DC-DC, enclosure); record FOORIR's quote, MOQ, lead time, warranty text and BIS R-number |
| H-02 | 2026-10-19 | todo | Pilot access: Warner cloud account + device IDs and device passwords for the 6 cameras on 3 pilot buses; Katch sandbox/topic (Parth); all injected as env vars; Warner SDK zip in the private bucket |
| H-03 | 2026-10-19 | todo | Cloud account in an Indian region with budget cap; staging-only deploy role; night GPU quota |
| H-04 | 2026-10-19 | todo | One day of Katch events for 3 buses, exported by Parth |
| H-05 | 2026-10-23 | todo | Pilot operator named (10 buses, routes, city); operator letter; DPDP processor agreement signed between VV-Co and the operator (signatory decided); notice stickers on 10 buses; operator announces the audit policy to conductors; sign the data-flow note |
| H-06 | 2026-10-26 | todo | Two depot managers review flagged trips weekly |
| H-07 | 2026-10-26 | todo | Ground truth: >=100 stops counted by people in the tool, each twice |
| H-08 | 2026-10-28 | todo | Parth embeds the review WebView + SSO in the Katch Android app |
| H-09 | 2026-10-28 | todo | Check ~10% of auto-labels (~400 frames) |
| H-10 | 2026-11-04 | todo | Fit FOORIR units (door contact on DI); run the commissioning script |
| H-11 | 2026-11-06 | todo | BIS CRS / ER-01 advice on the depth-only counter SKU |
| H-12 | after G3 | todo | Fit edge boxes on two pilot buses |
| H-13 | every Friday | todo | Review and merge the sprint branch; G1–G4 calls and GPU choice from evidence packs |
| H-14 | 2026-10-21 | todo | Warner answers: relay and cloud hosting location, settable sub-stream encoder, server-side SDK or RTSP, token rotation, LAN password derivation, limited-scope account (questions in docs/vendor/warner-h5sdk.md) |
| H-15 | 2026-10-22 | todo | Run tools/commission_warner.py --apply on the 6 pilot cameras: set device passwords, alarm push off, on-camera boxes off, audio off, continuous sub-stream SD recording on |
| H-16 | 2026-10-21 | todo | eSIM data plan per pilot bus today and the cost of ~16–20 GB/month if it is smaller (Parth); the biggest lever on cost per bus |
| H-17 | 2026-10-21 | todo | Camera positions per bus type on the pilot fleet: does either camera see a door from above? A photo of each view and the door count per bus (Parth) |
| H-18 | 2026-10-23 | todo | Pilot success metrics agreed with the pilot operator before deployment, as the charter requires: VDV 457-style per-stop protocol, 85 % / 95 % thresholds, KPI targets in docs/business-brief.md (KParth + Upsquare) |
| H-19 | 2026-11-06 | todo | Pricing inputs for G4: Katch's current per-bus subscription to operators, and the pilot pricing hypothesis (per bus-month, share of recovered fares, or both) |
| H-20 | 2026-10-26 | todo | Shareholders' agreement points that change the code: operator permission (in the processor agreement) to train models on its footage; VV-Co owns the IP created for it; licence terms for pre-existing Katch and Upsquare code |
| H-21 | after G1 | todo | Extend read-only pilot access from 3 to all 10 pilot buses and commission their cameras (H-15 steps); KPI: 10 buses live by week 12 |

## S1 — Phase 1 — clips and manual review (2026-10-19 → 2026-10-23)

Goal: Pilot buses record a clip at every stop; a manager can review a trip against ticket ticks; G1 evidence pack ready Friday

| ID | Status | Task | Needs input | Done when |
| --- | --- | --- | --- | --- |
| [S1-01](tasks/S1-01.md) | todo | Scaffold: Python 3.12 monorepo, docker-compose, CI, secret scanning, Terraform for staging in an Indian region | H-03 | make dev green; staging deploys |
| [S1-02](tasks/S1-02.md) | todo | Schema v0: the 10 entities plus operator, audit_log and review_session; operator-scoped rows; event tables partitioned by day, idempotent natural keys | — | Migrations apply up and down |
| [S1-03](tasks/S1-03.md) | todo | Contracts as code: Katch events, CameraAdapter, counter contract, MQTT topic | — | Every fixture validates |
| [S1-04](tasks/S1-04.md) | todo | Simulators: Katch replayer, fake Warner camera serving frame dumps, FOORIR device with dropout and backfill | H-04 | A fixture day replays at 60x |
| [S1-05](tasks/S1-05.md) | todo | G1 spike runners through the Warner bridge: sub-stream reality, time to first frame, relay path, SD playback, clock, posture, Katch latency | H-02, H-14, H-16, H-17 | G1 evidence pack on Friday |
| [S1-06](tasks/S1-06.md) | todo | Katch events adapter: webhook with signature check or topic consumer, idempotent upserts | H-02 | Replayed day, zero duplicates |
| [S1-07](tasks/S1-07.md) | todo | Stop-window gate: pre-connect on deceleration, window at speed 0 for > 5 s or POS events, 3 s padding, stop_event with dwell | — | >=95% of Katch stops matched |
| [S1-08](tasks/S1-08.md) | todo | Warner camera adapter over the bridge; clip recorder (remux, no decode) with 30-day lifecycle and overnight SD fill | H-02, H-05, H-15 | One clip per window on pilot buses |
| [S1-09](tasks/S1-09.md) | todo | API and auth: roles, signed clip URLs, audit row per clip view | — | Every clip view audited (tested) |
| [S1-10](tasks/S1-10.md) | todo | Review screen as a WebView: stop timeline, ticket ticks, fast scrub, counted-boardings entry | — | Playwright review passes at 360 px |
| [S1-11](tasks/S1-11.md) | todo | Reconciliation v0: ticket-and-GPS trip ranking with a 1% control sample, ₹ leakage estimate, flag inbox, weekly one-page PDF | — | Flags fill from the replayed day |
| [S1-12](tasks/S1-12.md) | todo | Retention and deletion jobs; observability with a no-clips-today alert | — | Back-dated clips removed; alert fires |
| [S1-13](tasks/S1-13.md) | todo | Capture sanitized fixtures from pilot access; measure GB per bus-day; draft the DPDP data-flow note, processor-agreement template and per-operator proportionality note | H-02, H-04 | Fixtures committed; DPDP pack ready for H-05 |
| [S1-14](tasks/S1-14.md) | todo | Warner bridge: headless Chromium running the vendor H5 SDK; pre-connect, open sub stream, playback and MQTT gets; video-only Annex-B frames to Python over a local socket; commissioning script | H-02 | 10 min live sub stream from a pilot camera reaches the recorder |

**Gate G1 Access (2026-10-23):** Warner sub stream (streamid 0) measured at <=300 kbps with >=640x360 and >=5 fps; time to first frame <=3 s after pre-connect; vendor relay residency acceptable (H-14); Katch events within 30 s. If it fails: Sprint 2 adds the on-bus clip gateway (LAN/ONVIF) for the affected fleet. Result: pending.

## S2 — Phase 2 — nightly AI count (2026-10-26 → 2026-10-30)

Goal: Every pilot clip is counted overnight; managers see AI counts vs tickets with ranked flags

| ID | Status | Task | Needs input | Done when |
| --- | --- | --- | --- | --- |
| [S2-01](tasks/S2-01.md) | todo | Frame sampler by view, day/night and crowding, only from operators that permit training; door polygons per camera layout; crop to 416/512 px | H-20 | 5,000 frames exported with a manifest |
| [S2-02](tasks/S2-02.md) | todo | Auto-labelling: pre-label heads with a large detector; export a 10% QA sample | H-09 | Labels and QA sample ready by Wednesday |
| [S2-03](tasks/S2-03.md) | todo | Training pipeline from config; train v1 (YOLO11n, head and person) on a night GPU | H-03 | v1 weights registered |
| [S2-04](tasks/S2-04.md) | todo | Tracker (ByteTrack or OC-SORT) tuned for 5–6 fps; track IDs reset per clip | — | ID switches measured |
| [S2-05](tasks/S2-05.md) | todo | Counting package vvco_count: sill line, inner zone, 3 s return discard, height proxy near 120 cm | — | Synthetic track suite passes |
| [S2-06](tasks/S2-06.md) | todo | Ground-truth tool for H-07 and accuracy harness: per-stop error, trip totals, splits by view and crowding | H-07 | Baseline and v1 scored |
| [S2-07](tasks/S2-07.md) | todo | Model registry: weights, dataset hash, harness report per version | — | No promotion without a report |
| [S2-08](tasks/S2-08.md) | todo | Nightly batch: queue, idempotent per clip and model, ONNX/TensorRT, drift control, 06:00 alert | H-03 | Re-run writes identical rows |
| [S2-09](tasks/S2-09.md) | todo | Reconciliation v1, flag scoring, AI counts in the review screen | — | Morning report by 07:00 |
| [S2-10](tasks/S2-10.md) | todo | GPU cost report from measured timings: cloud L4 at night vs on-prem RTX | — | Recommendation for H-13 |

## S3 — Phase 3 — door counters (2026-11-02 → 2026-11-06)

Goal: FOORIR counts land in crossing_event and the same report; nightly retrain loop running

| ID | Status | Task | Needs input | Done when |
| --- | --- | --- | --- | --- |
| [S3-01](tasks/S3-01.md) | todo | Counter ingest: FOORIR heartBeat and dataUpload to crossing_event; HTTPS, allow-list, heartbeat alerts | H-10 | Simulator and fitted units land as rows |
| [S3-02](tasks/S3-02.md) | todo | Late uploads: 90-day device cache backfill re-runs reconciliation for past days | — | Simulated 3-day dropout reconciles |
| [S3-03](tasks/S3-03.md) | todo | Source priority (counter, then edge, then AI) and disagreement flags | — | Mixed-source stops unit-tested |
| [S3-04](tasks/S3-04.md) | todo | Milesight VS133 adapter behind the same contract, plus a vendor conformance kit for further sensors | — | Contract tests pass for both vendors |
| [S3-05](tasks/S3-05.md) | todo | Commissioning script: rotate default credentials, turn off Map Collection, set HTTPS push | — | Refuses to finish on default creds |
| [S3-06](tasks/S3-06.md) | todo | Three-way comparison: counter vs AI vs manual per stop | — | Table for any day with all three |
| [S3-07](tasks/S3-07.md) | todo | Retrain loop: error gallery, active-learning sample, auto-label, retrain, harness, register | — | v2 and v3 registered with reports |
| [S3-08](tasks/S3-08.md) | todo | Flag-threshold tuning from reviewer decisions | H-06 | Threshold curve for H-13 |
| [S3-09](tasks/S3-09.md) | todo | Pilot KPI dashboard: buses live, per-stop accuracy, flag precision, recovered ₹ vs subscription, review minutes, GB per bus-day, churn | H-18 | Every KPI computed from data for any pilot week |

## S4 — Phase 4 — edge vision (2026-11-09 → 2026-11-13)

Goal: Same model and rule run on an RK3588 or Pi 5 + Hailo-8L box; only crossing events leave the bus

| ID | Status | Task | Needs input | Done when |
| --- | --- | --- | --- | --- |
| [S4-01](tasks/S4-01.md) | todo | vvco_count as an aarch64 wheel shared by batch and edge | — | Installs on aarch64 in CI |
| [S4-02](tasks/S4-02.md) | todo | Export to RKNN and Hailo HEF, INT8 with a calibration set; score on the harness | — | Loss vs batch <= 2 points |
| [S4-03](tasks/S4-03.md) | todo | Edge runtime: 2 RTSP streams at 360p 8–10 fps, GPS/door gating, MQTT QoS 1, offline buffer | H-01 | 24 h bench run with a 2 h dropout loses nothing |
| [S4-04](tasks/S4-04.md) | todo | Provisioning, signed OTA, model version pinning, heartbeat | — | Rollback tested |
| [S4-05](tasks/S4-05.md) | todo | Clip upload only for flagged events | — | No upload without a server request |
| [S4-06](tasks/S4-06.md) | todo | Edge-vs-batch comparison and egress privacy check tools | — | Both run on bench captures |
| [S4-07](tasks/S4-07.md) | todo | G3 and G4 evidence packs: accuracy report; pricing model from measured costs and recovered fares | H-16, H-19 | Packs ready for H-13 |
| [S4-08](tasks/S4-08.md) | todo | Plans and usage metering: 60-day free Phase 1 trial, Phase 2 tiers and success-fee option, bus-month meter | — | Monthly usage statement per operator from data |
| [S4-09](tasks/S4-09.md) | todo | Tender-grade accuracy report (VDV 457-style protocol) and tender compliance pack | H-18, H-11 | Publishable report regenerates from the harness |

## Gates

| Gate | Date | Pass | Evidence | Result |
| --- | --- | --- | --- | --- |
| G1 Access | 2026-10-23 | Warner sub stream (streamid 0) measured at <=300 kbps with >=640x360 and >=5 fps; time to first frame <=3 s after pre-connect; vendor relay residency acceptable (H-14); Katch events within 30 s | S1-05 | pending |
| G2 First operator | 2026-11-06 | One operator reviews flagged trips weekly | S1-11 | pending |
| G3 Accuracy | 2026-11-27 (est.) | >=85% per-stop boardings on top-down views; >=80% of flags confirmed | S4-07 | pending |
| G4 Pricing | 2026-12-18 (est.) | Operator accepts >=Rs500/bus-month or success fee; recovered fares > 3x price | S4-07 | pending |
