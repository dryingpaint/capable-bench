from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from .io import ensure_dir, write_json
from .tasks import list_tasks


def run_task_modal(
    task_id: str,
    tasks_dir: Path,
    answers_dir: Path,
    runs_dir: Path,
    agent_command: str,
    *,
    timeout_seconds: int = 1800,
) -> dict[str, Any]:
    try:
        import modal
    except ImportError as exc:
        raise RuntimeError(
            "Modal is not installed. Install project dependencies with `uv sync` or `pip install -e .`."
        ) from exc

    from .modal_app import app, run_benchmark_task_remote

    task_bundle = _bundle_task(task_id, tasks_dir, answers_dir)
    local_run_dir = runs_dir / task_id / task_bundle["run_id"]
    ensure_dir(local_run_dir)
    _write_task_snapshot(task_bundle, local_run_dir)

    with modal.enable_output(), app.run():
        result = run_benchmark_task_remote.remote(
            task_bundle,
            agent_command,
            timeout_seconds,
        )

    _write_artifacts(result["artifacts"], local_run_dir)
    summary = {
        **result["summary"],
        "run_dir": str(local_run_dir),
        "remote_task_dir": result["summary"].get("remote_task_dir"),
    }
    write_json(local_run_dir / "run_summary.json", summary)
    return summary


def run_suite_modal(
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

    try:
        import modal
    except ImportError as exc:
        raise RuntimeError(
            "Modal is not installed. Install project dependencies with `uv sync` or `pip install -e .`."
        ) from exc

    from .modal_app import app, run_benchmark_task_remote

    bundles = [_bundle_task(task["id"], tasks_dir, answers_dir) for task in tasks]
    local_run_dirs = {
        bundle["run_id"]: runs_dir / bundle["task_id"] / bundle["run_id"] for bundle in bundles
    }
    for bundle in bundles:
        local_run_dir = local_run_dirs[bundle["run_id"]]
        ensure_dir(local_run_dir)
        _write_task_snapshot(bundle, local_run_dir)

    call_args = [(bundle, agent_command, timeout_seconds) for bundle in bundles]
    with modal.enable_output(), app.run():
        remote_results = list(run_benchmark_task_remote.starmap(call_args))

    results = []
    for result in remote_results:
        run_id = result["summary"]["run_id"]
        local_run_dir = local_run_dirs[run_id]
        _write_artifacts(result["artifacts"], local_run_dir)
        summary = {
            **result["summary"],
            "run_dir": str(local_run_dir),
            "remote_task_dir": result["summary"].get("remote_task_dir"),
        }
        write_json(local_run_dir / "run_summary.json", summary)
        results.append(summary)

    summary = _suite_summary(results)
    ensure_dir(runs_dir)
    write_json(runs_dir / "latest_modal_suite_summary.json", summary)
    return summary


def _bundle_task(task_id: str, tasks_dir: Path, answers_dir: Path) -> dict[str, Any]:
    task_dir = tasks_dir / task_id
    if not task_dir.exists():
        raise FileNotFoundError(task_dir)

    task_files = {}
    for path in sorted(task_dir.rglob("*")):
        if path.is_file():
            task_files[str(path.relative_to(task_dir))] = path.read_bytes()

    gold_path = answers_dir / f"{task_id}.yaml"
    return {
        "task_id": task_id,
        "run_id": time.strftime("%Y%m%d-%H%M%S") + f"-{uuid.uuid4().hex[:8]}-modal",
        "task_files": task_files,
        "gold_answer": gold_path.read_bytes() if gold_path.exists() else None,
    }


def _write_task_snapshot(task_bundle: dict[str, Any], run_dir: Path) -> None:
    for rel_path, content in task_bundle["task_files"].items():
        path = run_dir / rel_path
        ensure_dir(path.parent)
        path.write_bytes(content)


def _write_artifacts(artifacts: dict[str, bytes], run_dir: Path) -> None:
    for rel_path, content in artifacts.items():
        path = run_dir / rel_path
        ensure_dir(path.parent)
        path.write_bytes(content)


def _suite_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    grades = [r.get("grade") for r in results if r.get("grade")]
    return {
        "executor": "modal",
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


def _mean(values: Any) -> float | None:
    values = list(values)
    if not values:
        return None
    return round(sum(float(v) for v in values) / len(values), 4)
