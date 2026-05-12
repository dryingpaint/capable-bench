from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from .grade import grade_attempt
from .io import ensure_dir, read_yaml, write_json


def _copy_task(task_dir: Path, run_dir: Path) -> None:
    ensure_dir(run_dir)
    for item in task_dir.iterdir():
        dest = run_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)


def run_task(
    task_id: str,
    tasks_dir: Path,
    answers_dir: Path,
    runs_dir: Path,
    agent_command: str,
    *,
    timeout_seconds: int = 1800,
) -> dict[str, Any]:
    task_dir = tasks_dir / task_id
    if not task_dir.exists():
        raise FileNotFoundError(task_dir)

    metadata = read_yaml(task_dir / "task.yaml")
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    run_dir = runs_dir / task_id / timestamp
    _copy_task(task_dir, run_dir)

    prompt_file = run_dir / "prompt.md"
    answer_file = run_dir / metadata.get("answer_file", "answer.json")
    stdout_file = run_dir / "stdout.txt"
    stderr_file = run_dir / "stderr.txt"

    replacements = {
        "{task_dir}": shlex.quote(str(run_dir)),
        "{prompt_file}": shlex.quote(str(prompt_file)),
        "{answer_file}": shlex.quote(str(answer_file)),
        "{task_id}": shlex.quote(task_id),
    }
    rendered_command = agent_command
    for placeholder, value in replacements.items():
        rendered_command = rendered_command.replace(placeholder, value)

    env = os.environ.copy()
    env.update(
        {
            "CAPABLE_BENCH_TASK_ID": task_id,
            "CAPABLE_BENCH_TASK_DIR": str(run_dir),
            "CAPABLE_BENCH_PROMPT_FILE": str(prompt_file),
            "CAPABLE_BENCH_ANSWER_FILE": str(answer_file),
        }
    )

    started = time.time()
    proc = subprocess.run(
        rendered_command,
        cwd=run_dir,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_seconds,
        env=env,
    )
    duration = time.time() - started
    stdout_file.write_text(proc.stdout, encoding="utf-8")
    stderr_file.write_text(proc.stderr, encoding="utf-8")

    answer_source = answer_file
    if not answer_file.exists():
        answer_source = stdout_file

    gold_path = answers_dir / f"{task_id}.yaml"
    grade_path = run_dir / "grade.json"
    grade = None
    if gold_path.exists():
        grade = grade_attempt(answer_source, gold_path, grade_path)

    summary = {
        "task_id": task_id,
        "run_dir": str(run_dir),
        "command": rendered_command,
        "returncode": proc.returncode,
        "duration_seconds": round(duration, 3),
        "answer_source": str(answer_source),
        "stdout_file": str(stdout_file),
        "stderr_file": str(stderr_file),
        "grade": grade,
    }
    write_json(run_dir / "run_summary.json", summary)
    return summary
