# BusAI Sprint Plan — Phases 1–4

> Copy of the live doc: [BusAI Sprint Plan — Phases 1–4](https://claude.ai/code/artifact/c6a73b2f-8fd0-4423-b280-ea61f11c69a1). Edit the live doc; this copy may be out of date.

Oct 19, 2026 · @Harshal Oza

## Summary

Claude Code builds all four phases in four one-week sprints, one sprint per phase, from 19 Oct to 13 Nov 2026. It owns all 39 build tickets. People own 15 inputs and decisions that no agent can supply: access, hardware, signatures, ground-truth counts and the gate calls.

The code compresses; the gates do not, because they wait on buses, depot managers and people counting stops. G1 Access lands with Sprint 1 on 23 Oct. G2 needs two weekly review cycles, so 6 Nov at the earliest. G3 Accuracy waits on ≥ 100 stops of human ground truth and is estimated for late November. G4 Pricing follows G3 with a few weeks of recovered-fare data, estimated mid-December. That is still about week 9 instead of week 22.

Every phase reuses one pipeline: Katch events, stop-window gate, clip store, one `crossing_event` table and reconciliation. So Sprints 2–4 each add a source or a model to code that already runs, which is what makes one week per phase realistic for an agent.

Sprint 1 starts today, Monday 19 Oct, with `/run-sprint S1`. Assumptions to confirm: Claude Code gets read-only access to three pilot buses today (H-02); one person reviews and merges the sprint branch each Friday.

*Roadmap chart (build vs gates): see the [live doc](https://claude.ai/code/artifact/c6a73b2f-8fd0-4423-b280-ea61f11c69a1).*

Claude Code's four sprints end on 13 Nov; the people track runs on to G3 because ground truth is counted by hand.

A one-page summary of this plan is in [BusAI Sprints — One-Pager](https://claude.ai/code/artifact/8a6c610e-3b1e-4be6-939f-12ba116640a9).

## How Claude Code runs a sprint in auto mode

Claude Code works each sprint as one long run against `backlog.yaml`, and a person reviews once, on Friday. The repo kit carries the rules, the tickets and a `/run-sprint` command.

1. Monday: start Claude Code in the repo and run `/run-sprint S1`.
2. Claude Code takes the next ready ticket, branches from `sprint/S1`, writes the brief's acceptance tests first, then the code, until `make lint test` is green.
3. When CI is green it merges the ticket into `sprint/S1`, sets the ticket to `review` and moves on. It never merges to `main`.
4. If a ticket waits on a person, it marks it `blocked`, writes what it needs in `BLOCKED.md`, and carries on with the next ready ticket instead of stopping.
5. Every assumption goes into `DECISIONS.md` under its ticket ID, so Friday's review can overturn it.
6. Friday: review `sprint/S1` as one diff together with `DECISIONS.md` and `BLOCKED.md`, merge to `main`, and set the tickets to `done`.

Guardrails, enforced by `CLAUDE.md` and deny rules in `.claude/settings.json`:

- Count tables carry no personal data. Head detection only; track IDs never link across clips.
- Clips stay in an Indian region, expire after 30 days, open only via signed URLs, and every view is audited.
- Pilot access is read-only, limited to three pilot buses, passed as environment variables and never written to files or logs.
- Claude Code deploys to staging and rents night GPUs within the budget cap. Production, and deleting cloud resources, are out of reach.
- Tests decide "done". The accuracy harness scores only against human or counter ground truth, never against auto-labels.

## Inputs only people can give

Fifteen items stay human because they need a bus, a purchase, a signature, a person counting, or a business call. Late inputs do not stop a sprint; Claude Code builds against simulators and marks the dependent ticket blocked.

| ID | Input | Needed by | Unblocks |
| --- | --- | --- | --- |
| H-01 | Order 2–4 FOORIR HX-CCD22 counters and 2 edge kits (Pi 5 + AI Kit or RK3588, DC-DC converter, enclosure) | Oct 16, 2026 | Sprints 3 and 4 on real hardware |
| H-02 | Pilot access for Claude Code: Warner cloud account, device IDs and passwords for the 6 cameras on 3 pilot buses, the Katch sandbox or topic (Parth), and the Warner SDK in the private bucket | Oct 19, 2026 | S1-05, S1-08, S1-13, S1-14 |
| H-03 | Cloud account in an Indian region with a budget cap, a staging-only deploy role and night GPU quota | Oct 19, 2026 | S1-01, S2-03, S2-08 |
| H-04 | One day of Katch events for 3 buses, exported by Parth | Oct 19, 2026 | S1-04, S1-06 |
| H-14 | Warner answers: where the relay and cloud are hosted, whether the sub stream can be set, a server-side SDK or RTSP path, rotating the token embedded in the SDK, LAN password derivation, a limited-scope account | Oct 21, 2026 | G1 |
| H-15 | Run the commissioning script on the 6 pilot cameras: unique passwords; alarm push, on-camera boxes and audio off; continuous sub-stream SD recording on | Oct 22, 2026 | S1-08 on pilot buses |
| H-05 | Pilot operator letter, DPDP notice stickers on 10 buses, sign-off on the data-flow note Claude Code drafts | Oct 23, 2026 | Recording on pilot buses |
| H-06 | Two depot managers review flagged trips weekly | Oct 26, 2026 | G2 |
| H-07 | Ground truth: ≥ 100 stops counted by people in the tool, each counted twice | Oct 26, 2026 | G3 (the long pole) |
| H-08 | Parth embeds the review WebView and SSO in the Katch Android app | Oct 28, 2026 | H-06 |
| H-09 | Check about 10% of the auto-labels, roughly 400 frames | Oct 28, 2026 | S2-03 model v1 |
| H-10 | Fit the FOORIR units with door contact on DI; run the commissioning script | Nov 4, 2026 | S3-01 on real data |
| H-11 | BIS CRS / ER-01 advice on the depth-only counter SKU | Nov 6, 2026 | Phase 3 at scale |
| H-12 | Fit edge boxes on two pilot buses | After G3 | Phase 4 in the field |
| H-13 | Review and merge the sprint branch; make the G1–G4 calls and the GPU choice from Claude Code's evidence packs | Every Friday | Next sprint |

## Sprint 1 — Phase 1: clips and manual review (19–23 Oct)

Goal: pilot buses record a clip at every stop, a manager can review a trip against ticket ticks, and the G1 evidence pack is ready on Friday. This sprint also lays the foundations the other three reuse, so it is the heaviest.

The vendor's H5 SDK (received 12 Oct) reshapes the camera work. It runs only in a browser, so Claude Code first builds a headless-Chromium bridge (S1-14). It reaches cameras through the vendor's P2P relay on `dvr163.com` rather than RTSP, and it cannot set sub-stream resolution or fps, so G1 now measures them instead. Audio arrives with the video and is dropped in the bridge. Camera settings change only through a commissioning script a person runs (H-15). Claude Code's notes are in `docs/vendor/warner-h5sdk.md`.

| ID | Task | Done when |
| --- | --- | --- |
| S1-01 | Scaffold: Python 3.12 monorepo, docker-compose, CI, secret scanning, Terraform for staging in an Indian region; Node 20 and headless Chromium; vendor SDK kept out of git | `make dev` green; staging deploys |
| S1-02 | Schema v0: the 10 entities plus `audit_log`, event tables partitioned by day, idempotent natural keys | Migrations apply up and down |
| S1-03 | Contracts as code: Katch events, a `CameraAdapter` shaped by the Warner SDK (pre-connect; frames report their real size and codec), counter contract, MQTT topic | Every fixture validates |
| S1-04 | Simulators: Katch replayer, fake Warner camera with its error codes and handshake delay, FOORIR device with dropout and backfill | A fixture day replays at 60× |
| S1-14 | Warner bridge, built first: headless Chromium runs the vendor SDK; pre-connect, sub stream, playback and read-only MQTT through an allow-list; audio dropped; video frames to Python; commissioning script for H-15 | 10 min live sub stream reaches the recorder |
| S1-05 | G1 spikes through the bridge: real sub-stream size, fps and bitrate; time to first frame; relay path; SD playback speed; clock drift; privacy posture; Katch latency | G1 evidence pack on Friday |
| S1-06 | Katch events adapter: webhook with signature check or topic consumer, idempotent upserts | Replayed day, zero duplicates |
| S1-07 | Stop-window gate: pre-connect when the bus slows below 10 km/h; window at speed 0 for > 5 s or POS events; 3 s padding; `stop_event` with dwell | ≥ 95% of Katch stops matched |
| S1-08 | Warner adapter over the bridge; recorder remuxes frames to MP4 without decoding, starts each clip on an I-frame, adds an H.264 proxy for H.265; overnight SD fill | One clip per window on pilot buses, no audio track |
| S1-09 | API and auth: roles, signed clip URLs, audit row per clip view | Every clip view audited (tested) |
| S1-10 | Review screen as a WebView: stop timeline, ticket ticks, fast scrub, counted-boardings entry | Playwright review passes at 360 px |
| S1-11 | Reconciliation v0: rule-based ranking, flag inbox, weekly one-page PDF | Flags fill from the replayed day |
| S1-12 | Retention and deletion jobs; observability with Warner error codes, a no-clips-today alert and a daily camera privacy-posture check | Alerts fire in tests |
| S1-13 | Capture sanitized fixtures (clips and Warner frame dumps); measure GB per bus-day; draft the DPDP data-flow note, including the vendor relay and cloud | Fixtures committed; note ready for H-05 |

Gate G1 (Fri 23 Oct): the sub stream measures ≤ 300 kbps at ≥ 640×360 and ≥ 5 fps; the first frame arrives ≤ 3 s after a pre-connected open; the vendor confirms an acceptable relay location (H-14); and Katch events arrive within 30 s. If the camera side fails, Sprint 2 adds an on-bus gateway that reads the cameras over the bus LAN instead of the relay.

## Sprint 2 — Phase 2: nightly AI count (26–30 Oct)

Goal: every pilot clip is counted overnight, and managers see AI counts against tickets with ranked flags. Labelling moves from people to auto-labels plus a 10% human check (H-09).

| ID | Task | Done when |
| --- | --- | --- |
| S2-01 | Frame sampler by view, day or night and crowding; door polygons per camera layout; crop to 416 or 512 px | 5,000 frames exported with a manifest |
| S2-02 | Auto-labelling: pre-label heads with a large detector; export a 10% sample for H-09 | Labels and QA sample ready by Wed |
| S2-03 | Training pipeline from config; train v1 (YOLO11n, head and person) on a night GPU | v1 weights registered |
| S2-04 | Tracker (ByteTrack or OC-SORT) tuned for 5–6 fps; track IDs reset per clip | ID switches measured |
| S2-05 | Counting package `vvco_count`: sill line, inner zone, 3 s return discard, height proxy near 120 cm | Synthetic track suite passes |
| S2-06 | Ground-truth tool for H-07 and accuracy harness: per-stop error, trip totals, splits by view and crowding | Baseline and v1 scored |
| S2-07 | Model registry: weights, dataset hash, harness report per version | No promotion without a report |
| S2-08 | Nightly batch: queue, idempotent per clip and model, ONNX or TensorRT, drift control, 06:00 alert | Re-run writes identical rows |
| S2-09 | Reconciliation v1, flag scoring, AI counts in the review screen | Morning report by 07:00 |
| S2-10 | GPU cost report from measured timings: cloud L4 at night vs an on-prem RTX | Recommendation for H-13 |

Exit: the batch runs every night on all pilot clips. The v1 accuracy number is provisional until H-07 reaches 100 stops.

## Sprint 3 — Phase 3: door counters (2–6 Nov)

Goal: FOORIR counts land in the same `crossing_event` table and morning report as AI counts, and the model improves every night through an automated retrain loop.

| ID | Task | Done when |
| --- | --- | --- |
| S3-01 | Counter ingest: FOORIR heartbeat and `dataUpload` to `crossing_event`; HTTPS, device allow-list, heartbeat alerts | Simulator and fitted units land as rows |
| S3-02 | Late uploads: 90-day device cache backfill re-runs reconciliation for past days | Simulated 3-day dropout reconciles |
| S3-03 | Source priority (counter, then edge, then AI) and disagreement flags | Mixed-source stops unit-tested |
| S3-04 | Milesight VS133 adapter behind the same contract | Contract tests pass for both vendors |
| S3-05 | Commissioning script: rotate default credentials, turn off Map Collection, set HTTPS push | Refuses to finish on default creds |
| S3-06 | Three-way comparison: counter vs AI vs manual per stop | Table for any day with all three |
| S3-07 | Retrain loop: error gallery, active-learning sample, auto-label, retrain, harness, register | v2 and v3 registered with reports |
| S3-08 | Flag-threshold tuning from reviewer decisions | Threshold curve for H-13 |

Exit: counters report on real buses if H-10 is done; otherwise on the simulator and bench, with the ticket marked blocked on H-10.

## Sprint 4 — Phase 4: edge vision (9–13 Nov)

Goal: the same model and counting rule run on an RK3588 or Pi 5 + Hailo-8L box, sending only crossing events off the bus. The build is ready before G3; fitting boxes on buses waits for G3 (H-12).

| ID | Task | Done when |
| --- | --- | --- |
| S4-01 | `vvco_count` as an aarch64 wheel shared by batch and edge | Installs on aarch64 in CI |
| S4-02 | Export to RKNN and Hailo HEF, INT8 with a calibration set; score on the harness | Loss vs batch ≤ 2 points |
| S4-03 | Edge runtime: 2 RTSP streams at 360p and 8–10 fps, GPS or door gating, MQTT QoS 1, offline buffer | 24 h bench run with a 2 h dropout loses nothing |
| S4-04 | Provisioning, signed OTA, model version pinning, heartbeat | Rollback tested |
| S4-05 | Clip upload only for flagged events | No upload without a server request |
| S4-06 | Edge-vs-batch comparison and egress privacy check tools | Both run on bench captures |
| S4-07 | G3 and G4 evidence packs: accuracy report, pricing model from measured costs and recovered fares | Packs ready for H-13 |

Exit: the edge runtime passes the bench on a kit (or in emulation if H-01 hardware is late). Diwali falls on 8 Nov, so expect slower human reviews this week; Claude Code's work is unaffected.

## Gates, risks and open decisions

The gates keep the pass conditions from the architecture doc; only their dates move. G3 and G4 are estimates that depend on how fast people supply ground truth and recovered-fare data.

| Gate | Date | Pass condition | Waits on |
| --- | --- | --- | --- |
| G1 Access | Oct 23, 2026 | Sub stream ≤ 300 kbps at ≥ 640×360 and ≥ 5 fps; first frame ≤ 3 s; relay location acceptable; Katch events within 30 s | S1-05 through the bridge; H-14 |
| G2 First operator | Nov 6, 2026 | One operator reviews flagged trips weekly | H-08, then two weekly cycles of H-06 |
| G3 Accuracy | Nov 27, 2026 (est.) | ≥ 85% per-stop boardings on top-down views; ≥ 80% of flags confirmed | H-07 reaching 100 stops; retrain loop |
| G4 Pricing | Dec 18, 2026 (est.) | Operator accepts ≥ ₹500 per bus-month or a success fee; recovered fares > 3× price | G3, then weeks of measured recoveries |

Risks:

- Pilot access (H-02) late: S1-05, S1-08, S1-13 and S1-14 slip and G1 moves; everything else runs on simulators.
- Review load: about 10 tickets a week land in one Friday diff. Tests are the first gate; read `DECISIONS.md` before the code.
- Auto-labels inherit the big detector's blind spots. The 10% check (H-09) and a harness scored only on human or counter ground truth guard against this.
- Hardware lead time: counters and edge kits must be ordered this week (H-01).

Open decisions:

- [ ] Clips vs the "no personal data" promise: Phase 1–2 clips show people and are personal data under DPDP. Keep clip review with notice, audit log and 30-day expiry, add face blur in the player, or both?
- [ ] Vendor relay: video now passes through Warner's P2P relay. If H-14 shows it is hosted outside India, accept it for the pilot, require an India-hosted relay, or move to an on-bus gateway that reads cameras over the bus LAN?
- [ ] Clock sync: may the bridge write `System.Time.TimeUtc` to the cameras, its only permitted setting change?
- [ ] Pilot-access scope for Claude Code: read-only, three buses, revocable. Agree?
- [ ] Merge policy: Claude Code merges green tickets into the sprint branch (assumed here), or a PR per ticket?
- [ ] Conductor-level ranking is employee data: who at the operator may see it?
