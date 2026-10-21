# BusAI sprint kit (auto mode)

Human-facing plan: [BusAI Sprint Plan — Phases 1–4](https://claude.ai/code/artifact/c6a73b2f-8fd0-4423-b280-ea61f11c69a1) (the live doc predates v3; `docs/sprint-plan.md` is current).

Source docs (Basecamp, by Apurva Oza): [Part B — Key aspects](https://app.basecamp.com/4531610/buckets/49226321/documents/10399563327) · [Phased Approach Review](https://app.basecamp.com/4531610/buckets/49226321/documents/10399537046) · [Part A — Technical architecture](https://app.basecamp.com/4531610/buckets/49226321/documents/10399548939)

**v3 (13 Oct 2026):** aligned with Part B and the Phased Approach Review. Adds operator data isolation and training permission, a no-automatic-penalties rule, ticket-and-GPS trip ranking with a 1 % control sample, ₹ leakage and recovered fares, a pilot KPI dashboard (S3-09), plans and usage metering (S4-08), a tender-grade accuracy report (S4-09), and six new human inputs (H-16 to H-21).

Four one-week sprints, one per phase, built by Claude Code in auto mode. People supply 21 inputs (access, hardware, signatures, business decisions, ground truth, gate calls) and review the sprint branch each Friday. Drop these files into the root of the VV-Co repo.

| File | What it is |
| --- | --- |
| `CLAUDE.md` | Project and business context, the auto-mode sprint loop, hard privacy, operator and access rules, repo map |
| `docs/business-brief.md` | What each phase promises and costs, unit economics, pilot KPIs, DPDP roles, risks, open business questions |
| `docs/architecture-brief.md` | Contracts, data model, AI pipeline, costs and gates from the architecture doc |
| `docs/vendor/warner-h5sdk.md` | What the camera vendor's H5 SDK can and cannot do, the bridge's allow-list, privacy posture, questions for the vendor |
| `docs/sprint-plan.md` | Markdown copy of the human-facing plan doc |
| `backlog.yaml` | 42 Claude Code tickets in 4 sprints, 21 human inputs (`H-xx`), 4 gates |
| `SPRINTS.md` | Generated sprint tables, input list and gate table |
| `tasks/<ID>.md` | Generated brief per ticket: context, deliverables, acceptance tests, inputs used |
| `.claude/commands/run-sprint.md` | `/run-sprint S1` — runs a whole sprint ticket by ticket |
| `.claude/commands/next-task.md` | `/next-task [ID]` — runs one ticket |
| `.claude/settings.json` | Deny rules: secrets files, pushes to `main`, force pushes, `terraform destroy`, prod, IAM, budgets |
| `tools/next_task.py` | What's ready now; what a ticket waits on; which inputs are open |
| `tools/render_briefs.py` | Regenerates `tasks/` and `SPRINTS.md`; `--check` validates the backlog (run in CI) |

## The weekly rhythm

- **Monday:** open Claude Code in the repo, switch to auto mode, run `/run-sprint S1` (then S2, S3, S4 in the following weeks).
- **During the week:** Claude Code merges green tickets into `sprint/S1`, logs assumptions in `DECISIONS.md`, and lists anything waiting on people in `BLOCKED.md`. Check `BLOCKED.md` mid-week; it is your to-do list.
- **Friday:** read `SPRINT_REPORT.md`, `DECISIONS.md` and `BLOCKED.md`, review the `sprint/S1` diff, merge to `main`, set tickets to `done`, record any gate result in `backlog.yaml`.

## Before Monday 19 Oct

- H-01: order the counters and edge kits (lead time).
- H-02: read-only pilot access for 3 buses, passed to Claude Code as environment variables.
- H-03: cloud account in an Indian region with a budget cap and a staging-only role.
- H-04: one day of Katch events for 3 buses.
- H-16 and H-17 (by 21 Oct): the eSIM plan per bus, and where the cameras point on each bus type.
- H-18 and H-05 (by 23 Oct): pilot success metrics agreed with the operator; operator letter, processor agreement and audit-policy announcement.
- Put `WARNER_H5SDK_V1.zip` in the private bucket (and locally in `vendor/warner_h5sdk/` — never in git), and send the vendor the questions in `docs/vendor/warner-h5sdk.md` (H-14).
- Keep the three VV-Co source docs linked above to hand; they replace the architecture PDF.

Requires Python 3.10+ and PyYAML for the tools (`pip install pyyaml`).
