# BusAI Sprints — One-Pager

Oct 19, 2026 · @Harshal Oza

Claude Code builds the BusAI passenger counter in four one-week sprints, one per phase, from today to 13 Nov 2026. The system counts people at bus doors and checks the counts against tickets, without collecting personal data. People supply access, hardware, sign-offs and hand counts, and review the week's work every Friday.

## Sprints

| Sprint | Dates | Phase | What Claude Code builds | Ends with |
| --- | --- | --- | --- | --- |
| S1 | 19–23 Oct | 1 · Clips and manual review | Warner camera bridge, stop detection, clip store, review screen for managers | G1 Access decision, Fri 23 Oct |
| S2 | 26–30 Oct | 2 · Nightly AI count | Auto-labelling, head detector, counting rule, overnight batch, AI-ranked flags | Morning report ready by 07:00 |
| S3 | 2–6 Nov | 3 · Door counters | FOORIR counter ingest, source priority, nightly retrain loop | G2 First operator, Fri 6 Nov |
| S4 | 9–13 Nov | 4 · Edge vision | Edge-box runtime, model export, over-the-air updates | G3 and G4 evidence packs |

Two gates wait on field data after the build: G3 Accuracy (est. 27 Nov) needs 100 stops counted by hand, and G4 Pricing (est. 18 Dec) needs a few weeks of recovered fares.

## Needed from people this week

| Due | Input |
| --- | --- |
| Today (19 Oct) | Pilot access for 3 buses and the Warner account (H-02); Indian-region cloud account (H-03); one day of Katch events (H-04); counters and edge kits ordered (H-01, due 16 Oct) |
| Wed 21 Oct | Warner's answers on relay hosting and the SDK (H-14) |
| Thu 22 Oct | Commission the 6 pilot cameras (H-15) |
| Fri 23 Oct | Pilot letter and DPDP notices (H-05); sprint review and the G1 call (H-13) |

Full detail: [BusAI Sprint Plan — Phases 1–4](https://claude.ai/code/artifact/c6a73b2f-8fd0-4423-b280-ea61f11c69a1).
