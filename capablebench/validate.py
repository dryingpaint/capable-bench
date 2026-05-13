from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_yaml, write_json
from .tasks import list_tasks


REQUIRED_TASK_FILES = {"task.yaml", "prompt.md"}


def validate_benchmark(
    tasks_dir: Path,
    answers_dir: Path,
    *,
    out_path: Path | None = None,
) -> dict[str, Any]:
    problems = list_tasks(tasks_dir)
    issues = []
    task_ids = set()

    if not (tasks_dir / "problems.csv").exists():
        issues.append({"severity": "error", "message": "Missing data/tasks/problems.csv"})

    for problem in problems:
        task_id = problem.get("id", "")
        task_ids.add(task_id)
        task_dir = tasks_dir / task_id
        if not task_dir.exists():
            issues.append({"task_id": task_id, "severity": "error", "message": "Task directory missing"})
            continue
        for filename in REQUIRED_TASK_FILES:
            if not (task_dir / filename).exists():
                issues.append(
                    {"task_id": task_id, "severity": "error", "message": f"Missing {filename}"}
                )
        task_yaml_path = task_dir / "task.yaml"
        if task_yaml_path.exists():
            metadata = read_yaml(task_yaml_path)
            for data_file in metadata.get("data_files", []):
                if not (task_dir / data_file).exists():
                    issues.append(
                        {
                            "task_id": task_id,
                            "severity": "error",
                            "message": f"Missing declared data file {data_file}",
                        }
                    )
            if metadata.get("id") != task_id:
                issues.append(
                    {
                        "task_id": task_id,
                        "severity": "error",
                        "message": "task.yaml id does not match problems.csv id",
                    }
                )
        answer_path = answers_dir / f"{task_id}.yaml"
        if not answer_path.exists():
            issues.append({"task_id": task_id, "severity": "error", "message": "Missing answer YAML"})
        else:
            _validate_answer(task_id, read_yaml(answer_path), issues)

    for answer_path in answers_dir.glob("*.yaml"):
        if answer_path.stem not in task_ids:
            issues.append(
                {
                    "task_id": answer_path.stem,
                    "severity": "warning",
                    "message": "Answer YAML has no matching problems.csv row",
                }
            )

    result = {
        "tasks_dir": str(tasks_dir),
        "answers_dir": str(answers_dir),
        "tasks_listed": len(problems),
        "issues": issues,
        "valid": not any(issue["severity"] == "error" for issue in issues),
    }
    if out_path is not None:
        write_json(out_path, result)
    return result


def _validate_answer(task_id: str, answer: dict[str, Any], issues: list[dict[str, str]]) -> None:
    task_type = answer.get("task_type")
    label_status = answer.get("label_status")
    scoring_mode = answer.get("scoring_mode")
    if answer.get("id") != task_id:
        issues.append(
            {
                "task_id": task_id,
                "severity": "error",
                "message": "answer YAML id does not match problems.csv id",
            }
        )
    if label_status in {"wet_lab_validation_pending", "wet_lab_pending"} or scoring_mode in {
        "wet_lab_validation_pending",
        "pending_wet_lab_validation",
        "unscored_pending_validation",
    }:
        if not answer.get("outcome_definition"):
            issues.append(
                {
                    "task_id": task_id,
                    "severity": "error",
                    "message": "Wet-lab-pending task is missing outcome_definition",
                }
            )
        return
    if task_type == "candidate_prioritization":
        if not answer.get("gold_ranking"):
            issues.append(
                {"task_id": task_id, "severity": "error", "message": "Missing gold_ranking"}
            )
    elif task_type == "hit_prediction":
        if not answer.get("gold_label"):
            issues.append(
                {"task_id": task_id, "severity": "error", "message": "Missing gold_label"}
            )
    elif task_type == "next_experiment":
        if not answer.get("gold_top") and not answer.get("gold_ranking"):
            issues.append(
                {"task_id": task_id, "severity": "error", "message": "Missing experiment gold"}
            )
    elif task_type in {"multitarget_activity", "program_lead_selection"}:
        gold = answer.get("gold") or {}
        if not gold or not isinstance(gold, dict):
            issues.append(
                {"task_id": task_id, "severity": "error", "message": f"Missing gold dict for {task_type}"}
            )
    else:
        issues.append(
            {
                "task_id": task_id,
                "severity": "error",
                "message": f"Unknown or unsupported answer task_type={task_type!r}",
            }
        )
