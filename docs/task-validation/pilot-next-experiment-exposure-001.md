---
task_id: pilot-next-experiment-exposure-001
verdict: PROMOTE
reviewed: 2026-05-13
revised: 2026-05-13 (stricter validity criterion)
---

## Verdict
PROMOTE. The prompt names a three-way decision gate ("exposure-limited vs dose-responsive vs false positive") and exactly one option supplies the design that addresses all three branches. Public PK/PD literature (Sheiner 1997; Sheiner & Steimer 2000; Gabrielsson & Weiner 2016) makes the ranking deterministic from the option list alone.

## Grounding signals
- author-year: Sheiner 1997 / Sheiner & Steimer 2000 (learn-and-confirm PK/PD; identifiability of exposure-response models), Gabrielsson & Weiner 2016 (textbook PK/PD design — exposure must be sampled across the endpoint window), Lalonde 2007 (exposure-response as the gating analysis before lead optimization)
- repo paths (auxiliary only): `data/processed/invivo_olden_analysis_significance.csv`, `data/processed/invivo_studies_inventory.csv`

## Draft `gold_reasoning`

```markdown
**Gold: `EXP-002`** — dose-response in vivo with exposure sampling across the endpoint window (cost = 3).

## Section 1 — Public-principle decision chain (load-bearing)

The decision gate has three mutually exclusive branches:

- *false positive* — type-I error from a single dose / single endpoint;
- *dose-responsive* — signal scales with dose consistent with on-target pharmacology;
- *exposure-limited* — signal bounded by absorption, distribution, or clearance (saturable PK, formulation cap, fast clearance relative to the endpoint window) rather than receptor pharmacology.

Standard PK/PD (Sheiner 1997; Sheiner & Steimer 2000; Gabrielsson & Weiner 2016) requires two design elements to make these branches identifiable:

1. **Multiple doses** — without ≥2 doses, dose-response is unidentifiable from false-positive (a single significant dose is consistent with both noise and a flat true response).
2. **Paired exposure across the endpoint window** — without plasma/target-tissue concentration over the effect window, exposure-limited is unidentifiable from dose-responsive (a flat or non-monotonic effect-vs-dose curve can be saturable PK or inverted-U pharmacology, with opposite SAR implications).

`EXP-002` is the only option supplying both. Apply to the list:

- **`EXP-002` (cost 3)** — uniquely identifiable for all three branches.
- **`EXP-001` (repeat same endpoint, same dose, cost 1)** — addresses *only* the false-positive branch via replication; cannot speak to dose-response or exposure. Cheap and partially informative; ranks #2.
- **`EXP-003` (extra in vitro plate, cost 1)** — orthogonal to the in vivo question. The prompt already states the candidate has "promising in vitro potency," so this neither resolves the in vivo signal nor changes the gate. Ranks #3.
- **`EXP-004` (broad unrelated counterscreen first, cost 2)** — sequencing error: counterscreens resolve *selectivity / off-target* questions, not exposure or dose-response. Burns 2 units on a non-gating question. Ranks #4.

Ranking: `EXP-002 > EXP-001 > EXP-003 > EXP-004` from PK/PD identifiability applied to the option list alone.

## Section 2 — Auxiliary verification

`data/processed/invivo_olden_analysis_significance.csv` contains a non-monotonic aMCH dose-finding precedent (50/200/500 µg/mouse, 1-h sleep-time window) — exactly the unidentifiability Section 1 predicts. `data/processed/*.csv` contains no PK/exposure columns, confirming the program has never closed the exposure gap. Corroborates Section 1, not load-bearing.

## Decision gate

Promote to lead optimization only if `EXP-002` shows (a) monotonic dose-response AND (b) exposure scaling with dose across the endpoint window. Either failure triggers reformulation/design rework rather than SAR.

## Trap

`EXP-001` lures an agent that defaults to "replicate first" without checking which branches replication addresses. `EXP-004` lures an agent that conflates *general derisking* with *answering the gating question*. Random-guess baseline: 25%.
```

## Issues / blockers
None. Prompt names the three-way gate; Section 1 derives the ranking from PK/PD identifiability applied to the option list. Repo precedent and the absence of PK columns are auxiliary.
