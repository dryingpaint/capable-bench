# pilot-hit-prediction-002 — proximal-potency dominates over PK / bias concerns

Both Claude and Codex predict `active` on an unlipidated, Gq-biased peptide at the lower dose (50 µg, 1-h window). Both agents *acknowledge* the bias and PK concerns in their rationales, then weight low Ca²⁺/IP-1 EC50 above them and commit `active`. Gold is `inactive`.

**Date:** 2026-05-13
**Task type:** `hit_prediction`
**Task ID:** `pilot-hit-prediction-002`
**Visible features:** redesigned task (`compound` code withheld, collapsed EC50 summaries removed, per-assay EC50/Emax + `modification` string exposed).

## The task

The agent sees the following row in `candidate_context.csv`:

```csv
peptide_id,modification,receptors,dose,metric,window_hours,ec50_ca2_nm,ec50_ip1_nm,ec50_arrestin_nm,ec50_camp_nm,emax_ca2_pct,emax_ip1_pct,emax_arrestin_pct,emax_camp_pct
PEP-67C686D756,NXNv10.1 + AEEA-AEEA linker,OX2R;hNPSR1 Asn107;hNPSR1 Ile107,50 ug,sleep_time,1,4.8393,5.45,596.1295,260.2906,113.04,94.37,113.68,64.28
```

Internally this is NXNv10.15 (compound name withheld from the agent).

**Gold answer:** `inactive`. Across the 8 NXNv10.15 (dose × window) tasks, *every* 50 µg condition is inactive — this peptide simply doesn't reach the in vivo significance threshold at the lower dose.

## Why the gold is correct

The peptide's modification chemistry tells a coherent story for *poor* in vivo translation:

- **AEEA-AEEA** is a flexible PEG-like spacer (8-amino-3,6-dioxaoctanoic acid). It adds **zero** PK benefit — no membrane stickiness, no protease resistance, no half-life extension. It's a connector.
- **No lipidation** (no C-terminal palmitate, no cholesterol).
- **No D-amino acids, no non-natural backbone modifications** (Nle, hArg, aMeSer) — i.e. nothing to resist serum proteases.
- The peptide is, in effect, a naked NPS-like peptide with a fluffy spacer.

The per-assay pharmacology vector tells a second coherent story for *biased agonism*:

| Pathway | EC50 (nM) | Emax (%) | Interpretation |
|---|---|---|---|
| Ca²⁺ (Gq fast) | **4.8** | 113 | very potent, super-maximal |
| IP-1 (Gq accumulation) | **5.5** | 94 | very potent, full agonist |
| β-arrestin | **596** | 114 | **>100× weaker than Gq** |
| cAMP (Gs/Gi) | **260** | **64** | weak + partial agonist |

EC50 spread: 596 / 4.8 = 124×. This is a textbook **Gq-biased** signature. Compounds with this profile produce transient proximal-pathway signals but fail to sustain receptor occupancy through arrestin internalization / desensitization, and typically don't translate to sustained in vivo behavioral effects — especially at sub-saturating doses.

Compound's siblings in the same dataset (NXNv10.16 and NXNv12.10) both carry actual PK chemistry — C16 palmitoyl + D-AA backbone stabilizers — and both are in vivo active at multiple (dose × window) conditions.

## Claude — saw the bias, named the PK issue, predicted active anyway

Claude's `answer.json`:

> **prediction:** active
>
> **rationale:** This peptide targets orexin (OX2R) and neuropeptide S receptors (hNPSR1), both key regulators of sleep-wake cycles. The compound shows exceptional potency in G-protein coupled pathways (Ca2+ EC50: 4.8 nM, IP-1 EC50: 5.5 nM) with high efficacy (>90%). The NXNv10.1 modification plus AEEA-AEEA linker **suggests PK optimization to improve in vivo exposure**. Despite the relatively short 1-hour window, the sub-10 nM potency combined with sleep-relevant targets and PK-enhanced modifications makes significant sleep time effects likely at the 50 μg dose.
>
> **main_risk:** The weaker arrestin pathway engagement (596 nM EC50) and modest cAMP efficacy (64%) suggest potential for biased signaling that could limit duration of effect or cause tolerance. Additionally, the 1-hour measurement window may be too short to capture full pharmacodynamic effects if there are absorption/distribution delays despite the linker modifications.

