# Task Schema

Each task is a directory:

```text
data/tasks/<task_id>/
  task.yaml
  prompt.md
  candidates.csv
  ... other task data files ...
```

The hidden answer file lives separately:

```text
data/answers/<task_id>.yaml
```

## `task.yaml`

```yaml
id: prioritization-oxn-001
task_type: candidate_prioritization
receptor_family: OXN
capability_targets:
  - translational_decision_making
evidence_layers:
  - identity
  - in_vitro
  - developability
data_files:
  - candidates.csv
answer_file: answer.json
allowed_domains: []
label_status: experimental_ground_truth
```

## `problems.csv`

`data/tasks/problems.csv` mirrors the BioMysteryBench-style one-row-per-problem
index:

- `id`
- `task_type`
- `question`
- `answer_rubric`
- `allowed_domains`
- `human_solvable`
- `data_path`

Recommended optional columns:

- `capability_targets`
- `evidence_layers`
- `difficulty`
- `label_status`
- `scoring_mode`

## Agent Answer Contract

Agents should write final answers to `answer.json`. Each answer should be valid
JSON so the grader can parse it deterministically. Free text is allowed inside
JSON fields such as `rationale`, `mechanism`, `uncertainty`, and
`experiment_plan`.

For `candidate_prioritization` tasks:

```json
{
  "ranking": [
    {
      "peptide_id": "PEP-...",
      "rank": 1,
      "confidence": 0.72,
      "rationale": "High potency and strong efficacy across comparable assays.",
      "main_risk": "No stability or in vivo outcome data in this task."
    }
  ],
  "top_3": ["PEP-...", "PEP-...", "PEP-..."]
}
```

For wet-lab-pending candidate generation tasks, the same answer shape can be
used before a gold ranking exists. Set `label_status` and `scoring_mode` to
`wet_lab_validation_pending` in `task.yaml`, and use an answer YAML stub that
defines `outcome_definition` but intentionally omits `gold_ranking`. The grader
will parse and retain the proposed recommendations while returning
`"scored": false` and `"score": null`.

```yaml
id: cb-next-best-nps-001
task_type: candidate_prioritization
label_status: wet_lab_validation_pending
scoring_mode: wet_lab_validation_pending
top_k: 3
outcome_definition: Expert-selected wet-lab validation outcome for the proposed
  top 3 candidates or modifications.
```

For `hit_prediction` tasks:

```json
{
  "prediction": "active",
  "confidence": 0.68,
  "effect_direction": "decreases inactivity",
  "rationale": "Potency and efficacy are strong, but exposure is uncertain.",
  "main_risk": "Dose may not maintain sufficient target coverage."
}
```

For `next_experiment` tasks:

```json
{
  "selected_option": "EXP-003",
  "ranked_options": ["EXP-003", "EXP-001", "EXP-004"],
  "rationale": "This separates exposure failure from receptor-specific biology.",
  "decision_gate": "Advance only if target-window exposure and endpoint rescue both replicate."
}
```

For `multitarget_activity` and `program_lead_selection` tasks, return a flat
JSON object whose keys match the `gold` field names in the answer YAML, with
exact-match string values:

```json
{
  "receptor_1_activity": "agonist",
  "receptor_2_activity": "inactive",
  "primary_lead": "PEP-..."
}
```

If an agent does not write `answer.json`, the runner falls back to stdout and the
grader tries to parse peptide IDs from that text.

## Final Ground Truth Extension

Mouse outcome data are populated locally with:

```text
uv run capablebench extract-invivo "<path-to-mouse-data-directory>"
```

That creates processed tables such as:

```text
data/processed/invivo_measurements_long.csv
data/processed/invivo_studies_inventory.csv
data/processed/invivo_json_exports_raw_measurements_long.csv
data/processed/invivo_json_exports_analysis_bars.csv
data/processed/invivo_json_exports_analysis_significance.csv
```

Use answer YAML files with labels derived from linked outcomes:

```yaml
id: prioritization-oxn-042
task_type: candidate_prioritization
label_status: experimental_ground_truth
top_k: 3
gold_ranking:
  - PEP-...
  - PEP-...
gold_top_3:
  - PEP-...
  - PEP-...
  - PEP-...
outcome_definition: study_normalized_inactivity_effect_size
```

For `hit_prediction` tasks:

```yaml
id: hit-oxn-001
task_type: hit_prediction
label_status: experimental_ground_truth
gold_label: active
accepted_labels:
  - active
  - responder
outcome_definition: prespecified_window_effect_direction
```

For `next_experiment` tasks:

```yaml
id: experiment-oxn-001
task_type: next_experiment
label_status: expert_utility_ranking
gold_top:
  - exp_003
gold_ranking:
  - exp_003
  - exp_001
  - exp_004
```

For `multitarget_activity` and `program_lead_selection` tasks:

```yaml
id: multitarget-mch-nps-001
task_type: multitarget_activity
label_status: experimental_ground_truth
gold:
  mch_activity: agonist
  nps_activity: inactive
```

Keyword-matching, rubric, and other subjective scoring modes are not permitted
in this benchmark. Every task must have objective ground truth backed by
measured experimental data.

## Build And Validate A Pilot

Generate task bundles from processed private tables:

```bash
uv run capablebench curate-pilot --clean
uv run capablebench validate
```
