from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .io import write_json
from .tasks import list_tasks


REQUIRED_TASK_TYPES = {
    "candidate_prioritization",
    "hit_prediction",
    "next_experiment",
    "failure_diagnosis",
    "mechanistic_hypothesis",
    "structure_activity_reasoning",
    "foundation_model_triage",
    "model_disagreement_analysis",
    "drug_discovery_program",
}

REQUIRED_CAPABILITIES = {
    "mechanistic_reasoning",
    "hypothesis_generation",
    "experiment_planning",
    "translational_decision_making",
    "model_augmented_discovery",
}

REQUIRED_EVIDENCE_LAYERS = {"identity", "in_vitro", "in_vivo", "model_outputs"}


def audit_benchmark_quality(
    tasks_dir: Path,
    runs_dir: Path,
    *,
    min_tasks: int = 30,
    min_hard_fraction: float = 0.45,
    saturation_target: float = 0.60,
    out_path: Path | None = None,
) -> dict[str, Any]:
    tasks = list_tasks(tasks_dir)
    task_types = Counter(task.get("task_type", "") for task in tasks)
    difficulties = Counter(task.get("difficulty", "") for task in tasks)
    capabilities = _split_values(task.get("capability_targets", "") for task in tasks)
    evidence_layers = _split_values(task.get("evidence_layers", "") for task in tasks)
    hard_fraction = difficulties["hard"] / len(tasks) if tasks else 0.0

    checks = [
        {
            "name": "minimum_task_count",
            "passed": len(tasks) >= min_tasks,
            "details": f"{len(tasks)} tasks listed; required >= {min_tasks}",
        },
        {
            "name": "required_task_types",
            "passed": REQUIRED_TASK_TYPES.issubset(task_types),
            "details": f"missing={sorted(REQUIRED_TASK_TYPES - set(task_types))}",
        },
        {
            "name": "required_capabilities",
            "passed": REQUIRED_CAPABILITIES.issubset(capabilities),
            "details": f"missing={sorted(REQUIRED_CAPABILITIES - capabilities)}",
        },
        {
            "name": "required_evidence_layers",
            "passed": REQUIRED_EVIDENCE_LAYERS.issubset(evidence_layers),
            "details": f"missing={sorted(REQUIRED_EVIDENCE_LAYERS - evidence_layers)}",
        },
        {
            "name": "hard_task_fraction",
            "passed": hard_fraction >= min_hard_fraction,
            "details": f"{hard_fraction:.3f}; required >= {min_hard_fraction:.3f}",
        },
    ]

    latest_summary = _load_latest_summary(runs_dir)
    calibration_summary = _load_json(runs_dir / "calibration_summary.json")
    if latest_summary:
        attempted = int(latest_summary.get("tasks_attempted", 0))
        if attempted >= min_tasks:
            mean_score = latest_summary.get("mean_score")
            checks.append(
                {
                    "name": "latest_full_run_unsaturated",
                    "passed": mean_score is not None and float(mean_score) < saturation_target,
                    "details": f"mean_score={mean_score}; target < {saturation_target}",
                }
            )

    if calibration_summary:
        calibration_scores = [
            calibration_summary.get("codex_stratified", {}).get("mean_score"),
            calibration_summary.get("claude_stratified", {}).get("mean_score"),
        ]
        present_scores = [float(score) for score in calibration_scores if score is not None]
        checks.append(
            {
                "name": "recorded_calibration_unsaturated",
                "passed": bool(present_scores)
                and all(score < saturation_target for score in present_scores),
                "details": f"scores={present_scores}; target < {saturation_target}",
            }
        )

    result = {
        "tasks_dir": str(tasks_dir),
        "runs_dir": str(runs_dir),
        "tasks": len(tasks),
        "task_types": dict(sorted(task_types.items())),
        "difficulties": dict(sorted(difficulties.items())),
        "hard_fraction": round(hard_fraction, 4),
        "capabilities": sorted(capabilities),
        "evidence_layers": sorted(evidence_layers),
        "latest_suite_summary": latest_summary,
        "calibration_summary": calibration_summary,
        "checks": checks,
        "passed": all(check["passed"] for check in checks),
    }
    if out_path is not None:
        write_json(out_path, result)
    return result


def _split_values(values: Any) -> set[str]:
    result = set()
    for value in values:
        for item in str(value).split(";"):
            item = item.strip()
            if item:
                result.add(item)
    return result


def _load_latest_summary(runs_dir: Path) -> dict[str, Any] | None:
    return _load_json(runs_dir / "latest_suite_summary.json")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
