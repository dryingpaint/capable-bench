# Golden-trace feasibility — can we generate fully-accurate mechanistic reasoning?

**Date:** 2026-05-13
**Question:** if we wanted to attach a *golden trace* (canonical mechanistic explanation) to every pairwise / ranking task so that the gold answer is auditable rather than just stated, how accurately can we actually do it given the data we have?

## TL;DR

- **For tasks where both peptides come from the same parent series:** confidence ~80% is achievable. The gold label is overdetermined by the observed lab data; the modification effects line up with established family SAR; the remaining uncertainty is per-modification attribution in combo variants.
- **For tasks where the two peptides come from different parent backbones:** confidence drops to ~60%. The observed potency ratio mixes a *backbone effect* (different starting potencies) with a *modification effect*. We can't decompose them without parent reference data we don't currently store in the panel.
- **The most common source of irreducible uncertainty isn't biology — it's panel construction:** the curated `modification` field strips backbone context, so even literature-perfect peptides become non-comparable when their parents differ.

## Two case studies

### Case 1 — `pilot-peptide-pairwise-sequence-nps-easy-011`

Truncated NPS-(1–17)-NH₂ (compound `NPSv26.2`, 6 records, full agonist 1.0 nM) vs combo-modified NPSv14 (3 records, partial agonist 60 nM, β-arrestin-dead). **Common implicit parent (the native NPS sequence).** Mechanistic rationale is well-supported:

- N-terminal active core preserved in the winner; modified at position 1 in the loser (HIGH confidence — established NPS SAR).
- Truncation removes the C-terminal AKS tail (known dispensable region; HIGH).
- Internal C16-palm at K12 is the wrong lipidation topology (MEDIUM).
- Emax loss + β-arrestin functional loss point to a biased partial-agonist phenotype; cannot be quantitatively decomposed without single-modification controls (SPECULATIVE on attribution).

**Overall confidence: ~80%.** See [`golden_trace_nps-easy-011.md`](golden_trace_nps-easy-011.md).

### Case 2 — `pilot-peptide-pairwise-sequence-mch-easy-011`

`[Ala17]hMCH` vs `MCH core19 D-Cys7`. Both have rich Bednarek 2001 literature provenance. **But:**

- `[Ala17]hMCH` is from Bednarek 2001 **Table 1**: alanine scan on the full hMCH backbone.
- `MCH core19 D-Cys7` is from Bednarek 2001 **Table 5**: D-amino-acid scan on **compound 19** — Bednarek's truncated cyclic-core MCH analog.

These are different parent backbones. The observed 30× MCHR1 binding gap mixes the *backbone potency difference* (hMCH ≪ compound 19 in IC50) and the *D-Cys7 modification effect* (~100× linearization penalty). The benchmark task as constructed cannot distinguish these from the inputs shown to the agent.

**Overall confidence: ~60%** with current panel data, ~85% if we add the parent rows from Bednarek 2001 (which exist in the published paper but not in our curated set).

See [`golden_trace_mch-easy-011.md`](golden_trace_mch-easy-011.md).

## What the case studies tell us about "fully accurate" mechanistic reasoning

**Achievable when these all hold:**

1. The two peptides are deltas off the same parent. (Or one is the parent itself.)
2. The parent's wild-type EC50 is also in the panel (so deltas can be quantified relative to it).
3. The modifications individually have published family-SAR precedent.
4. The lab data is rich enough (≥3 records per peptide, multiple receptors/assays, consistent direction) that the gold is overdetermined.

**Not achievable from current data when:**

1. The two peptides come from different literature sources / different parent series. The MCH panel mixes these.
2. The peptide is a combo variant with multiple simultaneous modifications and no single-mod controls. We can describe each modification's likely effect but cannot quantitatively attribute the observed potency gap.
3. The `modification` field is a stub like `D-Cys7` or `Trp17 f Ala` whose interpretation requires a parent reference we don't store.

## Concrete recommendations if we want to actually build the golden-trace corpus

In rough order of effort/value:

1. **Extend the curator to write `parent_compound_id` and `parent_best_ec50_nm` into each task's metadata where applicable.** Many of our peptides are deltas off a small set of reference parents (full hMCH, MCH compound 19, native NPS, NPSv1.0, etc.). Adding the parent reference makes any delta-vs-delta task reasonable to explain mechanistically.
2. **Drop pairwise tasks where the two peptides have different parent series and no parent data is in the panel.** That's the MCH easy-011 failure mode. Either reconstruct full sequences from delta + parent, or exclude.
3. **Add a `gold_reasoning` field to answer YAMLs with a 3-tier confidence-labeled rationale** (HIGH / MEDIUM / SPECULATIVE), produced by an LLM-with-verifier loop. The NPS easy-011 example demonstrates this is workable and worth ~80% accuracy for clean tasks.
4. **For the hardest counterintuitive golds (cyclic peptides, biased agonists, partial agonists), commission a single-page expert writeup** rather than rely on auto-generation. These are exactly the diagnostic tasks worth getting right.

## What this means for the broader benchmark

The "no keyword-based evaluation" rule pushes toward objective gold answers — which we already have. **Golden traces are the complement: they make the gold answer auditable.** The two together (objective label + auditable rationale) are what would let an external reader trust the benchmark without needing to re-derive every result from raw data.

The honest answer to "can we get fully accurate mechanistic reasoning?" is:

- **Yes for clean tasks** with common parent + family-SAR precedent + rich lab data (~80% confidence, with explicit uncertainty flags).
- **No for ~30–40% of current tasks** without panel-level fixes — specifically, adding parent compound references and pruning cross-series pairs.

I'd estimate ~40–50 of the 69 sequence-only tasks are in the "clean" category and could get good traces today; the rest need panel work first.
