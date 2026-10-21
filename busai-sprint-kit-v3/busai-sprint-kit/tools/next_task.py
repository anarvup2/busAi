#!/usr/bin/env python3
"""Show which tickets Claude Code can start now.

Ready = status todo, and every ticket in depends_on is review or done.
Human inputs (needs_input) never block a start; they are listed so the agent
knows which acceptance items may end up blocked.

Usage:  python tools/next_task.py            # ready tickets, earliest sprint first
        python tools/next_task.py S2         # ready tickets in one sprint
        python tools/next_task.py S2-03      # one ticket: ready or what blocks it
        python tools/next_task.py --all      # every ticket with its state
        python tools/next_task.py --inputs   # human inputs still open
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SATISFIED = {"review", "done"}


def main() -> int:
    data = yaml.safe_load((ROOT / "backlog.yaml").read_text(encoding="utf-8"))
    tickets = data["tickets"]
    by_id = {t["id"]: t for t in tickets}
    inputs = {i["id"]: i for i in data.get("inputs", [])}
    sprint_ids = [s["id"] for s in data["sprints"]]
    order = {s: n for n, s in enumerate(sprint_ids)}
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    def blockers(t: dict) -> list[str]:
        return [d for d in (t.get("depends_on") or []) if by_id[d]["status"] not in SATISFIED]

    def open_inputs(t: dict) -> list[str]:
        return [h for h in (t.get("needs_input") or []) if inputs[h]["status"] != "done"]

    if "--inputs" in sys.argv:
        for i in inputs.values():
            if i["status"] != "done":
                users = [t["id"] for t in tickets if i["id"] in (t.get("needs_input") or [])]
                print(f"{i['id']} (by {i['needed_by']}): {i['title']}  -> used by {', '.join(users) or '—'}")
        return 0

    if args and args[0] in by_id:
        t = by_id[args[0]]
        b = blockers(t)
        state = "READY" if t["status"] == "todo" and not b else t["status"].upper()
        print(f"{t['id']} {state}: {t['title']}")
        for d in b:
            print(f"  waits for {d} ({by_id[d]['status']}): {by_id[d]['title']}")
        for h in open_inputs(t):
            print(f"  uses open input {h}: {inputs[h]['title']}")
        return 0

    scope = [t for t in tickets if not args or t["sprint"] == args[0]]
    if args and args[0] not in sprint_ids:
        print(f"unknown ticket or sprint {args[0]}")
        return 1
    scope.sort(key=lambda t: order[t["sprint"]])

    if "--all" in sys.argv:
        for t in scope:
            b = blockers(t)
            tag = "READY" if t["status"] == "todo" and not b else t["status"]
            extra = f"  waits: {', '.join(b)}" if b and t["status"] == "todo" else ""
            print(f"{t['sprint']} {t['id']:<6} {tag:<11} {t['title'][:72]}{extra}")
        return 0

    ready = [t for t in scope if t["status"] == "todo" and not blockers(t)]
    if not ready:
        waiting = sorted({d for t in scope if t["status"] == "todo" for d in blockers(t)})
        print("No ticket is ready." + (" Waiting on: " + ", ".join(waiting) if waiting else " Sprint complete or all blocked."))
        return 0
    for t in ready:
        oi = open_inputs(t)
        print(f"{t['sprint']} {t['id']:<6} {t['title']}" + (f"  [open inputs: {', '.join(oi)}]" if oi else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
