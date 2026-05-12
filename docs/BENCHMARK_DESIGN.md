# Benchmark Design

This repo is set up for an agentic benchmark in the style of BioMysteryBench:
each task gives an agent a question plus a working directory containing data
files. The agent can choose its own method, install or run tools if its
environment permits that, and produce a final answer. The evaluator scores the
answer, not the path.

## Design Principles

- One task per directory under `data/tasks/<task_id>/`.
- One metadata row per task in `data/tasks/problems.csv`.
- Hidden or private answer material lives under `data/answers/<task_id>.yaml`.
- Task data are copied into an isolated run directory before each attempt.
- Agents are instructed to write `answer.json`; stdout is captured as a fallback.
- Graders are deterministic where possible and can be extended with expert
  rubrics for free-text scientific judgment.

## Task Families

1. `candidate_prioritization`: rank peptides for advancement.
2. `hit_prediction`: predict whether an in vivo effect will be observed.
3. `failure_diagnosis`: identify likely reasons for translational failure.
4. `next_experiment`: choose the next experiment that resolves the dominant
   uncertainty.

The ingestion path supports the in vitro mastersheet and mouse in vivo
Excel/JSON exports. Benchmark tasks should be curated from linked evidence and
labeled with experimental outcomes or explicit expert rubrics.

Operational ingestion instructions live in [Data Ingestion](DATA_INGESTION.md).

## Ground Truth

For benchmark tasks, use:

- linked mouse outcomes for candidate prioritization and hit prediction,
- curated expert labels for failure diagnosis,
- expert or counterfactual utility labels for next-experiment selection.
