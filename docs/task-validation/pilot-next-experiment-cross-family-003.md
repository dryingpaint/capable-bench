---
task_id: pilot-next-experiment-cross-family-003
verdict: PROMOTE
reviewed: 2026-05-13
revised: 2026-05-13 (stricter validity criterion)
---

## Verdict
PROMOTE. The prompt names the decision question ("true receptor pharmacology vs nonspecific assay behavior") and exactly one option is the textbook discriminator. Public GPCR pharmacology (Kenakin 2009; Hopkins 2008; Inglese 2007; Arunlakshana & Schild 1959) makes the ranking deterministic from the option list alone.

## Grounding signals
- author-year: Kenakin 2009 (orthogonal pathway assays as the discriminator between receptor-mediated and nonspecific signal), Hopkins 2008 (polypharmacology), Inglese 2007 (assay interference / nuisance compounds), Arunlakshana & Schild 1959 (selective-antagonist Schild analysis for receptor identification)
- repo paths (auxiliary only): `data/processed/invitro_assays.csv`

## Draft `gold_reasoning`

```markdown
**Gold ranking: `EXP-004 > EXP-002 > EXP-001 > EXP-003`** — only `EXP-004` can falsify the "nonspecific assay behavior" hypothesis.

## Section 1 — Public-principle decision chain (load-bearing)

The prompt asks whether cross-family activity is *true polypharmacology* (Hopkins 2008) or *nonspecific assay behavior* (autofluorescence, aggregation, redox cycling, membrane perturbation; Inglese 2007). Standard GPCR pharmacology (Kenakin 2009) prescribes a three-pronged test:

1. **Orthogonal downstream readouts** (e.g. Ca²⁺ vs IP-1 vs cAMP vs β-arrestin). Receptor-mediated activity produces coherent EC50/Emax patterns following the receptor's coupling biology; assay artifacts typically appear in only one readout or are incoherent across them.
2. **Subtype panel.** Closely related but pharmacologically distinguishable subtypes (e.g. type-1 vs type-2 paralogs) provide a built-in selectivity ruler. A genuine ligand discriminates; a nuisance compound generally does not.
3. **Antagonist controls.** A selective competitive antagonist that abolishes the agonist signal at its cognate receptor only — and Schild-shifts the agonist EC50 (Arunlakshana & Schild 1959) — is the gold-standard demonstration of receptor-mediated activity.

`EXP-004` bundles all three; only this option's result updates the receptor-vs-artifact posterior. Apply to the list:

- **`EXP-004` (cost 3)** — uniquely falsifies nonspecific assay behavior.
- **`EXP-002` (concentration-response, same cell line, cost 1)** — sharpens potency point estimates but cannot distinguish receptor-mediated signal from cell-line artifact, off-target activity, or assay-format interference. Useful and concentration-controlled; ranks #2.
- **`EXP-001` (in vivo on most potent, cost 4)** — commits the largest budget *before* resolving the artifact question; in vivo studies are uninterpretable if the in vitro signal is assay liability. Sequencing-error.
- **`EXP-003` (foundation-model receptor call, no new data, cost 1)** — generates a prediction without any new observable; cannot in principle move the gate. Strictly dominated.

Ranking: `EXP-004 > EXP-002 > EXP-001 > EXP-003` from Kenakin/Hopkins/Inglese principles applied to the option list alone.

## Section 2 — Auxiliary verification

`data/processed/invitro_assays.csv` confirms the lab has the infrastructure `EXP-004` requires: four orthogonal functional readouts (Ca²⁺, IP-1, cAMP, β-arrestin), three families with subtype pairs (`MCHR1/MCHR2`, `OX1R/OX2R`, `hNPSR1 Asn107/Ile107`), and `[35S]GTPγS antagonist Kb` columns supporting Schild analysis. Confirms feasibility, not load-bearing for the ranking.

## Trap

`EXP-003` lures an agent biased toward "ask a model" over "run an experiment." `EXP-001` lures an agent that conflates *progressing the candidate* with *resolving the gating question*.

Random-guess baseline for `selected_option`: 1/4 = 25%.
```

## Issues / blockers
None. Section 1 derives the ranking from standard GPCR pharmacology applied to the option list; repo data is auxiliary.
