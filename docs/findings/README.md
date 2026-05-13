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
| 2026-05-13 | [peptide-sequence-saturation-2026-05-13](peptide-sequence-saturation-2026-05-13/) | First full Modal run of the 60 sequence-only pairwise + 9 ranking tasks against codex and claude. Both agents at or below chance on pairwise (codex 30/60, claude 26/59); no clean difficulty gradient on the 2×/5–30×/30–100×/≥100× ratio buckets except OXN-Claude. MCH is systematically wrong for both agents (codex 7/20, claude 6/20), with failures splitting into a *format-bias* mode (gold winner is a terse delta, loser is a verbose full sequence; agents pick the verbose one) and a *genuine SAR* mode (agents weight aromatic C-terminal contacts over disulfide-bridge integrity in MCH-(7–17) cyclic peptides). Includes plot + preserved traces + recommendations for normalizing the MCH modification field and increasing per-cell N. |
