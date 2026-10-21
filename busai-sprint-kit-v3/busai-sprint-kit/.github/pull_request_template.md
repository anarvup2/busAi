## Sprint

<!-- e.g. sprint/S1 → main. Link SPRINT_REPORT.md -->

## Read first

- [ ] `SPRINT_REPORT.md` — what merged, what is blocked, what to look at first
- [ ] `DECISIONS.md` — every assumption Claude Code made this sprint
- [ ] `BLOCKED.md` — inputs people still owe

## Privacy and safety checklist (reviewer)

- [ ] No real credentials, keys or tokens anywhere in the diff
- [ ] Nothing reaches production or buses outside the pilot list
- [ ] Count tables, logs, metrics and fixtures carry no personal data
- [ ] Track IDs stay local to one clip; nothing links people across clips
- [ ] Clip access goes through signed URLs and writes `audit_log`; lifecycle still 30 days, Indian region
- [ ] Harness scores only against human or counter ground truth
- [ ] Every operator-owned table and query is operator-scoped; no cross-operator read
- [ ] No code path acts against a conductor automatically; flags confirmed only with a reviewer_id
- [ ] Training data only from operators with training permission; manifests record the agreement
- [ ] Accuracy figures in reports cite a harness report version and sample size
- [ ] `contracts/` changes have a version bump and a `DECISIONS.md` line

## After merge

- [ ] Tickets in `review` set to `done` in `backlog.yaml`
- [ ] Gate result recorded, if this sprint carries one
- [ ] `python tools/render_briefs.py --check` passes