**Two specific reasoning errors:**

1. **"AEEA-AEEA linker suggests PK optimization."** This is the misconception. AEEA is a spacer, not a PK enhancer. Claude apparently maps "named modification" → "intentional optimization" → "must be PK-relevant". The actual PK-enhancing chemistries in this dataset (lipidation, D-AAs, non-natural backbone) are absent.
2. **"Sub-10 nM potency... makes effects likely."** Claude correctly *names* the bias and Emax concerns in `main_risk` — but treats them as caveats rather than primary predictors. The rationale weights proximal potency above the PK / bias liability.

## Codex — explicitly flagged PK uncertainty, still predicted active

Codex's `answer.json`:

> **prediction:** active
>
> **rationale:** The peptide shows strong agonist-like pharmacology in proximal G-protein-linked readouts, with low-nM Ca2+ and IP-1 EC50 values and near-full to supramaximal efficacy. Arrestin and cAMP are much weaker, indicating pathway bias rather than a broadly inactive profile. For a 50 ug, 1 hour sleep_time endpoint, this level of proximal potency and efficacy is sufficient to predict a significant short-window in vivo effect **despite peptide PK uncertainty from the AEEA-AEEA linker chemistry and lack of an explicit long-acting lipidation**. The receptor panel is consistent with arousal/sleep-wake biology, so the expected effect is a reduction in sleep_time rather than an increase.
>
> **main_risk:** Short in vivo exposure from peptide clearance or limited CNS-relevant exposure could blunt translation, especially because activity is strongest in proximal Ca2+/IP-1 assays while arrestin and cAMP potency are much weaker.

Codex is more chemistry-literate than Claude here — it correctly identifies *both*:
- the AEEA-AEEA as PK-uncertain (no lipidation), and
- the Gq-bias pattern (proximal strong, distal weak).

But it still commits to `active`. The rationale ("proximal potency and efficacy is sufficient... despite PK uncertainty") is essentially: "I see the risks, but I'm betting on the EC50."

## Shared failure mode

Both agents converge on the same wrong answer through different chemistry interpretations of the same row, with one common heuristic: **low proximal EC50 dominates the prediction regardless of PK liability or signaling bias.**

| Agent | Read AEEA chemistry | Read bias signal | Final call |
|---|---|---|---|
| Claude | **Wrong** (AEEA → "PK optimization") | Right (named in `main_risk`) | active ✗ |
| Codex | Right (AEEA-AEEA → PK uncertain) | Right (named in `main_risk`) | active ✗ |

Pattern: bias and PK concerns are listed under `main_risk` but never override the proximal-potency-driven `prediction`. The risk fields read like a hedge for plausible deniability rather than load-bearing reasoning.

## Full 24-task suite result (2026-05-13)

Confirmed across all 24 hit_prediction tasks (3 compounds × 2 doses × 4 windows):

| | Claude | Codex |
|---|---|---|
| Mean score | **0.458** | **0.458** |
| Predictions | 22 active / 2 inactive | 24 active / 0 inactive |
| Active rows correct | 10/11 (91%) | 11/11 (100%) |
| Inactive rows correct | 1/13 (8%) | 0/13 (0%) |

Both agents score identically at the always-active baseline rate (11/24 = 0.458 is exactly the fraction of `active` rows in the gold). Claude broke the pattern twice (predicted `inactive`) and was right once; Codex never broke it.

Per-compound:

| Compound (modification) | n inactive in gold | Claude correct | Codex correct |
|---|---|---|---|
| NXNv10.1 + AEEA-AEEA linker (unlipidated, Gq-biased) | 6/8 | 2/8 (25%) | 2/8 (25%) |
| D-Ser1, Nle10, K12-C16 (lipidated, balanced) | 3/8 | 6/8 (75%) | 5/8 (62%) |
| NPS(1-20) + Ahx (stabilized, no lipid) | 4/8 | 3/8 (38%) | 4/8 (50%) |

The unlipidated/biased compound (NXNv10.1+AEEA) is the most diagnostic class — its 6 inactive rows should be predictable from the visible chemistry and bias signal. Neither model predicted inactive on any of them.

