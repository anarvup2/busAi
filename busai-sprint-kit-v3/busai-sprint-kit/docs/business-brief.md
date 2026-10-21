# Business brief for builders

Condensed from Apurva Oza's VV-Co working docs, posted to Basecamp on 13 Oct 2026. Those docs are the source of truth; this file keeps only what changes the code, the tickets or the evidence packs. Figures are estimates for review, not quotes.

- [VV-Co Part B — Key aspects](https://app.basecamp.com/4531610/buckets/49226321/documents/10399563327): competition, demand, regulation, business model, partnership, risks, GTM and KPIs
- [VV-Co Phased Approach Review](https://app.basecamp.com/4531610/buckets/49226321/documents/10399537046): the four phases, what is already on every bus, the 22-week roadmap
- [VV-Co Part A — Technical architecture](https://app.basecamp.com/4531610/buckets/49226321/documents/10399548939): condensed in `docs/architecture-brief.md`

## Position

Nobody in India sells count-versus-ticket reconciliation at private-operator prices. Global APC vendors are certified but cost €1,500–3,000 per door and have no Indian deployments; Chinese sensor makers are cheap and unaudited; Indian ticketing platforms count nothing yet. VV-Co's defensible position is the **join between Katch's ticket data and a measured count**, entered at ₹0 hardware, with a certified Phase 3 SKU for tenders.

Vendor accuracy claims (97–99.8 %) have never been matched by an independent field test; the only peer-reviewed study on real buses measured 53–83 % (Pronello & Garzón Ruiz 2023). The first published Indian accuracy report sets the benchmark tenders copy (S4-09).

## What each phase promises

| Phase | Operator gets | Promise | Price (draft until G4) | Buyer |
| --- | --- | --- | --- | --- |
| 1 Review | Trip video with ticket and stop markers; ranked trips; manual count entry | Shows where to look | Free for 60 days, then bundled into Phase 2 | Every Katch operator; onboarding |
| 2 Audit | Morning report per trip and stop; flagged trips with clips; conductor and route leakage trends | **Finds leakage**, not "counts to ±1"; 85 % is enough because gaps aggregate by conductor and week | ₹750 per bus-month list; ₹600 at ≥ 200 buses; ₹500 at ≥ 1,000; or 10–15 % of verified recovered fares | Private operators via Katch |
| 3 Certified | Real-time per-stop counts from dedicated door counters; tender-grade accuracy report | **≥ 95 %** per stop, measured | ₹60–90k per bus one-time + ₹1,000–1,500 per bus-month | STUs, e-bus OEMs, GCC operators, premium intercity |
| 4 Edge | Real-time counts and occupancy on-device | Same model as Phase 2, real time, no video leaves the bus | ₹15–45k per bus one-time + ₹1,000–1,500 per bus-month | Operators wanting live occupancy; STU safety tenders |

Channels: Katch's operator base first (2,500 buses, no new sales team); then e-bus OEMs and Tier-1 integrators, STU tenders (partner with a CRS-registered camera vendor), and AIS-140 device vendors.

## Unit economics (Phase 2, SDK + AI)

| Fleet | All-in cost per bus-month | Variable cost | At price | Variable margin |
| --- | --- | --- | --- | --- |
| 100 buses (pilot) | ₹1,150–1,270 | ₹320–450 | ₹750 | 40–57 %; all-in negative by design |
| 400 buses | ₹455–585 | ₹230–360 | ₹600 | 40–62 % |
| 1,000 buses | ₹300–440 | ₹200–340 | ₹500–750 | 32–73 % |

The biggest lever is the eSIM plan (H-16): with ~16 GB per month of existing headroom, cost at 1,000 buses falls to about ₹220–280. Pricing method (S4-07): cost floor = variable ÷ (1 − 0.65); value ceiling = 10–25 % of recovered value and never above one recovered ₹25 fare a day (≈ ₹650 a month); market anchors = AIS-140 device ≈ ₹250–400 a month, PMPML AI kit ≈ ₹670 a month, Katch's own subscription (H-19).

## Pilot KPIs (S3-09)

Targets are Part B defaults until the pilot operator agrees them (H-18).

| KPI | Definition | Pilot target |
| --- | --- | --- |
| Buses live | Buses with clips and counts in the last 24 h | 10 by week 12 |
| Per-stop accuracy | Boardings within tolerance vs ground truth, by view and crowding | ≥ 90 % top-down uncrowded; ≥ 80 % crowded |
| Flag precision | Flagged trips confirmed by a reviewer | ≥ 80 % |
| Recovered fares | ₹ per bus-month attributed to confirmed flags | ≥ 3× the subscription |
| Review effort | Manager minutes per bus-week | ≤ 15 |
| Data cost | GB per bus-day over eSIM | ≤ 0.6 |
| Churn | Operators cancelling after month 3 | 0 in pilot |

## Ranking before AI (S1-11)

Ticket and GPS data alone rank suspicious trips, so a manager reviews 2–3 % of trips rather than all of them: long dwell at a stop with zero tickets; revenue per km below the route's norm; a conductor whose tickets per stop sit below peers on the same route. Review the top-ranked trips and a random 1 % control sample. Phase 2 feeds the same ranking with AI counts. A 14-hour duty day is 14 hours of video per bus, so without ranking manual review does not scale past a handful of buses.

## DPDP and other rules that shape the code

| Rule | What the code must do | Ticket |
| --- | --- | --- |
| DPDP Act 2023 + Rules 2025 (core duties from 14 May 2027; AI CCTV in scope; penalties up to ₹250 crore) | Operator is fiduciary, VV-Co processor; processor agreement; notice stickers; role-based access with logs; ≤ 30-day video retention; aggregated counts only; no age or gender on identifiable minors | S1-02, S1-09, S1-12, S1-13 |
| Madras HC 2026 proportionality (Puttaswamy) | Per-operator note on purpose (revenue assurance, safety) and minimisation | S1-13 |
| Conductor and union pushback (risk: high) | Operator announces the audit policy (H-05); flags reviewed by humans; no automatic penalties | S1-09, S1-11 |
| BIS CRS (IS 13252 Pt 1) + MeitY ER-01 | Certified models for any new IP camera; written classification for depth-only counters (H-11); record origin and certification per device | S1-02, S3-04, S4-09 |
| AIS-140 / CMVR 125H | Use the mandated GPS as the stop and time source | S1-07 |
| AIS-184 driver drowsiness (2028) | Driver-facing analytics stay out of scope | CLAUDE.md |
| Chinese-origin hardware barred in some STU tenders | Keep a non-Chinese sensor option behind the counter contract; Phase 4 edge box as the tender option | S3-04 |
| CESL e-bus standards (AIS-153, IS 16833) and export (ECE R10, ITxPT, VDV 457) | Post-pilot; design the Phase 4 box to ECE R10 from the start | Backlog below |

## Partnership points that touch the code

The charter (discussion draft, 21 Jul 2026) leaves four items for the shareholders' agreement. Two change what we may build:

- **IP ownership:** VV-Co owns all IP created for it (models, reconciliation logic, app module); pre-existing Katch POS and Upsquare tooling are licensed in (H-20).
- **Data ownership:** the operator owns raw video; VV-Co holds anonymised counts and models; training on an operator's footage needs its permission in the processor agreement (H-20, S2-01).
- **Exclusivity:** Katch is the exclusive distributor for its operator base for a defined term; VV-Co is free to sell to OEMs and tenders. No code impact yet.
- **Pilot accuracy metric:** agree a VDV 457-style per-stop protocol and the 85 % / 95 % thresholds before the pilot (H-18).

## Risks the build mitigates

| Risk | Mitigation in the build |
| --- | --- |
| Accuracy below 85 % on oblique views | G1 records view per door (H-17); harness splits by view; G3 fail path adds door cameras or leads with Phase 3 |
| eSIM data cost higher than modelled | Stop-window pulls only; S1-05 measures GB per bus-day against the plan (H-16) |
| Camera SDK relays through a foreign cloud | G1 relay check (H-14); data-flow note; LAN gateway fallback |
| Katch tickets lack stop or time granularity | S1-05 checks it; S1-11 trip-level mode |
| FOORIR terms or BIS status disappoint | Counter contract, Milesight adapter, conformance kit (S3-04) |
| A ticketing incumbent (Chalo) adds counting | Ship Phase 1 fast; publish the accuracy report (S4-09) |
| ₹15 lakh budget overrun | Budget cap in the cloud account (H-03); CPU-only inference is enough for the 10-bus pilot |

## Open business questions (owned by people)

| Question | Input |
| --- | --- |
| eSIM plan size per bus today | H-16 |
| Camera positions per bus type; any top-down door view? | H-17 |
| Pilot operator, cities and 10 buses; why the demo vehicle KA07B3155 is registered at Kolar RTO, outside Katch's published footprint | H-05 |
| Who signs the DPDP processor agreements and owns the notice template | H-05 |
| Pilot success metrics and accuracy protocol | H-18 |
| What Katch charges operators today; the pilot pricing hypothesis | H-19 |
| FOORIR quote, MOQ, lead time, warranty, BIS R-number | H-01 |
| Training rights, IP and licence terms in the SHA | H-20 |
| Did the two-stereo-counter, ≥ 95 % clause survive into the final PM-eBus Sewa Volume 3? Who won BMTC's 30-bus trial, at what price? Is Chalo building counting? Will target STU tenders bar Chinese-origin sensors? Is RTM a supplier, a shareholder via Upsquare, or outside? | Business track; no ticket depends on them yet |

## Post-pilot backlog (not in the four sprints)

- Phase 3 tender integration: AIS-153 (ITS/PIS) and ITxPT data export; integrate at e-bus prototype approval, not retrofit.
- Phase 4 box hardening: ECE R10 EMC, ISO 16750, Indian assembly for tenders.
- Opt-in attribute module (Jetson-class) only with a legal design: aggregate per trip, no frames stored, nothing on identifiable minors.
- AIS-140 vendor bundle to reach non-Katch operators.
- Second product line in year 2: Phase 4 for live occupancy.
