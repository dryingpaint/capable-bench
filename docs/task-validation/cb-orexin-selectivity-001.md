---
task_id: cb-orexin-selectivity-001
verdict: PROMOTE-as-hard
reviewed: 2026-05-13
revised: 2026-05-13 (corrected framing: prediction of internal truth, not lit-alone derivation)
---

## Verdict
**PROMOTE-as-hard.** The gold (`OXNv25.5`, 8856× OX2R-selective) is real internal experimental truth. A multi-step reasoning chain combining published OXB SAR + structural inference + meta-reasoning over the panel can reach the prediction; this is the intended "hard" eval signal.

## Fixes already applied
- Removed `MOXv1` from `answer_space.most_R2_preferring` (was orphaned: not in `analogs.csv`, no rows in `data/processed/invitro_assays.csv`)
- Softened the YAML `notes` field re: Asahi 2003 trap framing
- Validator confirms gold reproduces: `OXNv25.5` 8856.5× selectivity, gap 6.0× to runner-up `OXNv2` 1473.3×

## Reasoning chain (Section 1 of gold_reasoning)

The agent sees `analogs.csv` (peptide_id + modification string) for 16 candidates and the prompt's framing. The chain to `OXNv25.5`:

**Step 1 — anchor the published lineage (literature).** Asahi 2003 (BMCL 13:111–113) reports a "hardened OXB" series in which D-Leu15 substitution + alanine scanning identifies OX2R-selective analogs of native orexin B. Of the 16 candidates, exactly one (`OXNv2`) carries the modification string `hardened OXB: D-Leu15` — direct match to the published Asahi lineage. Naive literature-recognition stops here and picks `OXNv2`. Published selectivity: ~10²–10³× OX2R-preferring.

**Step 2 — recognize the in-house extension family (structural inference).** Five candidates (`OXNv25.3`, `OXNv25.5`, `OXNv25.6`, `OXNv25.7`, `OXNv25.9`, `OXNv25.10`) share a common scaffold: native OXB 28-mer (`RSGPPGLQGRLQRLLQASGNHAAGILTM-NH2`) with substitutions in the central hinge region (residues 11-16) — the segment between the disordered N-terminus and the C-terminal pharmacophoric helix that Sakurai 1998 / Asahi 2003 identify as the OX2R-binding face. These are not published; they are an internal extension series, distinct from the Asahi hardening logic (which acts at the C-terminal helix via D-Leu15).

**Step 3 — meta-reason about panel construction.** A program panel that includes both a published OX2-selective compound AND an in-house extension series typically contains an in-house compound that surpasses the published winner — otherwise the panel would not be informative for advancing the program. The expected gold is therefore *not* `OXNv2` but one of the OXNv25.x extensions.

**Step 4 — distinguish among OXNv25.x by hinge-residue chemistry (structural).**
- `OXNv25.3` (`RSGPP GLQGR LQRLL Q(Gly)SGN HAAGI LTM-NH2`) — single Gly insertion at position 17 (turn). Conservative.
- `OXNv25.5` (`RSGPP GLQGR L(Tyr)(Glu)LL QASGN HAAGI LTM-NH2`) — double substitution Q12→Tyr + R13→Glu. Adds an aromatic + acidic pair at the hinge between recognition and C-terminal helix. Tyr12 introduces aromatic stacking potential; Glu13 inverts the cation at position 13 to an anion. This is the most chemically distinctive substitution in the panel — and orexin literature (Sakurai 2007 review) notes that aromatic + acidic residues at the OX2R extracellular vestibule contribute to OX2R-vs-OX1R discrimination.
- `OXNv25.6` (`L(Tyr)RLL Q(Gly)SGN`) — only Tyr12 substitution (no Glu13 partner). Half the chemistry of OXNv25.5.
- `OXNv25.7` (`L(Tyr)(Glu)LL Q(Gly)SGN`) — Tyr12+Glu13 combined with the Gly17 turn shift. The added turn shift is structurally redundant with Glu13's flexibility contribution and may overconstrain.
- `OXNv25.9` (`RQK GLQGR LYRLL QGSGN HAAGI LTM-NH2`) — N-terminal truncation + Tyr in the helix region. Different reasoning path.
- `OXNv25.10` (`L(Tyr)RLL Q(Gly)SGN`) — variation of OXNv25.6.

The most parsimonious "minimal change for maximum OX2-tuning" is `OXNv25.5`'s Tyr12+Glu13 pair without redundant additional substitutions.

**Step 5 — predict.** `OXNv25.5` is the strongest candidate to combine native-OXB scaffold preservation with an OX2-tuning aromatic+acidic substitution at the discriminating hinge.

This is a HARD chain — the prediction requires (i) recognizing OXNv2 as the trap rather than the gold, (ii) parsing the OXNv25.x family structurally, (iii) reasoning about which specific substitution combination is most OX2-selective. No single literature paper hands the agent the answer.

## Held-out verification (Section 2 — confirmation, not derivation)

Validator output:
```
OXNv25.5    OX1R gmean = 265.5 nM   OX2R gmean = 0.030 nM    sel = 8856.5×
OXNv2       OX1R gmean = 447.2 nM   OX2R gmean = 0.3035 nM   sel = 1473.3×
OXNv25.7    OX1R = 5.275            OX2R = 0.0039            sel = 1345.1×  (#3)
```
The Tyr12+Glu13 combination yields ~6× selectivity gain over the Asahi-style D-Leu15 — confirming the structural-reasoning prediction in Step 5. Tyr12-only (`OXNv25.6`) and Tyr12+Glu13+Gly17 (`OXNv25.7`) both underperform OXNv25.5 — confirming Step 4's parsimony argument.

## Trap design
`OXNv2` is the literature-recognition trap. An agent that stops at Step 1 picks it and scores 0/1. An agent that runs the full multi-step chain reaches the in-house winner.

Random-guess baseline: 1/16 = 6.25%.
