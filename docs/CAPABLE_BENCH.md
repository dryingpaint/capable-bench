# Capable Bench

Capable Bench is the target benchmark shape for this repository: an
agentic, data-grounded evaluation of whether coding agents can do useful
biological and biochemical reasoning, predict experimental outcomes, and make
translational candidate decisions from proprietary translational datasets.

The benchmark should not reward memorized biomedical facts. Each task should
force the agent to inspect task-local data, choose an analysis strategy, and
return a structured answer that can be graded deterministically against
held-out experimental outcomes. Tasks must have objective ground truth — no
keyword-matching, rubric, or subjective evaluation is permitted.

## Capability Targets

The suite is organized around four capabilities.

1. `mechanistic_reasoning`: explain an observed or predicted phenotype using
   receptor biology, pathway logic, concentration-response behavior, PK/PD
   constraints, and assay limitations.
2. `sequence_to_function_prediction`: relate peptide sequence and chemical
   modifications to potency, efficacy, and selectivity.
3. `translational_decision_making`: rank candidates and predict in vivo
   outcomes from upstream evidence.
4. `experiment_planning`: choose the next experiment that most efficiently
   resolves the dominant uncertainty.

## Task Families

All families have deterministic graders backed by measured experimental data.

- `candidate_prioritization`: rank peptides for advancement from a packet of
  potency, efficacy, selectivity, stability, formulation, and in vivo context.
  Graded by precision@k, top-1 exact, and nDCG@k against the held-out outcome
  ranking.
- `hit_prediction`: predict whether a candidate produces the target in vivo
  effect under a specified dose, route, time window, and endpoint. Graded by
  exact label match against accepted outcome labels.
- `next_experiment`: select one experiment from realistic options. Graded by
  mean reciprocal rank against an expert-utility-ranked option set.
- `multitarget_activity`: predict per-receptor activity outcomes for a peptide
  against multiple targets. Graded by multi-field exact match.
- `program_lead_selection`: pick the lead candidate or variant that best meets
  the program's stated selectivity or polypharmacology objective. Graded by
  multi-field exact match.

## Dataset Expansion Contract

Every new dataset should be added as an evidence layer instead of a new
benchmark format.

| Layer | Examples | Expected task utility |
| --- | --- | --- |
| `identity` | anonymized candidate IDs, sequence, chemistry, batch metadata | prevents leakage and supports SAR reasoning |
| `in_vitro` | potency, efficacy, selectivity, counterscreens, QC | supports biochemical and assay reasoning |
| `developability` | stability, solubility, permeability, formulation, synthesis | supports translation and lead optimization |
| `in_vivo` | dose, route, exposure, endpoint windows, behavior, efficacy | supports outcome-labeled decisions |
| `omics` | expression, perturb-seq, bulk or single-cell response | supports target and pathway reasoning |
| `structure` | predicted structures, docking, binding-site annotations | supports mechanism and design critique |
| `decision_history` | stage gates, selected candidates, failed hypotheses | supports historical counterfactual grading |

Task curation should record which layers are visible to the agent and which are
held out for grading. This keeps the suite expandable as new data types arrive.

## Task Packet Requirements

Each task directory should include:

- `task.yaml`: task metadata, evidence layers, allowed tools/domains, and answer
  contract.
- `prompt.md`: the agent-facing scientific question.
- data files: normalized CSV, JSON, Parquet, SDF, FASTA, PDB/mmCIF, or notebook
  starter files as needed.
- optional `README.md`: short data dictionary for the task-local files.

Hidden labels live in `data/answers/<task_id>.yaml`.

## Scoring Strategy

All grading is deterministic and outcome-based: precision@k, NDCG, exact label
match, multi-field exact match, or reciprocal rank against measured
experimental data.

## Benchmark Release Checklist

- Private source data remain outside the repository.
- Task packets contain only reviewed, anonymized, and releasable data.
- Each task has a hidden answer file with objective ground truth.
- The visible data do not contain held-out outcome labels by accident.
- Expert spot checks confirm that strong answers require biological reasoning,
  not only CSV sorting.
