# Benchmark Design

This repo is set up for an agentic benchmark in the style of BioMysteryBench:
each task gives an agent a question plus a working directory containing data
files. The agent can choose its own method, install or run tools if its
environment permits that, and produce a final answer. The evaluator scores the
answer, not the path.

The expanded benchmark concept is BioDiscoveryBench: a biological and
biochemical reasoning benchmark for coding agents that covers translational
candidate decisions, mechanistic hypothesis generation, experiment planning,
end-to-end drug discovery, and foundation-model-augmented discovery. The full
track specification lives in [BioDiscoveryBench](BIO_DISCOVERY_BENCHMARK.md).

## Design Principles

- One task per directory under `data/tasks/<task_id>/`.
- One metadata row per task in `data/tasks/problems.csv`.
- Hidden or private answer material lives under `data/answers/<task_id>.yaml`.
- Task data are copied into an isolated run directory before each attempt.
- Agents are instructed to write `answer.json`; stdout is captured as a fallback.
- Graders are deterministic where possible and can be extended with expert
  rubrics for free-text scientific judgment.

## Task Families

1. `candidate_prioritization`: rank peptides or candidates for advancement.
2. `hit_prediction`: predict whether an in vivo or functional effect will be
   observed.
3. `failure_diagnosis`: identify likely reasons for translational failure.
4. `next_experiment`: choose the next experiment that resolves the dominant
   uncertainty.
5. `mechanistic_hypothesis`: explain a phenotype or assay pattern using
   receptor, pathway, biochemical, or PK/PD reasoning.
6. `experiment_plan`: design a falsifiable experimental campaign with controls
   and decision gates.
7. `drug_discovery_program`: make an end-to-end target, candidate, experiment,
   and development recommendation.
8. `foundation_model_triage`: judge how to use protein, molecule, expression,
   perturbation, structure, or functional-prediction model outputs in a
   discovery decision.

The ingestion path supports the in vitro mastersheet and mouse in vivo
Excel/JSON exports. Benchmark tasks should be curated from linked evidence and
labeled with experimental outcomes or explicit expert rubrics.

Operational ingestion instructions live in [Data Ingestion](DATA_INGESTION.md).

## Ground Truth

For benchmark tasks, use:

- linked mouse outcomes for candidate prioritization and hit prediction,
- curated expert labels for failure diagnosis and mechanistic hypothesis tasks,
- expert or counterfactual utility labels for next-experiment selection,
- hidden expert rubrics and historical decision outcomes for end-to-end program
  tasks,
- held-out experimental data, expert review, and provenance-aware checks for
  foundation-model-augmented tasks.

## Scoring Modes

The grader supports four practical scoring modes:

- ranking metrics for `candidate_prioritization`,
- exact label matching for `hit_prediction`,
- option ranking for `next_experiment`,
- lightweight rubric concept checks for `failure_diagnosis`,
  `mechanistic_hypothesis`, `experiment_plan`, `drug_discovery_program`, and
  `foundation_model_triage`.

Rubric concept checks are useful for regression tests and large sweeps, but
scientific creativity and experiment quality should still receive expert review
before any benchmark report claims superiority.
