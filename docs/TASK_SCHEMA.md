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

## Agent Answer Contract

Agents should write final answers to `answer.json`. For prioritization tasks:

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
