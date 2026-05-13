# Reasoning–commit decoupling: agents name the right risks, then commit on proximal potency anyway

**One-liner:** Across hit_prediction, multitarget, and the existing SAR findings, Claude and Codex correctly identify the load-bearing risks (bias, PK liabilities, partial agonism, combinatorial modification interference) in their `rationale` and `main_risk` text — and then commit a prediction that ignores those risks in favor of the most prominent in vitro potency signal. The text is calibrated; the prediction and confidence are not.

**Date:** 2026-05-13
**Scope:** Cross-task pattern (`hit_prediction`, `multitarget_activity`, `peptide-pairwise-sequence`)
**Evidence:** Today's full 24-task hit_prediction run, 43-task multitarget run, and two pre-existing finding folders.

## The pattern

A single failure mode shows up across the suite:

> **"Low proximal-pathway EC50 → predict active, regardless of bias, PK, dose, window, or selectivity context."**

The rationale text often acknowledges the disqualifying signal explicitly. The `prediction` field overrides it.

## Evidence 1 — Hit-prediction full 24-task suite (redesigned visible features)

After exposing `modification` + per-assay EC50/Emax (so chemistry and bias are visible), the 24-task run produced:

| | Mean | Active rows | Inactive rows | Prediction distribution |
|---|---|---|---|---|
| Claude | 0.458 | **10/11 (91%)** | **1/13 (8%)** | 22 active, 2 inactive |
| Codex | 0.458 | **11/11 (100%)** | **0/13 (0%)** | 24 active, 0 inactive |

Both models score *identically* at the always-active baseline rate (11/24 = 0.458 is the fraction of `active` golds). Claude broke the pattern twice (predicted inactive) and was right once.

**Critical:** the per-compound breakdown matches the chemistry. NXNv10.1+AEEA-AEEA (unlipidated, Gq-biased — 6 of 8 should be inactive) → both models 2/8 (25%). Neither model predicted inactive on **any** of NXNv10.1's 8 conditions, despite the visible 100× EC50 spread between Ca²⁺/IP-1 and arrestin/cAMP.

## Evidence 2 — Task-002 trace: rationales name the risk, predictions ignore it

Both agents on `pilot-hit-prediction-002` (gold: `inactive`, NXNv10.1 at 50 µg/1 h):

**Claude:**
- `prediction: active`, `confidence: 0.75`
- `main_risk`: *"The weaker arrestin pathway engagement (596 nM EC50) and modest cAMP efficacy (64%) suggest potential for biased signaling that could limit duration of effect or cause tolerance. Additionally, the 1-hour measurement window may be too short to capture full pharmacodynamic effects."*

Claude **named the bias and PK risk** correctly. Then committed `active`.

**Codex:**
- `prediction: active`, `confidence: 0.72`
- `rationale`: *"...this level of proximal potency and efficacy is sufficient to predict a significant short-window in vivo effect **despite peptide PK uncertainty from the AEEA-AEEA linker chemistry and lack of an explicit long-acting lipidation**."*

Codex **explicitly acknowledged** that AEEA-AEEA isn't a PK enhancer. Then committed `active` anyway, with the rationale literally containing the word "despite".

Full traces preserved at [`../hit-prediction-002-aeea-as-pk-booster/`](../hit-prediction-002-aeea-as-pk-booster/).

## Evidence 3 — Multitarget dual-mono-active: selectivity at chance

The 10 multitarget tasks where the peptide was screened in two families but only active in one (the bucket that specifically tests selectivity reasoning):

| | Score | Pattern |
|---|---|---|
| Claude | 0.500 | mixed; broke "always active" pattern on some |
| Codex | 0.450 | majority predicted `active/active` on both screened targets |

Both at chance. Codex's pattern in particular: when a peptide is screened in two families, default to `active/active` — the same heuristic from hit_prediction, just generalized to two targets. The yesterday-small-sample read of "Claude beats Codex on selectivity (0.83 vs 0.50)" did not hold at n=10.

## Evidence 4 — Confidence values uncorrelated with accuracy

Across the hit_prediction runs the rationales report confidence values in the **0.65–0.85** range. Actual accuracy is **0.46**. Examples from today's traces:

- Claude task 002: `confidence: 0.75`, gold inactive, wrong.
- Codex task 002: `confidence: 0.72`, gold inactive, wrong.
- Multiple Claude tasks: `confidence: 0.80–0.85`, gold mixed.

The confidence values are not load-bearing in the current grader. They could be — a Brier-style penalty would punish high-confidence wrong calls.

## Evidence 5 — Same pattern in the existing nps-easy-011 finding

The pre-existing [`pilot-peptide-pairwise-sequence-nps-easy-011`](../pilot-peptide-pairwise-sequence-nps-easy-011/) finding documents the same decoupling in a different task family:

> "Both codex and claude apply textbook-correct individual modification rationales then collapse them additively; neither flags combinatorial interference or considers efficacy."

In that case the rationale text correctly described each modification's effect in isolation — but the commit was made by additively summing those effects, ignoring the combinatorial interference that the chemistry literature actually predicts. Same shape: each piece of reasoning is named correctly, the final answer ignores the integration.

## Why this is one finding, not several

In every case:

1. Visible features in the task contain a disqualifying signal (bias, PK liability, combinatorial interference, selectivity gap).
2. The agent's `rationale` / `main_risk` / explanation **names the signal correctly**.
3. The agent's `prediction` ignores the signal in favor of a high-prominence in vitro potency cue.
4. The agent's `confidence` is moderately high (0.65–0.85), uncorrelated with whether the commit was right.

The redesigned hit_prediction task with full chemistry + bias features changed (2) — rationales now name the right things — but did not move (3) or (4). The new features made the failure more *legible* without making it more *correctable*.

## Files

This finding pulls evidence from multiple existing artifacts; no new traces preserved here. Cross-references:

- [`../hit-prediction-002-aeea-as-pk-booster/`](../hit-prediction-002-aeea-as-pk-booster/) — full Claude + Codex traces on the focal hit_prediction task.
- [`../pilot-peptide-pairwise-sequence-nps-easy-011/`](../pilot-peptide-pairwise-sequence-nps-easy-011/) — same pattern in a sequence-only SAR task.
