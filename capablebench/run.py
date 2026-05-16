from __future__ import annotations

import json
import os
import selectors
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from .grade import grade_attempt
from .io import ensure_dir, read_yaml, write_json


def render_agent_command(
    agent_command: str,
    *,
    task_dir: Path,
    prompt_file: Path,
    answer_file: Path,
    task_id: str,
) -> str:
    replacements = {
        "{task_dir}": shlex.quote(str(task_dir)),
        "{prompt_file}": shlex.quote(str(prompt_file)),
        "{answer_file}": shlex.quote(str(answer_file)),
        "{task_id}": shlex.quote(task_id),
    }
    rendered_command = agent_command
    for placeholder, value in replacements.items():
        rendered_command = rendered_command.replace(placeholder, value)
    return rendered_command


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
    trace_file = run_dir / "agent_trace.txt"

    rendered_command = render_agent_command(
        agent_command,
        task_dir=run_dir,
        prompt_file=prompt_file,
        answer_file=answer_file,
        task_id=task_id,
    )

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
    proc = subprocess.Popen(
        rendered_command,
        cwd=run_dir,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    stdout, stderr, raw_trace = _capture_process(proc, timeout_seconds)
    duration = time.time() - started
    stdout_file.write_text(stdout, encoding="utf-8")
    stderr_file.write_text(stderr, encoding="utf-8")
    rendered_trace = _render_agent_trace(stdout, stderr)
    trace_file.write_text(rendered_trace or raw_trace, encoding="utf-8")

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
        "trace_file": str(trace_file),
        "grade": grade,
    }
    write_json(run_dir / "run_summary.json", summary)
    return summary


def _capture_process(proc: subprocess.Popen[str], timeout_seconds: int) -> tuple[str, str, str]:
    selector = selectors.DefaultSelector()
    if proc.stdout is not None:
        selector.register(proc.stdout, selectors.EVENT_READ, "stdout")
    if proc.stderr is not None:
        selector.register(proc.stderr, selectors.EVENT_READ, "stderr")

    started = time.time()
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    trace_parts: list[str] = []

    while selector.get_map():
        remaining = timeout_seconds - (time.time() - started)
        if remaining <= 0:
            proc.kill()
            stdout_tail, stderr_tail = proc.communicate()
            if stdout_tail:
                stdout_parts.append(stdout_tail)
                trace_parts.append(_format_trace_chunk("stdout", stdout_tail))
            if stderr_tail:
                stderr_parts.append(stderr_tail)
                trace_parts.append(_format_trace_chunk("stderr", stderr_tail))
            trace_parts.append(
                _format_trace_chunk("system", f"timeout after {timeout_seconds}s; process killed\n")
            )
            return "".join(stdout_parts), "".join(stderr_parts), "".join(trace_parts)

        events = selector.select(timeout=min(0.2, remaining))
        if not events and proc.poll() is not None:
            for fileobj in list(selector.get_map().values()):
                selector.unregister(fileobj.fileobj)
            break

        for key, _ in events:
            stream_name = key.data
            chunk = key.fileobj.readline()
            if chunk:
                if stream_name == "stdout":
                    stdout_parts.append(chunk)
                else:
                    stderr_parts.append(chunk)
                trace_parts.append(_format_trace_chunk(stream_name, chunk))
            else:
                selector.unregister(key.fileobj)

    stdout_tail, stderr_tail = proc.communicate()
    if stdout_tail:
        stdout_parts.append(stdout_tail)
        trace_parts.append(_format_trace_chunk("stdout", stdout_tail))
    if stderr_tail:
        stderr_parts.append(stderr_tail)
        trace_parts.append(_format_trace_chunk("stderr", stderr_tail))
    return "".join(stdout_parts), "".join(stderr_parts), "".join(trace_parts)


def _format_trace_chunk(stream_name: str, chunk: str) -> str:
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    return "".join(f"[{timestamp}] {stream_name}> {line}" for line in chunk.splitlines(True))


_TRACE_FIELD_LIMIT = 100_000


def _trunc(value: Any, limit: int = _TRACE_FIELD_LIMIT) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    if len(text) > limit:
        return text[:limit] + f"… (+{len(text) - limit} chars)"
    return text


