from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .grade import grade_attempt
from .io import ensure_dir
from .tasks import list_tasks


def refresh_dashboard_cache(runs_dir: Path, force: bool = False) -> dict[str, Any]:
    """Refresh cached grades in run summaries to ensure data consistency."""
    refreshed_count = 0
    error_count = 0

    print("Scanning for run summaries to refresh...")

    for summary_path in sorted(runs_dir.glob("*/*/run_summary.json")):
        try:
            summary = _read_json_optional(summary_path)
            if not summary:
                continue

            needs_refresh = force
            if not needs_refresh and "grade" not in summary:
                needs_refresh = True
            elif not needs_refresh and not isinstance(summary.get("grade"), dict):
                needs_refresh = True

            if needs_refresh:
                task_id = summary.get("task_id") or summary_path.parents[1].name
                run_dir = summary_path.parent
                answer_source = Path(summary.get("answer_source", ""))
                if not answer_source.is_absolute():
                    answer_source = run_dir / answer_source

                answers_dir = runs_dir.parent / "data" / "answers"
                gold_path = answers_dir / f"{task_id}.yaml"

                if answer_source.exists() and gold_path.exists():
                    try:
                        grade = grade_attempt(answer_source, gold_path)
                        summary["grade"] = grade
                        _write_json_safe(summary_path, summary)
                        refreshed_count += 1
                        print(f"Refreshed grade for {task_id}")
                    except Exception as exc:
                        print(f"Failed to refresh grade for {task_id}: {exc}")
                        error_count += 1
                else:
                    print(f"Cannot refresh {task_id}: missing answer or gold file")
                    error_count += 1
        except Exception as exc:
            print(f"Error processing {summary_path}: {exc}")
            error_count += 1

    return {
        "refreshed_count": refreshed_count,
        "error_count": error_count,
        "message": f"Refreshed {refreshed_count} cached grades, {error_count} errors",
    }


def validate_dashboard_data(tasks_dir: Path, answers_dir: Path, runs_dir: Path) -> dict[str, Any]:
    """Validate dashboard data integrity and report any issues."""
    issues = []
    stats = {
        "tasks_found": 0,
        "runs_found": 0,
        "graded_runs": 0,
        "ungraded_runs": 0,
        "corrupted_summaries": 0,
    }

    try:
        tasks = list_tasks(tasks_dir)
        stats["tasks_found"] = len(tasks)

        for task in tasks:
            task_dir = tasks_dir / task["id"]
            if not (task_dir / "prompt.md").exists():
                issues.append(f"Missing prompt.md for task {task['id']}")

            gold_path = answers_dir / f"{task['id']}.yaml"
            if not gold_path.exists():
                issues.append(f"Missing gold answer for task {task['id']}")
    except Exception as exc:
        issues.append(f"Failed to load tasks: {exc}")

    if runs_dir.exists():
        for summary_path in runs_dir.glob("*/*/run_summary.json"):
            try:
                summary = _read_json_optional(summary_path)
                if summary:
                    stats["runs_found"] += 1
                    if "grade" in summary and isinstance(summary["grade"], dict):
                        stats["graded_runs"] += 1
                    else:
                        stats["ungraded_runs"] += 1
                else:
                    stats["corrupted_summaries"] += 1
                    issues.append(f"Corrupted summary: {summary_path}")
            except Exception as exc:
                stats["corrupted_summaries"] += 1
                issues.append(f"Error reading {summary_path}: {exc}")

    return {
        "stats": stats,
        "issues": issues,
        "status": "healthy" if not issues else "has_issues",
    }


def _read_json_optional(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"Warning: Failed to read JSON file {path}: {exc}")
        return None


def _write_json_safe(path: Path, data: dict[str, Any]) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        ensure_dir(path.parent)
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=False)
            f.write("\n")
        temp_path.replace(path)
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink()
        print(f"Warning: Failed to write {path}: {exc}")
        raise
