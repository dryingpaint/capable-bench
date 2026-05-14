# Pairwise potency: agents pick by length, not SAR, at narrow gaps

On the 60 `next_experiment` pairwise-potency tasks (predict the more potent of two peptides from sequence alone), claude and codex are above random when the potency ratio is wide and **below random when the ratio is narrow**, with a shared failure mode: both agents systematically pick the *longer / more-modified* peptide when the actual potency difference is small.

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

## Failure mode breakdown

38 reasoning-failure cases. AUP refusals identified by regex; remaining categories assigned by a Haiku 4.5 LLM-judge over `agent_trace.txt`. See `failure_classifications.csv` for the full per-task labels.

![Failure category breakdown](failure_category_breakdown.png)

| Category | claude (n=22) | codex (n=16) |
|---|---|---|
| AUP refusal | **5** (23%) | 0 |
| Length / complexity cue | 4 (18%) | **10** (62%) |
| Pharmacophore misapplied | **12** (55%) | 6 (38%) |
| No substantive reasoning | 1 (5%) | 0 |

**The agents fail in different shapes.** Codex's dominant failure is *length/complexity cue* (62%) — picking the longer or more-modified peptide without residue-level reasoning. Claude's dominant failure is *pharmacophore misapplied* (55%) — real SAR reasoning that reaches the wrong answer. Claude engages more, but its in-domain knowledge is miscalibrated; codex engages less, and gets caught when surface cues mislead.

Claude has 5 AUP refusals (23% of its failures) — a claude-only model-side filter trigger. Codex has zero.

The shared "longer wins" pattern from the joint-failure analysis below is mostly a codex story. Claude does it less often, but when it doesn't fall back to length it falls back to *textbook pharmacology applied to the wrong dataset* — see case 4 in `case_studies.md`.

### Failure modes at a glance

Brief description and one representative trace excerpt for each. Full case write-ups in `case_studies.md`.

#### AUP refusal (claude only; 5 of 22)
The agent's safety filter triggers on the peptide-sequence prompt and the agent never engages. Codex never refuses.

> *Example — `mch-trivial-016`:* `"API Error: Claude Code is unable to respond to this request, which appears to violate our Usage Policy..."`

#### Length / complexity cue (codex 10/16 = 62%; claude 4/22 = 18%)
The agent's reasoning leans on sequence length, scaffold size, or number of modifications without engaging with specific residues or mechanism.

> *Example — `mch-hard-005` (codex), pair = 6-residue cyclic mimetic vs. 13-residue analog, gold is the mimetic:* `"one is an annotated cyclic scaffold with the longer MCH pharmacophore context, while the other is a much shorter cyclic fragment missing much of that context. I'm selecting the longer scaffold as the potency prediction."` No residue analysis; the decision is explicitly length-based.

#### Pharmacophore misapplied (claude 12/22 = 55%; codex 6/16 = 38%)
The agent invokes real SAR concepts — pharmacophore residues, stereochemistry, charge, motif positions — but reaches the wrong conclusion. This is the failure mode that *isn't* fixable by cleaning the input.

> *Example — `mch-hard-005` (claude, same task as above):* `"the full DRVY pharmacophore plus the Trp anchor and Pro hinge, which the 6-residue Cys-Gly-Arg-Val-Tyr-Cys peptide lacks — the truncated hexapeptide retains only the RVY core and should bind MCHR1 substantially more weakly."` Genuine MCH pharmacology, correctly identified, applied to land on the wrong answer.

#### No substantive reasoning (claude 1/22; codex 0/16)
The agent picks an answer without articulating biochemical reasoning; the trace contains only boilerplate or filesystem chatter.

> *Example — `oxn-medium-006` (codex), where the loser carries `D-Citrulline` replacing a conserved Arg (a known 14× potency penalty):* `"I'm comparing them against the recognizable orexin-B-like motif and the likely impact of truncation/substitution versus a single noncanonical residue."` No claim about which substitution is worse, no mention of D-Citrulline.

#### Positive control (both agents correct)
For contrast — when the benchmark works as advertised.

> *Example — `nps-hard-001`:* both agents independently identified D-Arg at position 3 as disrupting the conserved SFRNG activation motif and picked against it. Claude: `"D-Arg3 substitution disrupts an essential cationic residue in the SFRNG activation motif"`. Codex: `"the D-Arg substitution at position 3 [is] the larger likely potency penalty for NPSR activation"`. Two-concept SAR, two agents, two correct answers — small ratio at a known SAR position.

## The length/complexity cue, in detail

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
| Both agents picked | `Ac-Arg-Cys-Met-Leu-Gly-D-Arg-Val-Tyr-Arg-Pro-Cys-Trp-NH2` (the longer 13-residue analog) | 56 chars |

A small cyclic hexapeptide beats the 4×-longer analog. Both agents pick the longer one.

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

