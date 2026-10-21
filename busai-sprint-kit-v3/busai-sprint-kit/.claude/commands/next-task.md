---
description: Work one BusAI ticket (the next ready one, or the one named) per CLAUDE.md
argument-hint: "[ticket-id]"
---

Work one BusAI ticket. Requested: "$ARGUMENTS" (empty means the next ready ticket).

1. Run `python tools/next_task.py $ARGUMENTS`. If a named ticket is not READY, report what it waits on and stop. If no ID was given, take the first READY ticket in the earliest sprint.
2. Read `CLAUDE.md`, `tasks/<ID>.md`, and the parts of `docs/architecture-brief.md` the brief mentions.
3. Follow steps 3–4 of "How you run a sprint" in `CLAUDE.md`: branch from the sprint branch, tests first, code until `make lint test` is green, log assumptions in `DECISIONS.md`, merge into the sprint branch, set `review` (or `blocked` with a `BLOCKED.md` entry).
4. Finish with: what changed, how it was tested, any `DECISIONS.md` lines added, and the next READY ticket.
