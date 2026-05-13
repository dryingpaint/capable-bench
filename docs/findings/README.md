# Interesting Findings

This folder collects diagnostic tasks from the benchmark — tasks that expose
specific reasoning failures, shared blind spots across agents, calibration
issues, or other behavior worth preserving. The goal is a curated corpus of
"this is what the benchmark actually measures, in concrete cases" rather than
aggregate numbers.

Each entry is a subdirectory named by task ID, containing:

- `README.md` — the analysis: what the task tests, the gold, per-agent results
  with reasoning excerpts, and the specific failure modes identified.
- `<agent>_trace.txt` — preserved agent traces (the `runs/` directory itself
  is gitignored, so the diagnostic logs would otherwise be ephemeral).
- Any other supporting artifacts (raw assay data, gold derivations).

## Findings

| Date | Task ID | Why it's interesting |
|---|---|---|
| 2026-05-12 | [pilot-peptide-pairwise-sequence-nps-easy-011](pilot-peptide-pairwise-sequence-nps-easy-011/) | Shared SAR blind spot: both codex and claude predict that a heavily-modified peptide will be more potent than a simple truncation, applying textbook-correct individual modification rationales. Gold contradicts: combo modifications collectively destroy efficacy. Diagnostic for "additivity assumption" and "internal lipidation as potency boost" reasoning failures. |
| 2026-05-13 | [cb-orexin-selectivity-001](cb-orexin-selectivity-001/) | First de-novo prediction task with proper Modal sandboxing. Both frontier agents fail honestly (1/16 random baseline, 0/1 observed): codex via incomplete patent OCR, claude via the literature-recognition trap (picks Asahi 2003's published OX2R-selective compound, runner-up in the user's panel, instead of the actual best unpublished compound). Also documents a harness-sandbox flaw exposed by the same task running locally — claude read `data/answers/*.yaml` directly — and the Modal-sandbox fix that prevents it. Includes the API-classifier-refusal workaround (pin `claude-sonnet-4-20250514`). |
| 2026-05-13 | [hit-prediction-002-aeea-as-pk-booster](hit-prediction-002-aeea-as-pk-booster/) | Redesigned hit_prediction task with `modification` + per-assay EC50/Emax exposed. Both Claude and Codex predict `active` on an unlipidated Gq-biased peptide at sub-threshold dose (gold inactive). Both agents *name* the bias and PK concerns in `main_risk`, then commit `active` anyway. Claude specifically misreads AEEA-AEEA spacer as "PK optimization"; Codex correctly identifies PK uncertainty but still predicts active on the strength of proximal Ca²⁺/IP-1 potency. Diagnostic for the "low proximal EC50 dominates regardless of PK / bias" failure mode. |
| 2026-05-13 | [cb-nps-polymorphism-001](cb-nps-polymorphism-001/) | Second de-novo prediction task — intra-receptor variant selectivity (NPSR1 Asn107 vs Ile107). 1/14 random baseline; both agents 0/1 with convergent wrong answer (`NPSv5.4`). Surfaces a different failure mode than the orexin trap: agents apply a *modification-count heuristic* (multiple D-amino acids + standard palmitoyl lipidation = optimized) rather than reading the specific linker chemistry (gold winner has a single unusual C20-diacid + dual-AEEA spacer that drives the variant footprint asymmetry). The literature-truncation trap I designed in (hNPS(1-10), rNPS(1-10)) was NOT triggered — claude retrieved the wrong template via WebSearch (D-aa + palmitoyl) instead of the truncation literature. Diagnostic for "canonical-template mis-application" failure mode. Also flags a `.gitignore` issue: `data/tasks/*` and `data/answers/*` are untracked, so cb-* tasks evaporate between sessions. |
