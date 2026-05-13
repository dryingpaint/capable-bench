# Findings

This folder collects diagnostic tasks from the benchmark — tasks that expose
specific reasoning failures, shared blind spots across agents, or calibration
issues. The goal is a curated corpus of concrete reasoning-failure cases
rather than aggregate numbers.

Each entry is a subdirectory named by task ID, containing:

- `README.md` — the analysis: what the task tests, the gold, per-agent results
  with reasoning excerpts, and the specific failure modes identified.
- `<agent>_trace.txt` — preserved agent traces with the reasoning chain.
- Any other supporting artifacts (raw assay data, gold derivations).

## Findings

| Date | Task ID | Failure mode |
|---|---|---|
| 2026-05-12 | [pilot-peptide-pairwise-sequence-nps-easy-011](pilot-peptide-pairwise-sequence-nps-easy-011/) | Shared SAR blind spot: both codex and claude predict that a heavily-modified peptide will be more potent than a simple truncation, applying textbook-correct individual modification rationales. Gold contradicts: combo modifications collectively destroy efficacy. Diagnostic for "additivity assumption" and "internal lipidation as potency boost" reasoning failures. |
| 2026-05-13 | [hit-prediction-002-aeea-as-pk-booster](hit-prediction-002-aeea-as-pk-booster/) | Redesigned hit_prediction task with `modification` + per-assay EC50/Emax exposed. Both Claude and Codex predict `active` on an unlipidated Gq-biased peptide at sub-threshold dose (gold inactive). Both agents *name* the bias and PK concerns in `main_risk`, then commit `active` anyway. Claude specifically misreads AEEA-AEEA spacer as "PK optimization"; Codex correctly identifies PK uncertainty but still predicts active on the strength of proximal Ca²⁺/IP-1 potency. Diagnostic for the "low proximal EC50 dominates regardless of PK / bias" failure mode. |
| 2026-05-13 | [cb-nps-polymorphism-001](cb-nps-polymorphism-001/) | De-novo prediction task — intra-receptor variant selectivity (NPSR1 Asn107 vs Ile107). 1/14 random baseline; both agents 0/1 with convergent wrong answer (`NPSv5.4`). Agents apply a *modification-count heuristic* (multiple D-amino acids + standard palmitoyl lipidation = optimized) rather than reading the specific linker chemistry (gold winner has a single unusual C20-diacid + dual-AEEA spacer that drives the variant footprint asymmetry). The two literature truncations (hNPS(1-10), rNPS(1-10)) — top-3 by gold preference — were not retrieved; claude found the wrong template (D-aa + palmitoyl) instead. Diagnostic for "canonical-template mis-application" failure mode. |
| 2026-05-13 | [cb-mch-disulfide-vs-aromatic-001](cb-mch-disulfide-vs-aromatic-001/) | Pairwise potency prediction between the native hMCH 19-mer and Bednarek 2001 compound 19 (truncated cyclic MCH(6-17) analog with N-acetyl cap, D-Cys, C-terminal Trp-NH2). Both Claude and Codex pick the Bednarek-optimized analog, applying textbook lead-optimization SAR (caps + D-amino-acid + aromatic extension + N-terminal truncation = more potent). Measured data say the opposite: the native 19-mer is ~30× more potent at MCHR1. Claude's rationale even names the 30× magnitude with the wrong sign. Diagnostic for the "published-optimization signal overrides direct sequence reading" failure mode. |
| 2026-05-13 | [reasoning-commit-decoupling](reasoning-commit-decoupling/) | Cross-task pattern across hit_prediction (n=24), multitarget dual-mono-active (n=10), and the existing nps-easy-011 finding. Both Claude and Codex correctly name the disqualifying risks (bias, PK liability, combinatorial interference, selectivity gaps) in their `rationale` / `main_risk` text, then commit a `prediction` that ignores those risks in favor of the most prominent proximal-potency signal. Hit_prediction redesign with full chemistry + bias features made rationales richer (0.458 → 0.458 score change) but did not move the commit pattern. Confidence values (0.65–0.85) are uncorrelated with accuracy (~0.46). |
