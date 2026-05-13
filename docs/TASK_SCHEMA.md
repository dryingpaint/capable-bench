# Task Schema

Each task is a directory:

```text
data/tasks/<task_id>/
  task.yaml
  prompt.md
  candidates.csv
  ... other task data files ...
```

The hidden answer/rubric lives separately:

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

For `failure_diagnosis`, `mechanistic_hypothesis`, and `foundation_model_triage`
tasks:

```json
{
  "primary_hypothesis": "The in vivo failure is most consistent with exposure-limited target engagement.",
  "supporting_evidence": [
    "Comparable in vitro potency across analogs",
    "Reduced effect in the late behavioral window"
  ],
  "alternative_hypotheses": [
    "Assay-specific partial agonism",
    "Species-specific receptor coupling"
  ],
  "falsifying_experiment": "Measure free plasma and tissue exposure across the endpoint window with a positive-control arm.",
  "uncertainty": "No direct receptor occupancy data are visible in this task."
}
```

For `experiment_plan` and `drug_discovery_program` tasks:

```json
{
  "recommendation": "Advance PEP-... as the lead backup candidate and run a two-arm exposure-response study.",
  "mechanistic_model": "The candidate likely preserves receptor efficacy while improving developability.",
  "experiments": [
    {
      "id": "EXP-001",
      "purpose": "Confirm target-window exposure",
      "controls": ["vehicle", "positive_control"],
      "decision_gate": "Stop if free exposure is below the biochemical EC80 for most of the window."
    }
  ],
  "risks": ["selectivity", "short half-life", "assay transferability"],
  "next_design_cycle": "Prioritize substitutions predicted to improve stability without reducing potency."
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

For rubric-scored tasks:

```yaml
id: mechanism-oxn-001
task_type: mechanistic_hypothesis
label_status: expert_rubric
auto_score_cap: 0.3
rubric:
  required_concepts:
    - id: exposure_window
      weight: 2
      any_terms:
        - exposure window
        - target coverage
        - free plasma
    - id: assay_artifact
      weight: 1
      any_terms:
        - assay artifact
        - batch effect
        - plate effect
  forbidden_concepts:
    - id: unsupported_clinical_claim
      any_terms:
        - proven safe in humans
        - clinically validated
```

The rubric grader is intentionally lightweight. It is useful for automated
smoke checks. Expert-rubric tasks should set `auto_score_cap` so keyword
coverage cannot by itself saturate the benchmark; final reporting for creative
scientific tasks should include expert review against the hidden rubric.

## Build And Validate A Pilot

Generate task bundles from processed private tables:

```bash
uv run capablebench curate-pilot --clean
uv run capablebench validate
```

