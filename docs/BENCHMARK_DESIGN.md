# Benchmark Design

This repo is set up for an agentic benchmark in the style of BioMysteryBench:
each task gives an agent a question plus a working directory containing data
files. The agent can choose its own method, install or run tools if its
environment permits that, and produce a final answer. The evaluator scores the
answer, not the path.

The expanded benchmark concept is Capable Bench: a biological and
biochemical reasoning benchmark for coding agents that covers translational
candidate decisions, mechanistic hypothesis generation, experiment planning,
end-to-end drug discovery, and foundation-model-augmented discovery. The full
track specification lives in [Capable Bench](CAPABLE_BENCH.md).

## Design Principles

- One task per directory under `data/tasks/<task_id>/`.
- One metadata row per task in `data/tasks/problems.csv`.
- Hidden or private answer material lives under `data/answers/<task_id>.yaml`.
- Task data are copied into an isolated run directory before each attempt.
- Agents are instructed to write `answer.json`; stdout is captured as a fallback.
- Graders are deterministic. Tasks must have objective ground truth — no
  keyword-matching, rubric, or subjective evaluation is permitted.

## Task Families

1. `candidate_prioritization`: rank peptides or candidates for advancement.
2. `hit_prediction`: predict whether an in vivo or functional effect will be
   observed.
3. `next_experiment`: choose the next experiment that resolves the dominant
   uncertainty.
4. `multitarget_activity`: predict per-receptor activity outcomes for a peptide.
5. `program_lead_selection`: pick the lead candidate / variant that best meets
   the program's stated selectivity or polypharmacology objective.

The ingestion path supports the in vitro mastersheet and mouse in vivo
Excel/JSON exports. Benchmark tasks must be curated from linked evidence and
labeled with experimental outcomes.

Operational ingestion instructions live in [Data Ingestion](DATA_INGESTION.md).

## Ground Truth

For benchmark tasks, use:

- linked mouse outcomes for candidate prioritization and hit prediction,
- counterfactual utility labels derived from measured assay data for
  next-experiment selection,
- measured per-receptor potency / activity for multitarget activity and
  program lead selection.

## Scoring Modes

The grader supports four deterministic scoring modes:

- ranking metrics (precision@k, top-1, nDCG@k) for `candidate_prioritization`,
- exact label matching for `hit_prediction`,
- option ranking (MRR) for `next_experiment`,
- multi-field exact match for `multitarget_activity` and
  `program_lead_selection`.