def _render_agent_trace(stdout: str, stderr: str) -> str:
    """Parse JSONL events from claude `--output-format stream-json` or codex `--json`
    into a human-readable trace. Returns empty string when no JSON events are found,
    so callers can fall back to the raw timestamped capture."""
    events_seen = 0
    lines: list[str] = []
    for source in (stdout, stderr):
        for raw in source.splitlines():
            stripped = raw.strip()
            if not stripped or not stripped.startswith("{"):
                continue
            try:
                event = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            rendered = _format_agent_event(event)
            if rendered:
                lines.append(rendered)
                events_seen += 1
    if not events_seen:
        return ""
    return "\n".join(lines)


def _format_agent_event(event: dict[str, Any]) -> str:
    if not isinstance(event, dict):
        return ""
    et = event.get("type")
    # Claude `-p --output-format stream-json --verbose` schema
    if et == "system":
        sub = event.get("subtype") or ""
        model = event.get("model") or ""
        tag = f"system:{sub}" if sub else "system"
        return f"[{tag}] model={model}".rstrip(" =model")
    if et == "assistant":
        msg = event.get("message") or {}
        out: list[str] = []
        for block in msg.get("content", []) or []:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == "text":
                out.append(f"[assistant] {_trunc(block.get('text', ''))}")
            elif btype == "tool_use":
                name = block.get("name", "?")
                out.append(f"[tool_call] {name}({_trunc(block.get('input') or {})})")
        return "\n".join(out)
    if et == "user":
        msg = event.get("message") or {}
        content = msg.get("content")
        if not isinstance(content, list):
            return ""
        out = []
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            inner = block.get("content")
            if isinstance(inner, list):
                inner = "".join(
                    (c.get("text") or "") if isinstance(c, dict) else str(c) for c in inner
                )
            out.append(f"[tool_result] {_trunc(inner)}")
        return "\n".join(out)
    if et == "result":
        sub = event.get("subtype") or ""
        cost = event.get("total_cost_usd")
        dur = event.get("duration_ms")
        usage = event.get("usage") or {}
        toks = f"in={usage.get('input_tokens', '?')} out={usage.get('output_tokens', '?')}"
        return f"[result:{sub}] cost=${cost} duration={dur}ms tokens({toks})"

    # Codex `exec --json` schema: top-level `type` is one of
    # thread.started, turn.started, item.started, item.completed, turn.completed.
    # We collapse item lifecycle to one event per completed item to keep traces concise.
    if et == "thread.started":
        return f"[codex] thread_started id={event.get('thread_id', '')}"
    if et == "turn.started":
        return "[codex] turn_started"
    if et == "turn.completed":
        usage = event.get("usage") or {}
        return (
            f"[codex] turn_completed tokens(in={usage.get('input_tokens', '?')} "
            f"out={usage.get('output_tokens', '?')} "
            f"reasoning={usage.get('reasoning_output_tokens', '?')})"
        )
    if et == "item.completed":
        item = event.get("item") or {}
        itype = item.get("type")
        if itype == "agent_message":
            return f"[assistant] {_trunc(item.get('text') or item.get('message') or '')}"
        if itype == "reasoning":
            return f"[reasoning] {_trunc(item.get('text') or '')}"
        if itype == "command_execution":
            cmd = item.get("command")
            if isinstance(cmd, list):
                cmd = " ".join(cmd)
            out = item.get("aggregated_output") or item.get("output") or ""
            exit_code = item.get("exit_code")
            return (
                f"[exec] {_trunc(cmd or '')}\n"
                f"        ↳ exit={exit_code} {_trunc(out)}"
            )
        if itype == "file_change":
            changes = item.get("changes") or []
            summary = ", ".join(
                f"{c.get('kind', '?')} {c.get('path', '?')}" for c in changes if isinstance(c, dict)
            )
            return f"[file_change] {summary}"
        if itype:
            extras = {k: v for k, v in item.items() if k != "type"}
            return f"[{itype}] {_trunc(extras)}"
    # We deliberately drop `item.started` to avoid duplicating each command.
    if et == "item.started":
        return ""
    if et == "error":
        return f"[error] {_trunc(event.get('message') or event)}"
    return ""
