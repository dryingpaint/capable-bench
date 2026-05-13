from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .grade import grade_attempt
from .io import ensure_dir, read_yaml
from .tasks import list_tasks


def build_viewer(
    tasks_dir: Path,
    answers_dir: Path,
    runs_dir: Path,
    out_path: Path,
    *,
    include_all_runs: bool = False,
) -> dict[str, Any]:
    tasks = list_tasks(tasks_dir)
    task_ids = {task["id"] for task in tasks}
    runs = [run for run in _collect_runs(runs_dir, answers_dir) if run["task_id"] in task_ids]
    latest_by_task_model = _latest_by_task_model(runs)
    models = sorted({run["model"] for run in runs})
    task_rows = []
    for task in tasks:
        task_id = task["id"]
        task_dir = tasks_dir / task_id
        task_rows.append(
            {
                **task,
                "prompt": _read_text(task_dir / "prompt.md"),
                "task_yaml": _read_yaml_optional(task_dir / "task.yaml"),
                "data_files": _data_file_summaries(task_dir),
                "latest_runs": latest_by_task_model.get(task_id, {}),
                "gold_answer": _read_yaml_optional(answers_dir / f"{task_id}.yaml"),
            }
        )

    model_summary = _model_summary(list(latest_by_task_model.values()), models)
    calibration = _read_json_optional(runs_dir / "calibration_summary.json")
    payload = {
        "tasks": task_rows,
        "models": models,
        "model_summary": model_summary,
        "runs": runs if include_all_runs else [],
        "calibration": calibration,
    }
    ensure_dir(out_path.parent)
    out_path.write_text(_render_html(payload), encoding="utf-8")
    return {
        "out_path": str(out_path),
        "tasks": len(task_rows),
        "runs_indexed": len(runs),
        "models": models,
        "model_summary": model_summary,
    }


def _collect_runs(runs_dir: Path, answers_dir: Path) -> list[dict[str, Any]]:
    runs = []
    for summary_path in sorted(runs_dir.glob("*/*/run_summary.json")):
        summary = _read_json_optional(summary_path)
        if not summary:
            continue
        task_id = summary.get("task_id") or summary_path.parents[1].name
        model = _classify_model(summary.get("command", ""))
        run_dir = summary_path.parent
        answer_source = Path(summary.get("answer_source", ""))
        if not answer_source.is_absolute():
            answer_source = run_dir / answer_source
        gold_path = answers_dir / f"{task_id}.yaml"
        grade = summary.get("grade")
        # Only re-grade if no cached grade exists, or if explicitly requested
        if not grade and answer_source.exists() and gold_path.exists():
            try:
                grade = grade_attempt(answer_source, gold_path)
            except Exception as exc:
                grade = {"parsed_answer": False, "error": str(exc)}
        stdout_file = _run_artifact_path(run_dir, summary.get("stdout_file"), "stdout.txt")
        stderr_file = _run_artifact_path(run_dir, summary.get("stderr_file"), "stderr.txt")
        trace_file = _run_artifact_path(run_dir, summary.get("trace_file"), "agent_trace.txt")
        stdout_text = _read_text(stdout_file)
        stderr_text = _read_text(stderr_file)
        trace_text = _read_text(trace_file) or _combined_trace(stdout_text, stderr_text)
        runs.append(
            {
                "task_id": task_id,
                "model": model,
                "run_id": run_dir.name,
                "run_dir": str(run_dir),
                "command": summary.get("command", ""),
                "returncode": summary.get("returncode"),
                "duration_seconds": summary.get("duration_seconds"),
                "answer_source": str(answer_source),
                "answer_text": _read_text(answer_source),
                "stdout_file": str(stdout_file),
                "stdout_text": stdout_text,
                "stderr_file": str(stderr_file),
                "stderr_text": stderr_text,
                "trace_file": str(trace_file),
                "trace_text": trace_text,
                "grade": grade,
                "score": _score(grade),
                "timestamp": run_dir.name,
            }
        )
    return runs


