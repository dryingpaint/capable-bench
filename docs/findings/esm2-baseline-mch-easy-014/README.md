# ESM-2 baseline catches a full-length MCH scaffold

**Date:** 2026-05-14
**Task:** `pilot-peptide-pairwise-sequence-mch-easy-014`
**Context:** Both claude and codex picked the modified 12-mer. Gold is the full-length MCH-like 19-mer.

## Setup

Score both canonicalized peptide sequences with ESM-2-650M masked pseudo-log-likelihood (mean over residues). As a zero-shot baseline, rank the pair by higher mean PLL. Non-canonical residues are mapped to the closest canonical L-amino acid before scoring. No fine-tuning, no potency labels.

This is a sequence-prior probe, not a potency model. Higher PLL means the canonicalized sequence looks more plausible under ESM-2's learned protein prior; it does not imply that naturalness generally causes potency.

## Result

| Pick | Modification | Canonicalized | mean PLL |
|---|---|---|---|
| Gold winner (ESM baseline correct) | `DFDMLRCALGRVYRPCWQV` | `DFDMLRCALGRVYRPCWQV` (19-mer) | **-3.214** |
| Both agents picked | `Ac-Arg-Cys-Met-D-Leu-Gly-Arg-Val-Tyr-Arg-Pro-Cys-Trp-NH2` | `RCMLGRVYRPCW` (12-mer) | **-3.484** |

Gap = 0.270 nats/residue in favor of the full-length MCH-like 19-mer. The experimental gold is the same peptide, with a 30.4x potency ratio over the modified 12-mer.

This example has a larger PLL gap, a larger experimental effect size, and a clearer interpretation than the short-cyclic comparison. ESM-2 is not saying "more natural equals more potent" in general; here, after lossy canonicalization, it favors the sequence retaining a fuller MCH-like scaffold over a shorter modified core that both agents overvalued.

## Full-Probe Calibration

Running the same baseline over all 60 pairwise sequence tasks gives **33/60 = 55%** accuracy, with 3 pairs tied after canonicalization. That aggregate result is weak. This finding should be read as a useful diagnostic case where the unsupervised prior helped, not as evidence that ESM-2 masked PLL is a robust potency predictor.
