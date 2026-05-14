# Codex misses the D-Citrulline pharmacophore hit (oxn-medium-006)

**Date:** 2026-05-14
**Task:** `pilot-peptide-pairwise-sequence-oxn-medium-006`
**Family:** OXN / OX2R
**Failure mode:** correct-vs-thin SAR reasoning; Codex misses the decisive residue-level modification

## Setup

The task asks the agent to choose the more potent of two OX2R-family peptide analogs from sequence and modification strings only. No potency, efficacy, or assay counts are shown to the agent.

Gold is the lower `best_ec50_nm` peptide in held-out functional in vitro assays.

| Role | Peptide ID | Modification |
|---|---|---|
| Gold winner | `PEP-F9A8AC8ACB` | `RQK GLQGR LYRLL QGSGN HAAGI LT(Nle)-NH2` |
| Loser | `PEP-1644F77D58` | `RSGPPGLQGRLQ(D-Citrulline)LLQASGNHAAGILTM-NH2` |

The experimental effect size is large enough to be diagnostic: loser `3.008 nM` / winner `0.215 nM` = **13.96x** potency penalty.

## What Claude Did

Claude selected the gold winner and named the decisive chemistry:

> "PEP-1644F77D58 is orexin-B with a D-Citrulline replacing a conserved mid-sequence arginine -- a combined D-stereochemistry + charge-loss modification at a key pharmacophore residue that typically causes a large EC50 increase at OX2R."

[Full Claude trace](traces/claude.jsonl)

Claude identifies all of the important pieces:

- `D-Citrulline`
- replacement of a conserved Arg
- charge loss from Arg to neutral citrulline
- D-stereochemistry at a receptor-engaging residue
- the combined mechanism as a large potency penalty

## What Codex Did

Codex picked the wrong peptide. Its reasoning never names the key modification:

> "The two candidates are both amidated OXN/OX2R peptide analogs. I'm comparing them against the recognizable orexin-B-like motif and the likely impact of truncation/substitution versus a single noncanonical residue."

[Full Codex trace](traces/codex.jsonl)

That is a generic sequence-level comparison. It does not mention `D-Citrulline`, does not identify the Arg-to-citrulline charge loss, and does not explain why this "single noncanonical residue" dominates the potency comparison.
