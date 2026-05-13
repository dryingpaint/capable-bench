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
# Named Modal secrets - create with:
#   modal secret create codex-auth OPENAI_API_KEY=...
#   modal secret create claude-auth CLAUDE_CODE_OAUTH_TOKEN=...
# The CLIs don't read local env vars directly in the container: codex reads
# OPENAI_API_KEY from env when auth_mode=apikey; Claude Code 2.x reads
# CLAUDE_CODE_OAUTH_TOKEN (the OAuth access token from a Claude subscription)
# in headless mode because keychain isn't available in the container.
secrets = [
    modal.Secret.from_name("codex-auth"),
    modal.Secret.from_name("claude-auth"),
]


# Cap parallel containers so we don't fan out faster than the upstream
# LLM rate limits. codex on gpt-5.5 burns ~70-100K tokens per task and
# the OpenAI org TPM cap is 500K/min, so >=5 parallel runs cascade-fail
# with "stream disconnected ... rate limit reached". 3 keeps peak usage
# at ~300K TPM with headroom. Override per-run with --max-containers (CLI)
# or MODAL_MAX_CONTAINERS (env). Read at module import; if a fresh value
# is needed, set the env var BEFORE importing capablebench.modal_app /
# capablebench.modal_runner.
_MAX_CONTAINERS = int(os.environ.get("MODAL_MAX_CONTAINERS", "3"))


@app.function(
    image=image,
    timeout=3600,
    secrets=secrets,
    max_containers=_MAX_CONTAINERS,
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

    # The gold answer is INTENTIONALLY not bundled into the container.
    # Grading happens in the orchestrator after artifacts return. This
    # prevents the agent from discovering the gold via filesystem reads,
    # even with bypassPermissions / dangerously-bypass-approvals-and-sandbox.
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
            # Modal containers run as root; tell claude-code this is a sandbox
            # so it lets us use --permission-mode bypassPermissions there.
            "IS_SANDBOX": "1",
            "CLAUDE_CODE_DANGEROUSLY_ALLOW_ROOT": "1",
        }
    )

    # The codex CLI reads ~/.codex/auth.json rather than the OPENAI_API_KEY
    # env var alone. Materialize the auth file from the secret so codex can
    # authenticate inside the fresh container.
    openai_key = env.get("OPENAI_API_KEY", "")
    if openai_key:
        import json as _json
        codex_dir = Path.home() / ".codex"
        codex_dir.mkdir(parents=True, exist_ok=True)
        (codex_dir / "auth.json").write_text(
            _json.dumps({"auth_mode": "apikey", "OPENAI_API_KEY": openai_key})
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
    # Grading is deferred to the orchestrator (no gold inside the container).
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
