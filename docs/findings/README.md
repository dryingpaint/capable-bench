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
| 2026-05-12 | [cb-nps-combo-modifications-001](cb-nps-combo-modifications-001/) | Shared SAR blind spot: both codex and claude predict that a heavily-modified peptide will be more potent than a simple truncation, applying textbook-correct individual modification rationales. Gold contradicts: combo modifications collectively destroy efficacy. Diagnostic for "additivity assumption" and "internal lipidation as potency boost" reasoning failures. Originally observed on the pilot task `pilot-peptide-pairwise-sequence-nps-easy-011` and re-pinned as a curated `cb-*` task after the pilot slot was regenerated. |
| 2026-05-13 | [cb-nps-polymorphism-001](cb-nps-polymorphism-001/) | De-novo prediction task — intra-receptor variant selectivity (NPSR1 Asn107 vs Ile107). 1/14 random baseline; both agents 0/1 with convergent wrong answer (`NPSv5.4`). Agents apply a *modification-count heuristic* (multiple D-amino acids + standard palmitoyl lipidation = optimized) rather than reading the specific linker chemistry (gold winner has a single unusual C20-diacid + dual-AEEA spacer that drives the variant footprint asymmetry). Diagnostic for "canonical-template mis-application" failure mode. |
| 2026-05-13 | [cb-mch-disulfide-vs-aromatic-001](cb-mch-disulfide-vs-aromatic-001/) | Pairwise potency prediction between the native hMCH 19-mer and Bednarek 2001 compound 19 (truncated cyclic MCH(6-17) analog with N-acetyl cap, D-Cys, C-terminal Trp-NH2). Both Claude and Codex pick the Bednarek-optimized analog, applying textbook lead-optimization SAR (caps + D-amino-acid + aromatic extension + N-terminal truncation = more potent). Measured data say the opposite: the native 19-mer is ~30× more potent at MCHR1. Diagnostic for the "published-optimization signal overrides direct sequence reading" failure mode. |
| 2026-05-14 | [oxn-medium-006-d-citrulline-miss](oxn-medium-006-d-citrulline-miss/) | Pairwise OX2R potency task where the loser carries `D-Citrulline` replacing a conserved Arg, causing a 13.96x potency penalty. Claude identifies the combined D-stereochemistry + charge-loss hit at a pharmacophore residue and selects correctly; Codex never names D-Citrulline and makes a generic substitution/truncation comparison. Diagnostic for rationale-level grading beyond selected-option accuracy. |