def _latest_by_task_model(runs: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    latest: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for run in runs:
        current = latest[run["task_id"]].get(run["model"])
        if current is None or run["timestamp"] > current["timestamp"]:
            latest[run["task_id"]][run["model"]] = run
    return latest


def _model_summary(
    task_model_runs: list[dict[str, dict[str, Any]]], models: list[str]
) -> dict[str, Any]:
    summary = {}
    for model in models:
        runs = [item[model] for item in task_model_runs if model in item]
        scores = [run["score"] for run in runs if run["score"] is not None]
        summary[model] = {
            "tasks": len(runs),
            "mean_score": round(sum(scores) / len(scores), 4) if scores else None,
            "parsed_rate": _mean_bool(
                run.get("grade", {}).get("parsed_answer") for run in runs if run.get("grade")
            ),
            "error_rate": _mean_bool(run.get("returncode") not in {0, None} for run in runs),
        }
    return summary


def _mean_bool(values: Any) -> float | None:
    values = list(values)
    if not values:
        return None
    return round(sum(1.0 if value else 0.0 for value in values) / len(values), 4)


def _score(grade: dict[str, Any] | None) -> float | None:
    if not isinstance(grade, dict):
        return None
    if "score" in grade:
        return float(grade["score"])
    if "precision_at_k" in grade:
        return float(grade["precision_at_k"])
    return None


def _classify_model(command: str) -> str:
    lower = command.lower()
    if "codex" in lower:
        return "Codex"
    if "claude" in lower:
        return "Claude"
    if "modal" in lower:
        return "Modal"
    return "Other"


def _data_file_summaries(task_dir: Path) -> list[dict[str, Any]]:
    summaries = []
    for path in sorted(task_dir.iterdir()):
        if path.name in {"prompt.md", "task.yaml"} or not path.is_file():
            continue
        summaries.append(
            {
                "name": path.name,
                "size_bytes": path.stat().st_size,
                "preview": _preview(path),
            }
        )
    return summaries


def _run_artifact_path(run_dir: Path, value: Any, default_name: str) -> Path:
    path = Path(value or default_name)
    if not path.is_absolute():
        path = run_dir / path
    return path


def _combined_trace(stdout_text: str, stderr_text: str) -> str:
    parts = []
    if stdout_text:
        parts.append("### stdout\n" + stdout_text)
    if stderr_text:
        parts.append("### stderr\n" + stderr_text)
    return "\n\n".join(parts)


def _preview(path: Path, limit: int = 8) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[:limit]
    except Exception:
        return []


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _read_yaml_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return read_yaml(path)


def _read_json_optional(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _render_html(payload: dict[str, Any]) -> str:
    payload_json = json.dumps(payload, ensure_ascii=True)
    template = _HTML_TEMPLATE.replace("__PAYLOAD_JSON__", payload_json)
    return template


_HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Capable Bench Viewer</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f4ee;
      --bg-2: #fbfaf4;
      --panel: #ffffff;
      --ink: #15171a;
      --ink-2: #2c3138;
      --muted: #6b7178;
      --line: #e4e3dc;
      --line-strong: #cfcdc4;
      --accent: #1f4f53;
      --accent-soft: rgba(31,79,83,0.10);
      --good: #2d6f3f;
      --warn: #a36b00;
      --bad: #9f3a38;
      --shadow-sm: 0 1px 2px rgba(20,22,20,0.04);
      --shadow: 0 1px 2px rgba(20,22,20,0.04), 0 4px 14px rgba(20,22,20,0.05);
      --radius: 12px;
      --radius-sm: 8px;
    }
    * { box-sizing: border-box; }
    html, body { height: 100%; }
    body {
      margin: 0;
      font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
      font-feature-settings: 'cv11', 'ss01', 'ss02';
      color: var(--ink);
      background: var(--bg);
      line-height: 1.45;
      font-size: 14px;
      -webkit-font-smoothing: antialiased;
    }
    header {
      background:
        radial-gradient(900px 250px at 12% -50%, rgba(31,79,83,0.10), transparent 60%),
        linear-gradient(180deg, #fdfcf5, var(--bg));
      border-bottom: 1px solid var(--line);
      padding: 32px 32px 22px;
    }
    .head-row {
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 24px;
      max-width: 1440px;
      margin: 0 auto;
      flex-wrap: wrap;
    }
    .eyebrow {
      font-size: 11px;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      color: var(--accent);
      font-weight: 600;
      margin-bottom: 8px;
    }
    h1 {
      margin: 0;
      font-size: 30px;
      font-weight: 700;
      letter-spacing: -0.02em;
    }
    .sub { color: var(--muted); font-size: 13px; }
    .head-meta {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 999px;
      font-size: 12px;
      color: var(--ink-2);
      box-shadow: var(--shadow-sm);
    }
    .chip .dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--accent);
    }
    .chip.gate-pass .dot { background: var(--good); }
    .chip.gate-fail .dot { background: var(--bad); }
    main {
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px 32px 56px;
    }
    .kpis {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
      margin-bottom: 22px;
    }
    .kpi {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 14px 16px 16px;
      box-shadow: var(--shadow-sm);
      position: relative;
      overflow: hidden;
    }
    .kpi .label {
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      font-weight: 600;
    }
    .kpi .value {
      font-size: 28px;
      font-weight: 700;
      margin-top: 6px;
      letter-spacing: -0.02em;
      color: var(--ink);
    }
    .kpi .delta {
      font-size: 12px;
      color: var(--muted);
      margin-top: 4px;
    }
    .kpi.accent { background: linear-gradient(180deg, #fbfaf4, var(--panel)); }
    .charts {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 24px;
    }
    .chart-card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 16px 18px 12px;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      min-height: 280px;
    }
    .chart-card.span-2 { grid-column: span 2; }
    .chart-head {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
      margin-bottom: 10px;
    }
    .chart-head h3 {
      margin: 0;
      font-size: 14px;
      font-weight: 600;
      letter-spacing: -0.01em;
    }
    .chart-head .sub { font-size: 12px; margin-top: 2px; }
    .chart-head .legend {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      font-size: 11px;
      color: var(--muted);
    }
    .chart-head .legend span {
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }
    .chart-head .legend i {
      width: 9px;
      height: 9px;
      border-radius: 2px;
      display: inline-block;
    }
    .chart-canvas-wrap {
      position: relative;
      flex: 1;
      min-height: 220px;
    }
    .chart-card.tall .chart-canvas-wrap { min-height: 320px; }
    .filters {
      display: grid;
      grid-template-columns: 1.6fr 1fr 1fr 1fr;
      gap: 10px;
      margin: 4px 0 14px;
    }
    input, select {
      width: 100%;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: var(--radius-sm);
      background: var(--panel);
      font: inherit;
      color: var(--ink);
      transition: border-color .12s, box-shadow .12s;
    }
    input:focus, select:focus {
      outline: none;
      border-color: var(--accent);
      box-shadow: 0 0 0 3px var(--accent-soft);
    }
    .table-card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow-sm);
      overflow: hidden;
    }
    .table-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      border-bottom: 1px solid var(--line);
      background: var(--bg-2);
    }
    .table-head h3 { margin: 0; font-size: 14px; font-weight: 600; }
    .table-wrap { overflow-x: auto; }
    table {
      width: 100%;
      border-collapse: collapse;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 10px 14px;
      text-align: left;
      vertical-align: top;
      font-size: 13px;
    }
    th {
      background: #fbfaf4;
      font-size: 11px;
      letter-spacing: 0.07em;
      text-transform: uppercase;
      font-weight: 600;
      color: #5a6066;
      position: sticky;
      top: 0;
      z-index: 1;
    }
    tr:hover td { background: #fafbf6; }
    tr:last-child td { border-bottom: none; }
    .task-id {
      font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
      font-weight: 500;
    }
    .q-text {
      color: var(--muted);
      font-size: 12px;
      margin-top: 3px;
      max-width: 460px;
      overflow: hidden;
      text-overflow: ellipsis;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
    }
    .pill {
      display: inline-block;
      border-radius: 6px;
      padding: 2px 8px;
      margin: 1px 3px 1px 0;
      background: #eef2ee;
      color: #3f494d;
      font-size: 11px;
      white-space: nowrap;
    }
    .pill.diff-easy { background: #e6f1e9; color: #1f5a32; }
    .pill.diff-medium { background: #fdf2da; color: #6d4a07; }
    .pill.diff-hard { background: #f7e0de; color: #7d2b29; }
    .score { font-weight: 700; font-size: 14px; letter-spacing: -0.01em; }
    .score.good { color: var(--good); }
    .score.warn { color: var(--warn); }
    .score.bad { color: var(--bad); }
    .score.none { color: var(--muted); font-weight: 500; }
    .bar-mini {
      width: 60px;
      height: 4px;
      background: #ececea;
      border-radius: 2px;
      overflow: hidden;
      margin-top: 4px;
    }
    .bar-mini > div { height: 100%; background: var(--accent); }
    .meta-line {
      font-size: 11px;
      color: var(--muted);
      margin-top: 2px;
    }
    button {
      border: 1px solid var(--line);
      border-radius: var(--radius-sm);
      background: var(--panel);
      padding: 6px 12px;
      cursor: pointer;
      font: inherit;
      font-size: 13px;
      color: var(--ink-2);
      transition: background .12s, border-color .12s;
    }
    button:hover { background: var(--bg-2); border-color: var(--line-strong); }
    dialog {
      width: min(1180px, calc(100vw - 40px));
      max-height: calc(100vh - 40px);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 0;
      box-shadow: 0 24px 60px rgba(0,0,0,0.2);
    }
    dialog::backdrop { background: rgba(20,22,20,0.36); backdrop-filter: blur(2px); }
    .dialog-head {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      padding: 14px 18px;
      border-bottom: 1px solid var(--line);
      background: var(--bg-2);
    }
    .dialog-body { padding: 18px; overflow: auto; }
    pre {
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: #f6f5ef;
      border: 1px solid var(--line);
      border-radius: var(--radius-sm);
      padding: 10px 12px;
      font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
      max-height: 260px;
      overflow: auto;
    }
    .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    .run-card {
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--panel);
      margin: 10px 0;
      padding: 12px 14px;
    }
    .run-card summary {
      cursor: pointer;
      font-weight: 600;
      list-style: none;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .run-card summary::-webkit-details-marker { display: none; }
    .run-card summary::before {
      content: '';
      width: 8px;
      height: 8px;
      border-right: 1.5px solid var(--ink-2);
      border-bottom: 1.5px solid var(--ink-2);
      transform: rotate(-45deg);
      transition: transform .12s;
    }
    .run-card[open] summary::before { transform: rotate(45deg); }
    .run-meta {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 6px 12px;
      margin: 10px 0;
      color: var(--muted);
      font-size: 12px;
      overflow-wrap: anywhere;
    }
    .run-meta strong { color: var(--ink-2); font-weight: 600; }
    .trace-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 12px;
    }
    .trace-block h4 { margin: 10px 0 6px; font-size: 12px; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); font-weight: 600; }
    .gold-card {
      border: 1px solid var(--line);
      border-left: 3px solid var(--good);
      background: #f4faf5;
      border-radius: var(--radius);
      padding: 12px 14px;
      margin: 8px 0 14px;
    }
    .gold-card h4 { margin: 0 0 8px; font-size: 12px; letter-spacing: 0.06em; text-transform: uppercase; color: var(--good); font-weight: 700; }
    .gold-card .gold-meta { font-size: 12px; color: var(--muted); margin-bottom: 8px; }
    .gold-card .gold-row { display: flex; gap: 8px; margin: 4px 0; font-size: 13px; flex-wrap: wrap; }
    .gold-card .gold-row > strong { min-width: 130px; color: var(--ink-2); }
    .gold-card .gold-row > span { flex: 1; min-width: 0; }
    .gold-card .gold-label {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 6px;
      background: #d6ebd9;
      color: #1f5a32;
      font-weight: 600;
      font-size: 12px;
    }
    .gold-card ol { margin: 4px 0 8px 18px; padding: 0; font-size: 13px; }
    .gold-card ol li { margin: 2px 0; }
    .gold-card .concept {
      display: flex;
      gap: 8px;
      align-items: baseline;
      padding: 4px 0;
      border-top: 1px dashed #d2e3d6;
      font-size: 12.5px;
    }
    .gold-card .concept:first-of-type { border-top: none; }
    .gold-card .concept .cid { font-weight: 600; min-width: 150px; color: var(--ink-2); }
    .gold-card .concept .cw { color: var(--muted); font-size: 11px; min-width: 32px; }
    .gold-card .concept .cterms { color: #2c3138; font-family: 'JetBrains Mono', ui-monospace, Menlo, monospace; font-size: 11.5px; overflow-wrap: anywhere; }
    .gold-card .forbidden { color: var(--bad); }
    .trace-block pre { max-height: 340px; }
    .note { margin: 0 0 10px; color: var(--muted); font-size: 13px; }
    .empty {
      padding: 28px;
      text-align: center;
      color: var(--muted);
      font-size: 13px;
    }
    @media (max-width: 1000px) {
      .charts { grid-template-columns: 1fr; }
      .chart-card.span-2 { grid-column: span 1; }
      .filters { grid-template-columns: 1fr; }
      .grid2 { grid-template-columns: 1fr; }
      header, main { padding-left: 18px; padding-right: 18px; }
    }
  </style>
</head>
<body>
  <header>
    <div class="head-row">
      <div>
        <div class="eyebrow">Capable Bench</div>
        <h1>Pilot Suite Performance</h1>
        <div class="sub" id="subtitle"></div>
      </div>
      <div class="head-meta" id="headMeta"></div>
    </div>
  </header>
  <main>
    <section class="kpis" id="kpis"></section>

    <section class="charts" id="charts">
      <div class="chart-card span-2 tall">
        <div class="chart-head">
          <div>
            <h3>Model leaderboard</h3>
            <div class="sub">Mean score across all scored tasks (latest run per model)</div>
          </div>
          <div class="legend" id="legendLeaderboard"></div>
        </div>
        <div class="chart-canvas-wrap"><canvas id="chartLeaderboard"></canvas></div>
      </div>

      <div class="chart-card">
        <div class="chart-head">
          <div>
            <h3>Score distribution</h3>
            <div class="sub">Tasks per score bin, by model</div>
          </div>
          <div class="legend" id="legendHistogram"></div>
        </div>
        <div class="chart-canvas-wrap"><canvas id="chartHistogram"></canvas></div>
      </div>

      <div class="chart-card">
        <div class="chart-head">
          <div>
            <h3>Reliability</h3>
            <div class="sub">Answer-parsed rate vs non-zero return code</div>
          </div>
        </div>
        <div class="chart-canvas-wrap"><canvas id="chartReliability"></canvas></div>
      </div>

      <div class="chart-card span-2 tall">
        <div class="chart-head">
          <div>
            <h3>Mean score by task type</h3>
            <div class="sub">Per-model mean on each task family</div>
          </div>
          <div class="legend" id="legendTaskType"></div>
        </div>
        <div class="chart-canvas-wrap"><canvas id="chartTaskType"></canvas></div>
      </div>

      <div class="chart-card">
        <div class="chart-head">
          <div>
            <h3>Mean score by difficulty</h3>
            <div class="sub">How performance scales with task difficulty</div>
          </div>
        </div>
        <div class="chart-canvas-wrap"><canvas id="chartDifficulty"></canvas></div>
      </div>

      <div class="chart-card">
        <div class="chart-head">
          <div>
            <h3>Mean score by capability target</h3>
            <div class="sub">Tasks contribute to every capability they tag</div>
          </div>
        </div>
        <div class="chart-canvas-wrap"><canvas id="chartCapability"></canvas></div>
      </div>
    </section>

    <section class="filters">
      <input id="search" placeholder="Search tasks, questions, capabilities…">
      <select id="typeFilter"><option value="">All task types</option></select>
      <select id="difficultyFilter"><option value="">All difficulties</option></select>
      <select id="modelFilter"><option value="">All model columns</option></select>
    </section>
    <section class="table-card">
      <div class="table-head">
        <h3 id="tableHeading">Tasks</h3>
        <div class="sub" id="tableSub"></div>
      </div>
      <div class="table-wrap">
        <table>
          <thead id="thead"></thead>
          <tbody id="tbody"></tbody>
        </table>
      </div>
    </section>
  </main>
  <dialog id="detailDialog">
    <div class="dialog-head">
      <div>
        <strong id="detailTitle"></strong>
        <div class="sub" id="detailSub"></div>
      </div>
      <button onclick="document.getElementById('detailDialog').close()">Close</button>
    </div>
    <div class="dialog-body" id="detailBody"></div>
  </dialog>
  <script>
    const DATA = __PAYLOAD_JSON__;
    const state = { search: "", type: "", difficulty: "", model: "" };
    const PALETTE = ["#1f4f53", "#c97064", "#d4a373", "#5a8a73", "#7b6c8a", "#c4a35a", "#456b8a"];
    const charts = {};

    function colorFor(i) { return PALETTE[i % PALETTE.length]; }
    function alphaFor(i, a) {
      const hex = colorFor(i).replace('#','');
      const n = parseInt(hex, 16);
      const r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
      return `rgba(${r},${g},${b},${a})`;
    }
    function fmtScore(value) {
      if (value === null || value === undefined || Number.isNaN(value)) return "—";
      return Number(value).toFixed(3);
    }
    function fmtPct(value) {
      if (value === null || value === undefined || Number.isNaN(value)) return "—";
      return `${Math.round(value * 100)}%`;
    }
    function scoreClass(value) {
      if (value === null || value === undefined || Number.isNaN(value)) return "none";
      if (value < 0.4) return "bad";
      if (value < 0.6) return "warn";
      return "good";
    }
    function unique(values) {
      return [...new Set(values.filter(Boolean))].sort();
    }
    function difficultyKey(value) {
      return String(value || "").toLowerCase().replace(/[^a-z]/g, "");
    }
    function escapeHtml(value) {
      return String(value == null ? "" : value).replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[ch]));
    }
    function escapeJs(value) {
      return String(value).replace(/['\\]/g, "\\$&");
    }

    function modelColors() {
      return DATA.models.map((m, i) => ({ model: m, color: colorFor(i) }));
    }

    function init() {
      const taskTypes = unique(DATA.tasks.map(t => t.task_type));
      const difficulties = unique(DATA.tasks.map(t => t.difficulty));
      const haveRuns = DATA.models.length > 0;
      document.getElementById("subtitle").textContent =
        `${DATA.tasks.length} tasks · ${taskTypes.length} task types · ${DATA.models.length} model${DATA.models.length === 1 ? "" : "s"} compared`;
      renderHeadMeta();
      renderKpis();
      if (haveRuns) {
        renderCharts();
      } else {
        document.getElementById("charts").innerHTML = '<div class="chart-card span-2"><div class="empty">No scored runs yet — once you run the suite, leaderboards and breakdowns will appear here.</div></div>';
      }
      fillSelect("typeFilter", taskTypes);
      fillSelect("difficultyFilter", difficulties);
      fillSelect("modelFilter", DATA.models);
      ["search", "typeFilter", "difficultyFilter", "modelFilter"].forEach(id => {
        document.getElementById(id).addEventListener("input", event => {
          const map = { search: "search", typeFilter: "type", difficultyFilter: "difficulty", modelFilter: "model" };
          state[map[id]] = event.target.value;
          renderTable();
        });
      });
      renderTable();
    }
    function fillSelect(id, values) {
      const el = document.getElementById(id);
      values.forEach(value => {
        const opt = document.createElement("option");
        opt.value = value;
        opt.textContent = value;
        el.appendChild(opt);
      });
    }
    function renderHeadMeta() {
      const head = document.getElementById("headMeta");
      const chips = [];
      if (DATA.calibration) {
        const passed = DATA.calibration.quality_gate_passed;
        chips.push(`<div class="chip ${passed ? "gate-pass" : "gate-fail"}"><span class="dot"></span>Calibration gate · ${passed ? "passed" : "check"}</div>`);
        if (DATA.calibration.hard_fraction !== undefined) {
          chips.push(`<div class="chip">Hard fraction · ${(DATA.calibration.hard_fraction * 100).toFixed(0)}%</div>`);
        }
        if (DATA.calibration.saturation_target) {
          chips.push(`<div class="chip">Saturation target · ${escapeHtml(DATA.calibration.saturation_target)}</div>`);
        }
      }
      head.innerHTML = chips.join("");
    }
    function renderKpis() {
      const kpis = document.getElementById("kpis");
      const taskTypes = unique(DATA.tasks.map(t => t.task_type)).length;
      const hard = DATA.tasks.filter(t => (t.difficulty || "").toLowerCase() === "hard").length;
      const ranked = DATA.models
        .map(m => [m, DATA.model_summary[m]?.mean_score])
        .filter(([, v]) => v !== null && v !== undefined)
        .sort((a, b) => b[1] - a[1]);
      const cards = [
        { label: "Tasks", value: DATA.tasks.length, delta: `${taskTypes} task types` },
        { label: "Hard tasks", value: hard, delta: `${Math.round(100 * hard / Math.max(DATA.tasks.length, 1))}% of suite` },
        { label: "Models scored", value: DATA.models.length || "—", delta: DATA.models.join(" · ") || "no runs yet" },
      ];
      if (ranked.length) {
        const [topModel, topScore] = ranked[0];
        cards.push({ label: "Top mean score", value: fmtScore(topScore), delta: topModel, accent: true });
        if (ranked.length > 1) {
          const [secondModel, secondScore] = ranked[1];
          cards.push({ label: "Runner-up", value: fmtScore(secondScore), delta: `${secondModel} · Δ ${(topScore - secondScore).toFixed(3)}` });
        }
      }
      kpis.innerHTML = cards.map(card =>
        `<div class="kpi${card.accent ? " accent" : ""}">
          <div class="label">${escapeHtml(card.label)}</div>
          <div class="value">${escapeHtml(String(card.value))}</div>
          <div class="delta">${escapeHtml(card.delta || "")}</div>
        </div>`
      ).join("");
    }
    function makeLegend(id) {
      const el = document.getElementById(id);
      if (!el) return;
      el.innerHTML = modelColors().map(({ model, color }) =>
        `<span><i style="background:${color}"></i>${escapeHtml(model)}</span>`
      ).join("");
    }
    function scoresPerModel() {
      const out = {};
      DATA.models.forEach(m => out[m] = []);
      DATA.tasks.forEach(task => {
        DATA.models.forEach(m => {
          const run = task.latest_runs[m];
          if (run && typeof run.score === "number") out[m].push(run.score);
        });
      });
      return out;
    }
    function meanScoresByGroup(getGroups) {
      const buckets = {};
      DATA.tasks.forEach(task => {
        const groups = getGroups(task);
        groups.forEach(g => {
          if (!g) return;
          buckets[g] = buckets[g] || {};
          DATA.models.forEach(m => {
            const run = task.latest_runs[m];
            if (run && typeof run.score === "number") {
              buckets[g][m] = buckets[g][m] || [];
              buckets[g][m].push(run.score);
            }
          });
        });
      });
      const labels = Object.keys(buckets).sort();
      const datasets = DATA.models.map((m, i) => ({
        label: m,
        backgroundColor: alphaFor(i, 0.85),
        borderColor: colorFor(i),
        borderWidth: 1,
        borderRadius: 4,
        data: labels.map(g => {
          const arr = (buckets[g] && buckets[g][m]) || [];
          if (!arr.length) return null;
          return arr.reduce((a, b) => a + b, 0) / arr.length;
        }),
      }));
      return { labels, datasets };
    }
    function renderCharts() {
      Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
      Chart.defaults.color = "#2c3138";
      const grid = "#ececea";
      const ticks = "#5a6066";

      // Leaderboard
      const sorted = DATA.models
        .map((m, i) => ({ m, i, mean: DATA.model_summary[m]?.mean_score ?? 0, tasks: DATA.model_summary[m]?.tasks ?? 0 }))
        .sort((a, b) => b.mean - a.mean);
      charts.leaderboard = new Chart(document.getElementById("chartLeaderboard"), {
        type: "bar",
        data: {
          labels: sorted.map(s => s.m),
          datasets: [{
            label: "Mean score",
            data: sorted.map(s => s.mean),
            backgroundColor: sorted.map(s => alphaFor(s.i, 0.85)),
            borderColor: sorted.map(s => colorFor(s.i)),
            borderWidth: 1,
            borderRadius: 6,
          }],
        },
        options: {
          indexAxis: "y",
          maintainAspectRatio: false,
          responsive: true,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: ctx => {
                  const s = sorted[ctx.dataIndex];
                  return `${ctx.parsed.x.toFixed(3)} · ${s.tasks} tasks`;
                },
              },
            },
          },
          scales: {
            x: { min: 0, max: 1, grid: { color: grid }, ticks: { color: ticks, callback: v => v.toFixed(1) } },
            y: { grid: { display: false }, ticks: { color: ticks, font: { weight: "600" } } },
          },
        },
      });
      makeLegend("legendLeaderboard");

      // Histogram
      const bins = 10;
      const histLabels = Array.from({ length: bins }, (_, i) => `${(i / bins).toFixed(1)}`);
      const sp = scoresPerModel();
      const histDatasets = DATA.models.map((m, i) => {
        const counts = new Array(bins).fill(0);
        sp[m].forEach(s => {
          const b = Math.min(bins - 1, Math.max(0, Math.floor(s * bins)));
          counts[b]++;
        });
        return {
          label: m,
          data: counts,
          backgroundColor: alphaFor(i, 0.85),
          borderColor: colorFor(i),
          borderWidth: 1,
          borderRadius: 3,
        };
      });
      charts.histogram = new Chart(document.getElementById("chartHistogram"), {
        type: "bar",
        data: { labels: histLabels, datasets: histDatasets },
        options: {
          maintainAspectRatio: false,
          responsive: true,
          plugins: { legend: { display: false }, tooltip: { mode: "index", intersect: false } },
          scales: {
            x: { stacked: false, grid: { display: false }, ticks: { color: ticks } },
            y: { beginAtZero: true, grid: { color: grid }, ticks: { color: ticks, precision: 0 }, title: { display: true, text: "Tasks", color: ticks, font: { size: 11 } } },
          },
        },
      });
      makeLegend("legendHistogram");

      // Reliability
      const parsedData = DATA.models.map(m => DATA.model_summary[m]?.parsed_rate ?? 0);
      const errorData = DATA.models.map(m => DATA.model_summary[m]?.error_rate ?? 0);
      charts.reliability = new Chart(document.getElementById("chartReliability"), {
        type: "bar",
        data: {
          labels: DATA.models,
          datasets: [
            { label: "Parsed", data: parsedData, backgroundColor: "rgba(45,111,63,0.85)", borderColor: "#2d6f3f", borderWidth: 1, borderRadius: 4 },
            { label: "Error rc≠0", data: errorData, backgroundColor: "rgba(159,58,56,0.85)", borderColor: "#9f3a38", borderWidth: 1, borderRadius: 4 },
          ],
        },
        options: {
          maintainAspectRatio: false,
          responsive: true,
          plugins: {
            legend: { position: "bottom", labels: { boxWidth: 12, padding: 12, font: { size: 11 } } },
            tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${(ctx.parsed.y * 100).toFixed(1)}%` } },
          },
          scales: {
            x: { grid: { display: false }, ticks: { color: ticks } },
            y: { beginAtZero: true, max: 1, grid: { color: grid }, ticks: { color: ticks, callback: v => `${Math.round(v * 100)}%` } },
          },
        },
      });

      // By task type
      const byType = meanScoresByGroup(t => [t.task_type]);
      charts.taskType = new Chart(document.getElementById("chartTaskType"), {
        type: "bar",
        data: byType,
        options: {
          maintainAspectRatio: false,
          responsive: true,
          plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y == null ? "—" : ctx.parsed.y.toFixed(3)}` } },
          },
          scales: {
            x: { grid: { display: false }, ticks: { color: ticks, autoSkip: false, maxRotation: 35, minRotation: 25 } },
            y: { min: 0, max: 1, grid: { color: grid }, ticks: { color: ticks, callback: v => v.toFixed(1) } },
          },
        },
      });
      makeLegend("legendTaskType");

      // By difficulty (custom ordering)
      const diffOrder = ["easy", "medium", "hard"];
      const byDiffRaw = meanScoresByGroup(t => [t.difficulty || ""]);
      const order = byDiffRaw.labels
        .map(l => ({ l, i: diffOrder.indexOf(String(l).toLowerCase()) }))
        .sort((a, b) => (a.i === -1 ? 99 : a.i) - (b.i === -1 ? 99 : b.i));
      const byDiff = {
        labels: order.map(o => o.l),
        datasets: byDiffRaw.datasets.map(ds => ({ ...ds, data: order.map(o => ds.data[byDiffRaw.labels.indexOf(o.l)]) })),
      };
      charts.difficulty = new Chart(document.getElementById("chartDifficulty"), {
        type: "bar",
        data: byDiff,
        options: {
          maintainAspectRatio: false,
          responsive: true,
          plugins: {
            legend: { position: "bottom", labels: { boxWidth: 12, padding: 10, font: { size: 11 } } },
            tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y == null ? "—" : ctx.parsed.y.toFixed(3)}` } },
          },
          scales: {
            x: { grid: { display: false }, ticks: { color: ticks } },
            y: { min: 0, max: 1, grid: { color: grid }, ticks: { color: ticks, callback: v => v.toFixed(1) } },
          },
        },
      });

      // By capability
      const byCap = meanScoresByGroup(t => String(t.capability_targets || "").split(";").map(s => s.trim()).filter(Boolean));
      charts.capability = new Chart(document.getElementById("chartCapability"), {
        type: "bar",
        data: byCap,
        options: {
          indexAxis: "y",
          maintainAspectRatio: false,
          responsive: true,
          plugins: {
            legend: { position: "bottom", labels: { boxWidth: 12, padding: 10, font: { size: 11 } } },
            tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.x == null ? "—" : ctx.parsed.x.toFixed(3)}` } },
          },
          scales: {
            x: { min: 0, max: 1, grid: { color: grid }, ticks: { color: ticks, callback: v => v.toFixed(1) } },
            y: { grid: { display: false }, ticks: { color: ticks, font: { size: 11 } } },
          },
        },
      });
    }
    function visibleModels() {
      return state.model ? [state.model] : DATA.models;
    }
    function renderTable() {
      const models = visibleModels();
      document.getElementById("thead").innerHTML = `<tr>
        <th style="min-width:280px">Task</th>
        <th>Type</th>
        <th>Difficulty</th>
        <th>Capabilities</th>
        <th>Evidence</th>
        ${models.map(m => `<th>${escapeHtml(m)}</th>`).join("")}
        <th></th>
      </tr>`;
      const q = state.search.toLowerCase();
      const rows = DATA.tasks.filter(task => {
        if (state.type && task.task_type !== state.type) return false;
        if (state.difficulty && task.difficulty !== state.difficulty) return false;
        const haystack = `${task.id} ${task.task_type} ${task.question} ${task.capability_targets} ${task.evidence_layers}`.toLowerCase();
        return !q || haystack.includes(q);
      });
      document.getElementById("tableSub").textContent = `${rows.length} of ${DATA.tasks.length} task${DATA.tasks.length === 1 ? "" : "s"} shown`;
      if (!rows.length) {
        document.getElementById("tbody").innerHTML = `<tr><td colspan="${5 + models.length + 1}"><div class="empty">No tasks match the current filters.</div></td></tr>`;
        return;
      }
      document.getElementById("tbody").innerHTML = rows.map(task => {
        const modelCells = models.map(model => {
          const run = task.latest_runs[model];
          if (!run) return '<td><div class="score none">—</div></td>';
          const parsed = run.grade && run.grade.parsed_answer ? "" : " · unparsed";
          const rc = run.returncode === 0 || run.returncode == null ? "" : ` · rc=${run.returncode}`;
          const widthPct = run.score == null ? 0 : Math.max(2, Math.min(100, run.score * 100));
          return `<td>
            <div class="score ${scoreClass(run.score)}">${fmtScore(run.score)}</div>
            <div class="bar-mini"><div style="width:${widthPct}%"></div></div>
            <div class="meta-line">${escapeHtml(run.run_id)}${parsed}${rc}</div>
          </td>`;
        }).join("");
        const diffClass = difficultyKey(task.difficulty);
        const diffPill = task.difficulty
          ? `<span class="pill diff-${diffClass}">${escapeHtml(task.difficulty)}</span>`
          : "";
        return `<tr>
          <td>
            <div class="task-id">${escapeHtml(task.id)}</div>
            <div class="q-text">${escapeHtml(task.question || "")}</div>
          </td>
          <td>${escapeHtml(task.task_type)}</td>
          <td>${diffPill}</td>
          <td>${pills(task.capability_targets)}</td>
          <td>${pills(task.evidence_layers)}</td>
          ${modelCells}
          <td><button onclick="showDetail('${escapeJs(task.id)}')">View</button></td>
        </tr>`;
      }).join("");
    }
    function pills(value) {
      return String(value || "").split(";").map(v => v.trim()).filter(Boolean)
        .map(v => `<span class="pill">${escapeHtml(v)}</span>`).join("");
    }
    function renderGold(task) {
      const g = task.gold_answer;
      if (!g || (typeof g === "object" && !Object.keys(g).length)) return "";
      const labelStatus = g.label_status || task.label_status || "";
      const parts = [];
      parts.push(`<div class="gold-meta">Label status · ${escapeHtml(labelStatus || "—")}${g.outcome_definition ? ` · ${escapeHtml(g.outcome_definition)}` : ""}</div>`);
      // Hit-prediction style: simple gold_label
      if (g.gold_label !== undefined) {
        parts.push(`<div class="gold-row"><strong>Gold label</strong><span class="gold-label">${escapeHtml(g.gold_label)}</span></div>`);
        if (Array.isArray(g.accepted_labels) && g.accepted_labels.length) {
          parts.push(`<div class="gold-row"><strong>Accepted</strong><span>${g.accepted_labels.map(v => `<span class="pill">${escapeHtml(v)}</span>`).join("")}</span></div>`);
        }
      }
      // Ranking-style golds
      const rankFields = [
        ["gold_top", "Gold top"],
        ["gold_top_k", "Gold top-K"],
        ["gold_top_3", "Gold top-3"],
        ["gold_ranking", "Gold ranking"],
        ["gold_full_ranking", "Gold full ranking"],
      ];
      rankFields.forEach(([field, label]) => {
        const arr = g[field];
        if (Array.isArray(arr) && arr.length) {
          parts.push(`<div class="gold-row"><strong>${label}</strong><span><ol>${arr.map(v => `<li>${escapeHtml(typeof v === "object" ? JSON.stringify(v) : v)}</li>`).join("")}</ol></span></div>`);
        }
      });
      if (g.top_k !== undefined) {
        parts.push(`<div class="gold-row"><strong>K</strong><span>${escapeHtml(g.top_k)}</span></div>`);
      }
      if (g.auto_score_cap !== undefined) {
        parts.push(`<div class="gold-row"><strong>Auto-score cap</strong><span>${escapeHtml(g.auto_score_cap)}</span></div>`);
      }
      // Rubric style
      const rubric = g.rubric;
      if (rubric && typeof rubric === "object") {
        const required = rubric.required_concepts || rubric.concepts;
        if (Array.isArray(required) && required.length) {
          const rows = required.map(c => {
            const cid = c.id || c.name || "concept";
            const w = c.weight !== undefined ? `w=${c.weight}` : "";
            const terms = (c.any_terms || c.terms || []).join(" · ");
            return `<div class="concept"><span class="cid">${escapeHtml(cid)}</span><span class="cw">${escapeHtml(w)}</span><span class="cterms">${escapeHtml(terms)}</span></div>`;
          }).join("");
          parts.push(`<div class="gold-row"><strong>Required concepts</strong><span>${rows}</span></div>`);
        }
        const forbidden = rubric.forbidden_terms || rubric.forbidden;
        if (Array.isArray(forbidden) && forbidden.length) {
          parts.push(`<div class="gold-row"><strong>Forbidden</strong><span>${forbidden.map(v => `<span class="pill forbidden">${escapeHtml(v)}</span>`).join("")}</span></div>`);
        }
        const cap = rubric.auto_score_cap;
        if (cap !== undefined) {
          parts.push(`<div class="gold-row"><strong>Auto-score cap</strong><span>${escapeHtml(cap)}</span></div>`);
        }
      }
      // Anything else: dump raw at the bottom for completeness
      parts.push(`<details><summary class="sub" style="cursor:pointer;margin-top:8px">Raw gold YAML</summary><pre>${escapeHtml(JSON.stringify(g, null, 2))}</pre></details>`);
      return `<div class="gold-card"><h4>Right answer</h4>${parts.join("")}</div>`;
    }
    function showDetail(taskId) {
      const task = DATA.tasks.find(t => t.id === taskId);
      document.getElementById("detailTitle").textContent = task.id;
      const subParts = [task.task_type, task.difficulty].filter(Boolean);
      document.getElementById("detailSub").textContent = subParts.join(" · ");
      const runBlocks = DATA.models.map(model => {
        const run = task.latest_runs[model];
        if (!run) return `<details class="run-card"><summary>${escapeHtml(model)} · no run found</summary></details>`;
        return `<details class="run-card" open>
          <summary><span style="font-weight:600">${escapeHtml(model)}</span> <span class="score ${scoreClass(run.score)}">${fmtScore(run.score)}</span></summary>
          <div class="run-meta">
            <div><strong>Run</strong><br>${escapeHtml(run.run_id)}</div>
            <div><strong>Return code</strong><br>${escapeHtml(run.returncode ?? "—")}</div>
            <div><strong>Duration</strong><br>${run.duration_seconds == null ? "—" : Number(run.duration_seconds).toFixed(2) + "s"}</div>
            <div><strong>Run dir</strong><br>${escapeHtml(run.run_dir)}</div>
          </div>
          <div class="trace-block"><h4>Command</h4><pre>${escapeHtml(run.command || "")}</pre></div>
          <div class="trace-grid">
            <div class="trace-block"><h4>Grade</h4><pre>${escapeHtml(JSON.stringify(run.grade, null, 2))}</pre></div>
            <div class="trace-block"><h4>Answer artifact</h4><pre>${escapeHtml(run.answer_text || "")}</pre></div>
            <div class="trace-block"><h4>Agent trace</h4><pre>${escapeHtml(run.trace_text || "")}</pre></div>
            <div class="trace-block"><h4>Stdout</h4><pre>${escapeHtml(run.stdout_text || "")}</pre></div>
            <div class="trace-block"><h4>Stderr</h4><pre>${escapeHtml(run.stderr_text || "")}</pre></div>
          </div>
        </details>`;
      }).join("");
      const dataFiles = task.data_files.map(file => `
        <h4>${escapeHtml(file.name)} · ${file.size_bytes} bytes</h4>
        <pre>${escapeHtml(file.preview.join("\n"))}</pre>`).join("");
      document.getElementById("detailBody").innerHTML = `
        <div class="grid2">
          <section><h3>Prompt</h3><pre>${escapeHtml(task.prompt || "")}</pre></section>
          <section><h3>Task metadata</h3><pre>${escapeHtml(JSON.stringify(task.task_yaml, null, 2))}</pre></section>
        </div>
        ${renderGold(task)}
        <section><h3>Data files</h3>${dataFiles || "<p class='sub'>No data files.</p>"}</section>
        <section>
          <h3>Agent trace & artifacts</h3>
          <p class="note">Captured command, answer artifact, combined agent trace, stdout, stderr, and grade for the latest run per model. Agent turns and tool calls only appear when the invoked CLI emits them; hidden model chain-of-thought is not exposed.</p>
          ${runBlocks}
        </section>
      `;
      document.getElementById("detailDialog").showModal();
    }
    init();
  </script>
</body>
</html>
"""
