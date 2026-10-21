# CLAUDE.md — BusAI / VV-Co passenger counting

You are building the VV-Co platform, mostly on your own in auto mode. VV-Co counts bus passengers at each door and reconciles the counts against tickets issued by the Katch POS, so operators can find fare leakage. **We count people; we never identify them.**

Read this file at the start of every session, then `backlog.yaml`, then the brief for your ticket (`tasks/<ID>.md`). Contracts and numbers are in `docs/architecture-brief.md`; the business requirements (who pays, for what, KPIs, DPDP roles, risks) are in `docs/business-brief.md`.

## The business in one paragraph

VV-Co (Vehicle Vision Company) is a joint venture of KParth Mobility (Katch: POS ticketing on 2,500+ buses, 100+ private operators), Upsquare (AI and engineering) and an investment pool, a third each. The charter funds a ₹15 lakh, 150-day prototype and a 10-bus pilot. We sell **recovered fares, not analytics**: Phase 1 is a free 60-day on-ramp, Phase 2 a subscription (₹750 / ₹600 / ₹500 per bus-month by fleet size, or 10–15% of verified recovered fares), Phases 3–4 hardware plus subscription for buyers who need certified (≥ 95%) or real-time counts. Phase 2 promises "finds leakage", not "counts to ±1"; only Phase 3 promises ≥ 95%. Katch sells to its operators; VV-Co delivers. Source docs (Basecamp, by Apurva Oza): [Part B — Key aspects](https://app.basecamp.com/4531610/buckets/49226321/documents/10399563327), [Phased Approach Review](https://app.basecamp.com/4531610/buckets/49226321/documents/10399537046), [Part A — Technical architecture](https://app.basecamp.com/4531610/buckets/49226321/documents/10399548939).

## The system in one paragraph

One pipeline serves four phases; only the bus-side source changes.

```
Katch box (tickets, GPS) ─► Katch events adapter ─► stop-window gate ─► clip recorder ─► batch inference ─┐
Cameras + vendor SDK ─────► camera adapter ─────────────────────────────┘                                  ├─► crossing_event ─► reconciliation ─► review app + web console + PDF
FOORIR door counters (P3) ─► counter ingest ───────────────────────────────────────────────────────────────┤
Edge box (P4) ─► MQTT ─────► counter ingest ───────────────────────────────────────────────────────────────┘
```

Four one-week sprints, one per phase: S1 clips and manual review, S2 nightly AI count, S3 door counters, S4 edge vision. `crossing_event` is the hinge: reconciliation and reporting never care which source wrote a row.

## How you run a sprint (auto mode)

People review once a week. Between reviews you keep going on your own.

1. `git checkout sprint/<S>` (create it from `main` if missing).
2. `python tools/next_task.py <S>` → take the first READY ticket. Set it `in_progress` in `backlog.yaml`.
3. Branch `t/<ID>-<slug>` from the sprint branch. Write the brief's acceptance tests first, then the code, until `make lint test` is green.
4. Merge the ticket branch into `sprint/<S>` (fast-forward or squash, message `<ID>: <title>`). Set the ticket to `review`. **Never merge into `main`.**
5. Repeat until no ticket in the sprint is READY. Then, if time remains, take READY tickets from the next sprint.
6. At the end, write `SPRINT_REPORT.md` for the sprint: what merged, what is blocked and on which input, test counts, anything the reviewer must read first.

**Inputs from people (`H-xx`) are not a reason to stop.** Build and test against `sim/` and `fixtures/`. If an acceptance item truly needs an open input, finish everything else, set the ticket `blocked`, and add an entry to `BLOCKED.md`: ticket, input, exactly what you need, what you built meanwhile.

**Do not stop to ask.** Take the most reasonable reading of the brief and log it in `DECISIONS.md` under the ticket ID (one line: decision, why, how to reverse). Friday's review can overturn it. Stop and ask only for something irreversible or outside these rules.

You may set `in_progress`, `review` and `blocked`. Only people set `done`, set `dropped`, change `inputs[].status`, or record gate results.

## Hard rules (never break these)

**Privacy**
- Count tables (`crossing_event`, `stop_reconciliation`, `flag`, reports) carry no personal data: no images, embeddings, face crops or identities.
- Detect heads and persons only. No face recognition, re-identification, gender, age, emotion or any attribute beyond the adult/child height proxy.
- Track IDs are local to one clip. Never link tracks across clips, stops, trips or days.
- Clips live only in the object store, in an Indian region, with a 30-day lifecycle. They are served only via signed URLs (≤ 5 min), and every access writes an `audit_log` row.
- Logs, metrics, fixtures and reports never contain clip frames, faces, ticket-holder data or phone numbers. Conductor IDs are hashed in fixtures and restricted to depot managers in the product.
- The accuracy harness scores only against human counts or counter data, never against auto-labels.
- No driver-facing analytics (drowsiness, distraction, DMS): that is OEM compliance under AIS-184 and employee data. Out of scope.

**Operators, people and decisions**
- Each operator is a separate DPDP data fiduciary; VV-Co is its processor. Every operator-owned row carries `operator_id`, every query runs under row-level security, and no code path reads across operators.
- The operator owns its raw video. VV-Co keeps anonymised counts and the models. Frames from an operator are used for training only when `operator.training_permitted` is true (H-20), and every dataset manifest records the operator and the agreement that permits it.
- AI counts and flags are evidence for a person. No code path penalises, suspends, scores or notifies against a conductor automatically; a flag becomes `confirmed` only with a human `reviewer_id`.
- Never print an accuracy figure (report, UI, PDF, README) without the harness report version and sample size behind it.

**Access**
- Pilot access (H-02) is read-only, for the three pilot buses only, and arrives as environment variables. Never write those values to a file, a log, a test, a commit or a PR. Never connect to any bus outside the pilot list.
- Staging only. You may deploy to staging and start night GPU jobs within the budget cap. You may not touch production, delete cloud resources, change IAM, or raise the budget.
- No real secret in the repo, ever. Devices are referenced by `credentials_ref` (vault path). Known-bad defaults (`admin/hf123456`, `admin/123456`, Warner `admin` with an empty password) must make code refuse to run.

**Cameras (Warner H5 SDK)** — read `docs/vendor/warner-h5sdk.md` before touching camera code.
- The SDK is browser-only and lives in `vendor/warner_h5sdk/` (git-ignored, checksum-pinned). Never commit it. Never read, copy or use the access token and app key embedded in `connector.js`, and never reuse the demo's password-derivation logic.
- Only `services/warner_bridge/` talks to the SDK, through its allow-list: connect, login, open/close stream, search/playback, capability set, and MQTT gets of the listed properties. No other setting is ever written at runtime; `User.List` is never requested.
- Drop audio frames inside the bridge. No audio track may exist in any clip, fixture or log.
- Camera settings change only through `tools/commission_warner.py --apply`, run by a person (H-15).

**Contracts and code**
- Files in `contracts/` are versioned. A change bumps the version and gets a `DECISIONS.md` line.
- Timestamps are UTC. Katch uses milliseconds; FOORIR uses microseconds. Normalise at ingest.
- Every ingest path is idempotent (natural key + upsert). Every pipeline step is deterministic for a given input and `model_version`.
- No new runtime dependency without a `DECISIONS.md` line.

## Repo map (S1-01 creates it)

```
contracts/          JSON Schemas + Python interfaces
db/migrations/      Alembic (Postgres 16)
services/
  ingest_katch/     Katch webhook/topic consumer        S1-06
  gate/             stop-window gate                    S1-07
  warner_bridge/    headless Chromium + vendor H5 SDK   S1-14
  camera_adapters/  base + warner.py (talks to bridge)  S1-08
  recorder/         FFmpeg clip recorder                S1-08
  api/              FastAPI, auth, audit, signed URLs   S1-09
  reconcile/        reconciliation, flags, ₹ leakage, KPIs   S1-11, S2-09, S3-03, S3-09
  metering/         plans, trial, bus-month meter       S4-08
  batch/            nightly GPU job queue               S2-08
  counter_ingest/   FOORIR HTTP + MQTT + vendors        S3-01, S3-04
packages/vvco_count/ tracker glue + counting rule, shared by batch and edge   S2-04, S2-05, S4-01
ml/                 sampling, autolabel, train, harness, registry, loop, export
edge/               edge runtime (RK3588 / Pi 5 + Hailo-8L)                  S4-03
web/                React console + review screen (WebView in Katch app)
sim/                Katch replayer, fake camera, FOORIR device simulator
fixtures/           sanitized real samples (S1-13 and H-04)
infra/              docker-compose, Terraform (staging), Grafana, Prometheus
tools/              render_briefs.py, next_task.py, spikes/, commissioning
tasks/              generated briefs, one per ticket
vendor/             third-party SDKs, git-ignored (make vendor fetches them)
BLOCKED.md  DECISIONS.md  SPRINT_REPORT.md
```

## Conventions

- Python 3.12, uv, FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic, pytest, ruff, mypy (strict on `services/` and `packages/`).
- Web: React + TypeScript; the review screen works inside an Android WebView at 360 px.
- Commands: `make dev`, `make test`, `make lint`, `make replay DAY=…`, `make deploy-staging`.
- After editing `backlog.yaml`, run `python tools/render_briefs.py` and commit the generated files.

## Glossary

- **Stop window**: speed 0 for > 5 s (or a ticket while stationary), padded 3 s; the only time we record.
- **Crossing event**: one person crossing the door line: direction, time, height proxy, confidence, source.
- **Gap**: tickets minus counted boardings at a stop. A **flag** is a trip whose gaps look like leakage; it always carries its clips.
- **Gate (G1–G4)**: a human stop/go decision; you prepare its evidence pack.
- **Control sample**: a seeded random 1% of trips reviewed regardless of score, so the ranking can be checked for blind spots.
- **Estimated leakage / recovered ₹**: unticketed boardings × median fare (computed), and the amount the operator says it actually recovered (entered). Always shown separately.
- **Bus-month**: a bus that produced clips or counts on any day of the month; the billing unit.
