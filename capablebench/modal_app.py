from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any

import modal

from .grade import grade_attempt
from .io import ensure_dir, read_yaml, write_json
from .run import render_agent_command


APP_NAME = "capable-bench"
REMOTE_ROOT = Path("/tmp/capable-bench-task")


image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("curl", "git", "nodejs", "npm", "ripgrep")
    .pip_install("pyyaml>=6.0")
    .run_commands("npm install -g @openai/codex @anthropic-ai/claude-code")
    .add_local_python_source("capablebench")
)

app = modal.App(APP_NAME)
secrets = [
    modal.Secret.from_dict(
        {
            "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
            "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY"),
        }
    )
]


@app.function(
    image=image,
    timeout=3600,
    secrets=secrets,
)
def run_benchmark_task_remote(
    task_bundle: dict[str, Any],
    agent_command: str,
    timeout_seconds: int = 1800,
) -> dict[str, Any]:
    task_id = task_bundle["task_id"]
    run_id = task_bundle["run_id"]
    task_dir = REMOTE_ROOT / task_id / run_id
    ensure_dir(task_dir)

    for rel_path, content in task_bundle["task_files"].items():
        path = task_dir / rel_path
        ensure_dir(path.parent)
        path.write_bytes(content)

    gold_path = None
    if task_bundle.get("gold_answer") is not None:
        gold_path = task_dir / "_gold_answer.yaml"
        gold_path.write_bytes(task_bundle["gold_answer"])

    metadata = read_yaml(task_dir / "task.yaml")
    prompt_file = task_dir / "prompt.md"
    answer_file = task_dir / metadata.get("answer_file", "answer.json")
    stdout_file = task_dir / "stdout.txt"
    stderr_file = task_dir / "stderr.txt"

    rendered_command = render_agent_command(
        agent_command,
        task_dir=task_dir,
        prompt_file=prompt_file,
        answer_file=answer_file,
        task_id=task_id,
    )

    env = os.environ.copy()
    env.update(
        {
            "CAPABLE_BENCH_TASK_ID": task_id,
            "CAPABLE_BENCH_TASK_DIR": str(task_dir),
            "CAPABLE_BENCH_PROMPT_FILE": str(prompt_file),
            "CAPABLE_BENCH_ANSWER_FILE": str(answer_file),
        }
    )

    started = time.time()
    proc = subprocess.run(
        rendered_command,
        cwd=task_dir,
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

    answer_source = answer_file if answer_file.exists() else stdout_file
    grade = None
    grade_path = task_dir / "grade.json"
    if gold_path is not None:
        grade = grade_attempt(answer_source, gold_path, grade_path)

    summary = {
        "task_id": task_id,
        "run_id": run_id,
        "remote_task_dir": str(task_dir),
        "command": rendered_command,
        "returncode": proc.returncode,
        "duration_seconds": round(duration, 3),
        "answer_source": str(answer_source),
        "stdout_file": str(stdout_file),
        "stderr_file": str(stderr_file),
        "grade": grade,
        "executor": "modal",
    }
    write_json(task_dir / "run_summary.json", summary)

    artifacts = {}
    for path in sorted(task_dir.rglob("*")):
        if path.is_file() and path.name != "_gold_answer.yaml":
            artifacts[str(path.relative_to(task_dir))] = path.read_bytes()

    return {
        "summary": summary,
        "artifacts": artifacts,
    }
