---
description: Run a whole BusAI sprint in auto mode, ticket by ticket, on the sprint branch
argument-hint: "<sprint-id, e.g. S1>"
---

Run sprint "$ARGUMENTS" of the BusAI backlog to completion, following `CLAUDE.md` exactly.

1. Read `CLAUDE.md`, `backlog.yaml` and `docs/architecture-brief.md`. Check out `sprint/$ARGUMENTS` (create it from `main` if missing).
2. Run `python tools/next_task.py --inputs` and note which human inputs are still open. Do not wait for them.
3. Loop:
   a. `python tools/next_task.py $ARGUMENTS` → take the first READY ticket; if none, go to step 4.
   b. Set it `in_progress`; branch `t/<ID>-<slug>` from `sprint/$ARGUMENTS`; read `tasks/<ID>.md`.
   c. Write the acceptance tests first, then the code, until `make lint test` is green. Use `sim/` and `fixtures/` for anything an open input would supply.
   d. Log assumptions in `DECISIONS.md` under the ticket ID.
   e. Merge into `sprint/$ARGUMENTS`; set the ticket to `review`, or to `blocked` with a `BLOCKED.md` entry if an acceptance item needs an open input.
   f. Run `python tools/render_briefs.py --check`, commit, continue the loop.
4. When nothing in the sprint is READY: if tickets in the next sprint are READY, start them the same way on the next sprint's branch.
5. Write `SPRINT_REPORT.md`: merged tickets, blocked tickets with the input each needs, test counts, the three things the reviewer should read first, and evidence packs produced (for example `docs/spikes/G1.md`).

Never merge into `main`, mark anything `done`, touch production, write pilot credentials anywhere, or stop to ask about something `DECISIONS.md` can record.
