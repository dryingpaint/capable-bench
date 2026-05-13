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
