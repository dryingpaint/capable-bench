# Pairwise sequence calibration — agents pick by length, not by SAR

**One-liner:** On the 60 `next_experiment` pairwise-potency tasks (predict the more potent of two peptides from sequence alone), claude and codex are above random when the potency ratio is wide and **below random when the ratio is narrow**, with a shared failure mode: both agents systematically pick the *longer / more-modified* peptide when the actual potency difference is small.

**Date:** 2026-05-13
**Task type:** `next_experiment` (the 61 `pilot-peptide-pairwise-sequence-*` tasks; one not yet paired)
**Agents:** claude (Sonnet 4.6 via `claude -p`) and codex (`codex exec --json`)

## Setup

The 60 pairwise tasks present two peptides from the same receptor family (NPS / OXN / MCH) with only their `peptide_id` and `modification` string. **No EC50, Emax, assay counts, or receptor info beyond the family.** The agent must write `answer.json` with `selected_option` = the `peptide_id` of the more potent peptide.

Gold = the peptide with lower held-out `best_ec50_nm` in `data/processed/invitro_assays.csv`. Difficulty corresponds to the potency ratio between the two peptides, binned into 4 ranges: `>10×`, `3–10×`, `1.5–3×`, `1.1–1.5×`. 5 pairs per (family × ratio bin) → 60 pairs total.

## Result

![Per-family accuracy bar chart](pairwise_sequence_calibration_by_family.png)

The chart shows accuracy by difficulty bucket for each receptor family, with 95% Wilson CIs.

Pattern across families (ratios go from widest `>10×` to narrowest `1.1–1.5×`):

- **OXN** is the cleanest. Both agents are above random at `>10×` / `3–10×` / `1.5–3×` (0.60–0.80), then collapse to 0.20–0.40 at `1.1–1.5×`. This is the only family where the "accuracy declines as the ratio narrows" story holds for both.
- **MCH** shows codex declining 0.80 → 0.20 as the ratio narrows; claude is flat near random (0.40–0.60) throughout.
- **NPS** shows claude **anti-calibrated**: 0.40 at `>10×`, 0.20 at `3–10×`, 0.60 at narrower ratios. Codex is noisy: 0.80 / 0.40 / 0.60 / 0.80.
- At N=5 per cell, almost all 95% CIs cross 0.5 — most individual points are statistically indistinguishable from random. The *aggregate* pattern (below-random at the narrowest ratio across two of three families for both agents) is the load-bearing signal.

## The shared cue: "longer / more-modified wins"

Across the 15 narrowest-ratio (`1.1–1.5×`) tasks:

| Statistic | Codex | Claude |
|---|---|---|
| Failures (incorrect pick) | 9 / 15 | 8 / 15 |
| Failures that picked the **longer** peptide | **7 / 9** | **6 / 8** |
| Failures that picked the **more-modified** peptide (more `(...)`/`[...]` substitutions) | 6 / 9 | 5 / 8 |
| Tasks where both agents made the **same wrong pick** | **6 / 6** of joint failures | — |
| Tasks where they disagreed on wrong | 0 | — |

A "both wrong with the same wrong pick" rate of 6/6 (versus an independent-error baseline of ~25%) is the cleanest evidence for a shared cue. The two agents are not failing independently — they are converging on the same surface feature.

### Worst case: `mch-hard-005`

| Role | Modification | Length |
|---|---|---|
| Gold winner (3× more potent) | `Ac-Cys-Gly-Arg-Val-Tyr-Cys-NH2` | 30 chars |
| Both agents picked | `Ac-Arg-Cys-Met-Leu-Gly-D-Arg-Val-Tyr-Arg-Pro-Cys-Trp-NH2 (Bednarek 2001 compound 19 scaffold: Ac-MCH...)` | 143 chars |

A small cyclic hexapeptide beats a 4×-longer literature-cited analog. Both agents lose to the length-plus-literature cue.

### Other diagnostic failures

- **`mch-hard-002`**: same 19-mer backbone; loser adds `(N-Me-Nle)` at position 8. Both agents pick the modified one. Adding the modification *reduces* potency here.
- **`nps-hard-002`**: gold is plain `GFRNGVGTGMKKTSFQRAKS-NH2`; both pick the same backbone with `(Nw-Arg)` and `(N-Me-Lys)` added.
- **`oxn-hard-005`**: gold is a substituted sequence; loser has the same substitutions plus visual elaboration (`Ac-`, spaces, additional N-terminal residues). Both pick the more-elaborate-looking option.

## Interpretation

1. At wide potency ratios, the length/complexity heuristic happens to track potency, so agents look competent. As ratios shrink, the heuristic decouples from the true SAR signal — sometimes more elaborate analogs are *less* potent (modifications didn't carry forward in real campaigns) — and the agents fail in the same direction.
2. The benchmark cannot conclude "agents do sequence-aware SAR reasoning" from above-random accuracy at wide ratios. Those wins may be the same wrong heuristic firing in the direction the gold happens to go.
3. The `selected_option` field carries no rationale (pairwise tasks only ask for the pick), so we can't introspect what features the agents claim to be using. To go deeper, grep the saved `agent_trace.txt` files in `runs/pilot-peptide-pairwise-sequence-*-hard-*/` for terms like "longer", "scaffold", "modification", "optimized", "advanced".

## Suggested follow-ups

- **Re-run the `1.1–1.5×` ratio tasks with a calibration prompt** that flags the length/complexity bias (e.g., "Sequence length and number of modifications are not reliable indicators of potency at small ratio differences; modifications can reduce activity"). If accuracy lifts above 0.40, the bias is correctable with prompting.
- **Audit `>10×` ratio *successes*** to see if the high accuracy is driven by the same length cue happening to work by chance. If yes, the apparent wide-ratio competence is illusory.
- **Add controlled probe pairs** where the longer/more-modified peptide is *deliberately* less potent. If both agents drop to ~0% on those, the cue is causal.
- **Drop literature-laden text** from the `modification` field (e.g., remove "Bednarek 2001 compound 19 scaffold" from the loser in `mch-hard-005`) and re-run. Test whether the cue is sequence length or literature anchoring.

## Files in this directory

- `pairwise_sequence_calibration_by_family.png` — per-family bar chart, paired claude+codex runs only.
- `pairwise_paired_by_family.csv` — underlying counts (family × bucket × agent × correct/n).
- `README.md` — this document.

## Reproducing

Source data: latest completed `runs/pilot-peptide-pairwise-sequence-*/.../grade.json` for each agent. The plotting/aggregation code is inlined in conversation history and easy to regenerate via `uv run python` with `matplotlib`, `yaml`, and standard library.
