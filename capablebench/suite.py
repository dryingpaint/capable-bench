from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .io import ensure_dir, write_json
from .run import run_task
from .tasks import list_tasks


def run_suite(
    tasks_dir: Path,
    answers_dir: Path,
    runs_dir: Path,
    agent_command: str,
    *,
    limit: int | None = None,
    timeout_seconds: int = 1800,
) -> dict[str, Any]:
    tasks = list_tasks(tasks_dir)
    if limit is not None:
        tasks = tasks[:limit]

    results = []
    for task in tasks:
        results.append(
            run_task(
                task["id"],
                tasks_dir,
                answers_dir,
                runs_dir,
                agent_command,
                timeout_seconds=timeout_seconds,
            )
        )

    grades = [r.get("grade") for r in results if r.get("grade")]
    summary = {
        "tasks_attempted": len(results),
        "tasks_graded": len(grades),
        "mean_precision_at_k": _mean(g.get("precision_at_k", 0.0) for g in grades),
        "mean_ndcg_at_k": _mean(g.get("ndcg_at_k", 0.0) for g in grades),
        "top1_exact_rate": _mean(1.0 if g.get("top1_exact") else 0.0 for g in grades),
        "top1_in_gold_top_k_rate": _mean(
            1.0 if g.get("top1_in_gold_top_k") else 0.0 for g in grades
        ),
        "runs": results,
    }
    ensure_dir(runs_dir)
    write_json(runs_dir / "latest_suite_summary.json", summary)
    return summary


def summarize_runs(runs_dir: Path) -> dict[str, Any]:
    grade_paths = sorted(runs_dir.glob("*/*/grade.json"))
    grades = []
    for path in grade_paths:
        with path.open("r", encoding="utf-8") as f:
            grades.append(json.load(f))
    return {
        "grades_found": len(grades),
        "mean_precision_at_k": _mean(g.get("precision_at_k", 0.0) for g in grades),
        "mean_ndcg_at_k": _mean(g.get("ndcg_at_k", 0.0) for g in grades),
        "top1_exact_rate": _mean(1.0 if g.get("top1_exact") else 0.0 for g in grades),
        "top1_in_gold_top_k_rate": _mean(
            1.0 if g.get("top1_in_gold_top_k") else 0.0 for g in grades
        ),
    }


def _mean(values: Any) -> float | None:
    values = list(values)
    if not values:
        return None
    return round(sum(float(v) for v in values) / len(values), 4)

