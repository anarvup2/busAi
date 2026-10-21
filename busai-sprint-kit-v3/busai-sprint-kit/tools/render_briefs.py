#!/usr/bin/env python3
"""Render tasks/<ID>.md briefs and SPRINTS.md from backlog.yaml.

Usage:  python tools/render_briefs.py [--check]
  --check  exit 1 if backlog.yaml has errors (unknown deps or inputs, cycles,
           tickets without briefs) or if rendered files differ from disk.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "backlog.yaml"
TASKS = ROOT / "tasks"
SPRINTS_MD = ROOT / "SPRINTS.md"

VALID_STATUS = {"todo", "in_progress", "review", "blocked", "done", "dropped"}
VALID_OWNER = {"claude_code", "human"}


def load() -> dict:
    return yaml.safe_load(BACKLOG.read_text(encoding="utf-8"))


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    tickets = data["tickets"]
    ids = [t["id"] for t in tickets]
    input_ids = {i["id"] for i in data.get("inputs", [])}
    sprint_ids = {s["id"] for s in data["sprints"]}
    if len(ids) != len(set(ids)):
        errors.append("duplicate ticket ids")
    known = set(ids)
    sprint_pos = {s["id"]: n for n, s in enumerate(data["sprints"])}
    by_id = {t["id"]: t for t in tickets}
    for t in tickets:
        if t.get("owner", "claude_code") not in VALID_OWNER:
            errors.append(f"{t['id']}: bad owner {t.get('owner')}")
        if t["status"] not in VALID_STATUS:
            errors.append(f"{t['id']}: bad status {t['status']}")
        if t["sprint"] not in sprint_ids:
            errors.append(f"{t['id']}: unknown sprint {t['sprint']}")
        for d in t.get("depends_on") or []:
            if d not in known:
                errors.append(f"{t['id']}: unknown dependency {d}")
            elif sprint_pos[by_id[d]["sprint"]] > sprint_pos[t["sprint"]]:
                errors.append(f"{t['id']}: depends on {d}, which is in a later sprint")
        for h in t.get("needs_input") or []:
            if h not in input_ids:
                errors.append(f"{t['id']}: unknown input {h}")
        if t.get("owner", "claude_code") == "claude_code" and "brief" not in t:
            errors.append(f"{t['id']}: Claude Code ticket without a brief")
    graph = {t["id"]: list(t.get("depends_on") or []) for t in tickets}
    state: dict[str, int] = {}

    def visit(n: str, path: list[str]) -> None:
        if state.get(n) == 1:
            errors.append("dependency cycle: " + " -> ".join(path + [n]))
            return
        if state.get(n) == 2:
            return
        state[n] = 1
        for m in graph.get(n, []):
            visit(m, path + [n])
        state[n] = 2

    for n in graph:
        visit(n, [])
    return errors


def bullets(items) -> str:
    items = items or []
    return "\n".join(f"- {i}" for i in items) if items else "- (none)"


def render_brief(t: dict, sprint: dict, by_id: dict, inputs: dict) -> str:
    b = t["brief"]
    deps = t.get("depends_on") or []
    needs = t.get("needs_input") or []
    dep_lines = "\n".join(f"- {d} — {by_id[d]['title']}" for d in deps) if deps else "- (none)"
    need_lines = (
        "\n".join(f"- {h} — {inputs[h]['title']} (needed by {inputs[h]['needed_by']})" for h in needs)
        if needs
        else "- (none)"
    )
    parts = [
        f"# {t['id']} — {t['title']}",
        "",
        f"**Sprint:** {sprint['id']} {sprint['name']} ({sprint['start']} → {sprint['end']})  ",
        f"**Done when:** {t['done_when']}",
        "",
        "> Generated from `backlog.yaml` by `tools/render_briefs.py`. Edit the YAML, not this file.",
        "",
        "## Context",
        "",
        b["context"],
        "",
        "## Depends on (satisfied at `review` or `done`)",
        "",
        dep_lines,
        "",
        "## Human inputs this ticket uses",
        "",
        need_lines,
        "",
        "Not a reason to wait. Build and test against `sim/` and `fixtures/`. If an acceptance item can only pass with the input, finish everything else, set `status: blocked`, and add an entry to `BLOCKED.md`.",
        "",
        "## Deliver",
        "",
        bullets(b.get("deliver")),
        "",
        "## Acceptance tests (write these first)",
        "",
        "\n".join(f"- [ ] {a}" for a in b.get("acceptance", [])),
        "",
        "## Out of scope",
        "",
        bullets(b.get("out_of_scope")),
        "",
        "## Before merging into the sprint branch",
        "",
        "- [ ] `CLAUDE.md` hard rules respected (privacy, credentials, staging only)",
        "- [ ] Contracts unchanged, or version bumped with a reason in `DECISIONS.md`",
        "- [ ] Assumptions logged in `DECISIONS.md` under this ticket ID",
        "- [ ] `make lint test` green",
        f"- [ ] `backlog.yaml`: {t['id']} set to `review` (or `blocked` + `BLOCKED.md` entry)",
        "",
    ]
    return "\n".join(parts)


def render_sprints(data: dict) -> str:
    by_sprint: dict[str, list[dict]] = {}
    for t in data["tickets"]:
        by_sprint.setdefault(t["sprint"], []).append(t)
    gates = {g["id"]: g for g in data["gates"]}
    out = [
        "# Sprints",
        "",
        f"> Generated from `backlog.yaml`. Human-facing plan: {data.get('plan_doc', 'the BusAI Sprint Plan doc')}",
        "",
        "## Human inputs",
        "",
        "| ID | Needed by | Status | Input |",
        "| --- | --- | --- | --- |",
    ]
    for i in data.get("inputs", []):
        out.append(f"| {i['id']} | {i['needed_by']} | {i['status']} | {i['title']} |")
    out.append("")
    for s in data["sprints"]:
        out += [f"## {s['id']} — {s['name']} ({s['start']} → {s['end']})", "", f"Goal: {s['goal']}", ""]
        out += ["| ID | Status | Task | Needs input | Done when |", "| --- | --- | --- | --- | --- |"]
        for t in by_sprint.get(s["id"], []):
            link = f"[{t['id']}](tasks/{t['id']}.md)" if "brief" in t else t["id"]
            needs = ", ".join(t.get("needs_input") or []) or "—"
            out.append(f"| {link} | {t['status']} | {t['title']} | {needs} | {t['done_when']} |")
        if s.get("gate"):
            g = gates[s["gate"]]
            out += ["", f"**Gate {g['id']} {g['name']} ({g['date']}):** {g['pass']}. If it fails: {g['on_fail']}. Result: {g['result'] or 'pending'}."]
        out.append("")
    out += ["## Gates", "", "| Gate | Date | Pass | Evidence | Result |", "| --- | --- | --- | --- | --- |"]
    for g in data["gates"]:
        date = f"{g['date']}{' (est.)' if g.get('estimate') else ''}"
        out.append(f"| {g['id']} {g['name']} | {date} | {g['pass']} | {g.get('evidence', '—')} | {g['result'] or 'pending'} |")
    out.append("")
    return "\n".join(out)


def main() -> int:
    check = "--check" in sys.argv
    data = load()
    errors = validate(data)
    if errors:
        print("backlog.yaml errors:\n  " + "\n  ".join(errors))
        return 1
    sprints = {s["id"]: s for s in data["sprints"]}
    by_id = {t["id"]: t for t in data["tickets"]}
    inputs = {i["id"]: i for i in data.get("inputs", [])}
    wanted: dict[Path, str] = {}
    for t in data["tickets"]:
        if "brief" in t:
            wanted[TASKS / f"{t['id']}.md"] = render_brief(t, sprints[t["sprint"]], by_id, inputs)
    wanted[SPRINTS_MD] = render_sprints(data)

    if check:
        stale = [p for p, txt in wanted.items() if not p.exists() or p.read_text(encoding="utf-8") != txt]
        extra = [p for p in TASKS.glob("*.md") if p not in wanted] if TASKS.exists() else []
        if stale or extra:
            if stale:
                print("stale or missing: " + ", ".join(str(p.relative_to(ROOT)) for p in stale))
            if extra:
                print("orphan briefs: " + ", ".join(str(p.relative_to(ROOT)) for p in extra))
            return 1
        print("backlog and briefs are in sync")
        return 0

    TASKS.mkdir(exist_ok=True)
    for p in TASKS.glob("*.md"):
        if p not in wanted:
            p.unlink()
    for p, txt in wanted.items():
        p.write_text(txt, encoding="utf-8")
    per_sprint: dict[str, int] = {}
    for t in data["tickets"]:
        per_sprint[t["sprint"]] = per_sprint.get(t["sprint"], 0) + 1
    print(f"rendered {len(wanted) - 1} briefs + SPRINTS.md; tickets per sprint: {per_sprint}; inputs: {len(inputs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
