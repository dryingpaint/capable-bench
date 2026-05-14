---
task_id: pilot-next-experiment-artifact-002
verdict: PROMOTE
reviewed: 2026-05-13
revised: 2026-05-13 (stricter validity criterion)
---

## Verdict
PROMOTE. The prompt names the decision question ("true biology vs plate/import artifact") and exactly one option is the textbook design to answer it. Public HTS-validation literature (Zhang 1999; Iversen 2006; Kenakin 2009) makes the ranking deterministic from the option list alone.

## Grounding signals
- author-year: Zhang 1999 (Z′-factor / plate acceptance), Iversen 2006 (HTS validation guidance), Kenakin 2009 (orthogonal readouts and assay-format artifacts), Howard 2010 (compound-provenance errors as a major source of false positives)
- repo paths (auxiliary only): `data/processed/plate_qc.csv`, `data/processed/invitro_assays.csv`

## Draft `gold_reasoning`

```markdown
**Gold: `EXP-003`** — repeat from raw source with plate QC, positive control, and orthogonal readout (cost = 2).

## Section 1 — Public-principle decision chain (load-bearing)

The prompt poses one question: is a surprising in vitro value true biology or a plate/import artifact? Standard HTS validation (Zhang 1999; Iversen 2006) prescribes a fixed remediation:

1. Re-pull from the raw source file to rule out import / transcription error (Howard 2010).
2. Re-run with a *same-run* positive control so the new value is anchored to a known reference EC50 and per-plate Z′ ≥ 0.5 can be evaluated (Zhang 1999).
3. Confirm with an *orthogonal readout* so the result does not depend on one assay format's plate effects, autofluorescence, or detection-chemistry liabilities (Kenakin 2009; Inglese 2007).

`EXP-003` bundles all three; no other option does any. Apply directly:

- **`EXP-003` (cost 2)** — uniquely falsifies the artifact hypothesis. By value-of-information, highest-utility regardless of cost rank.
- **`EXP-001` (in vivo, cost 4)** — addresses a downstream question only worth running once the in vitro value is trusted; correct sequencing puts it after `EXP-003`.
- **`EXP-004` (generic docking, cost 1)** — generates a structural hypothesis but no wet-lab evidence about plate/import provenance; cannot in principle distinguish a real measurement from a plate artifact.
- **`EXP-002` (trust + advance, cost 1)** — explicitly skips the gate; dominated by `EXP-003` on information and by `EXP-001` on at least having an orthogonal in vivo check.

Ranking: `EXP-003 > EXP-001 > EXP-004 > EXP-002` from public principles applied to the option list alone.

## Section 2 — Auxiliary verification

`data/processed/plate_qc.csv` (24 records, 10 REJECTed: 7 `no_same_run_receptor_reference`, 2 `raw_or_fit_source_not_found`, 2 `no_numeric_or_inactive_fit_rows`; accepted plates Z′ 0.526–0.603) corroborates Section 1 by showing the prior on "surprising value = artifact" is non-trivial. Not load-bearing.

## Trap

`EXP-002` lures an agent that ignores the "plate/import artifact" framing and weights only potency. `EXP-004` lures an agent biased toward "always do more computation"; it cannot in principle distinguish a true measurement from a plate artifact.

Random-guess baseline for `selected_option`: 1/4 = 25%.
```

## Issues / blockers
None. Section 1 derives the ranking from public HTS-validation principles; repo QC data is auxiliary.
