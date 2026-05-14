# ESM-2 zero-shot flips a pairwise task both agents

**Date:** 2026-05-14
**Task:** `pilot-peptide-pairwise-sequence-mch-hard-005`
**Prior:** Both claude and codex picked the longer peptide; gold is the shorter cyclic hexamer. Worst-case example called out in `[pairwise-sequence-calibration](../pairwise-sequence-calibration/README.md)`.

## Setup

Score both peptides with ESM-2-650M masked pseudo-log-likelihood (mean over residues). Predict the more potent peptide = higher mean PLL. Non-canonical residues are mapped to the closest canonical L-amino acid before scoring; stripped sequences are not tied for this task. No fine-tuning, no labels.

## Result


| Pick                   | Modification                                               | Stripped                | mean PLL   |
| ---------------------- | ---------------------------------------------------------- | ----------------------- | ---------- |
| Gold winner (ESM ✓)    | `Ac-Cys-Gly-Arg-Val-Tyr-Cys-NH2`                           | `CGRVYC` (6-mer)        | **−3.289** |
| Both agents picked (✗) | `Ac-Arg-Cys-Met-Leu-Gly-D-Arg-Val-Tyr-Arg-Pro-Cys-Trp-NH2` | `RCMLGRVYRPCW` (12-mer) | **−3.484** |


Gap = 0.195 nats/residue in favor of the cyclic hexamer. ESM-2 inverts the length cue both agents fell for: the shorter cyclic looks *more* native under the masked-residue prior than the elaborated 12-mer.

This is n=1, and the PLL gap is modest. 