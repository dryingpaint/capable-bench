# capablebench

capablebench is a biological and biochemical reasoning benchmark for coding
agents. The goal is to test whether agents such as Codex or Claude Code can
inspect messy scientific data, run their own analyses, generate hypotheses,
plan experiments, and make experimentally useful drug discovery decisions.

The setup follows the useful parts of BioMysteryBench: each problem has a
prompt, task-specific data files, optional network-domain metadata, and a hidden
answer or rubric. Agents are free to solve the task however they want; the
grader scores the final answer.

The benchmark design is documented in
[BioDiscoveryBench](docs/BIO_DISCOVERY_BENCHMARK.md). It covers translational
candidate ranking, hit prediction, failure diagnosis, mechanistic hypothesis
generation, next-experiment selection, end-to-end discovery program planning,
and tasks that require agents to use or critique biology foundation-model
outputs.

## Quick Start

Install the locked dependencies with uv:

```bash
uv sync
```

```bash
uv run capablebench ingest "<path-to-invitro-mastersheet.xlsx>"
uv run capablebench extract-invivo "<path-to-mouse-data-directory>"
uv run capablebench curate-pilot --clean
uv run capablebench list-tasks
```

For the full private data flow, including in vitro and in vivo extraction, see
[Data Ingestion](docs/DATA_INGESTION.md).

Run an arbitrary agent command against a task:

```bash
uv run capablebench run TASK_ID \
  --agent-command 'codex exec --json --cd {task_dir} "$(cat {prompt_file})"'
```

For Claude Code, use the same placeholder contract with your preferred CLI
flags:

```bash
uv run capablebench run TASK_ID \
  --agent-command 'claude -p --output-format stream-json --verbose "$(cat {prompt_file})"'
```

The runner substitutes:

- `{task_dir}`: isolated working directory for the attempt
- `{prompt_file}`: prompt shown to the agent
- `{answer_file}`: expected final answer path
- `{task_id}`: task identifier

If the agent writes `{answer_file}`, that file is graded. Otherwise stdout is
saved and used as a fallback.

Run the same command across a task set:

```bash
uv run capablebench run-suite \
  --agent-command 'codex exec --json --cd {task_dir} "$(cat {prompt_file})"' \
  --limit 10
uv run capablebench summarize
```

Run on Modal instead of locally:

```bash
export OPENAI_API_KEY=...
modal setup
uv run capablebench run TASK_ID \
  --remote modal \
  --agent-command 'codex exec --json --cd {task_dir} "$(cat {prompt_file})"'
```

Run a task set as parallel Modal function calls:

```bash
uv run capablebench run-suite \
  --remote modal \
  --agent-command 'codex exec --json --cd {task_dir} "$(cat {prompt_file})"' \
  --limit 10
```

The Modal runner bundles each task directory, reconstructs it inside a remote
function, runs the agent command there, grades the result remotely, and writes
the returned artifacts back under `runs/` locally. The image is defined in
`capablebench/modal_app.py` and installs Codex and Claude Code CLIs into a
`modal.Image.debian_slim` container.

## Dependency Management

Use uv for all dependency changes:

```bash
uv add PACKAGE
uv remove PACKAGE
uv lock
uv sync --locked
```

## Current Data Flow

1. `ingest` reads the Excel mastersheet and writes normalized in vitro CSVs to
   `data/processed/`.
2. `extract-invivo` reads mouse Excel/JSON exports and writes local in vivo CSVs
   to `data/processed/`.
3. `curate-pilot` builds benchmark task bundles from processed tables.
4. Curated or outcome-linked task bundles live in `data/tasks/`, with hidden
   answer/rubric files in `data/answers/`.
5. `validate` checks that task bundles and hidden answers are complete.
6. `run` creates an isolated run directory under `runs/`, copies task data, and
   executes the supplied command.
7. `grade` scores an attempt against the hidden answer file.

## Task Curation

Tasks should be curated from linked in vitro/in vivo evidence and should use
experimental outcome labels or explicit expert rubrics. The schema supports
ranking, label, option-ranking, and rubric-scored tasks; see
[Task Schema](docs/TASK_SCHEMA.md).

Build the current private benchmark from processed tables:

```bash
uv run capablebench curate-pilot --clean
uv run capablebench validate
uv run capablebench audit-quality
```


Run a stratified calibration subset by naming task IDs:

```bash
uv run capablebench run-suite \
  --task-id pilot-prioritization-nps-001 \
  --task-id pilot-hit-prediction-001 \
  --agent-command 'codex exec --json --skip-git-repo-check --cd {task_dir} --dangerously-bypass-approvals-and-sandbox "$(cat {prompt_file})"'
```

For a saved subset, drop a YAML manifest under `data/task-sets/<name>.yaml`
with a `tasks:` list of task IDs and pass `--task-set <name>` (or a path).
Manifests are merged with any explicit `--task-id` flags:

```bash
# Run all 60 pairwise potency-prediction tasks on Modal
uv run capablebench run-suite \
  --task-set pairwise \
  --remote modal \
  --max-containers 10 \
  --agent-command 'codex exec --json --cd {task_dir} "$(cat {prompt_file})"'
```

## Performance Dashboard

### Next.js Dashboard (Recommended)

Launch the modern, interactive performance dashboard:

```bash
cd dashboard
./start.sh
```

The dashboard will be available at http://localhost:3000 and provides:

- **Real-time metrics** with auto-refresh every 30 seconds
- **Interactive visualizations** - model leaderboards, score distributions, task breakdowns
- **Advanced filtering** - search, filter by task type, difficulty, and model
- **Tagging system** - automatically flags saturation, format errors, execution issues
- **Detailed task views** - full traces, answers, metadata in organized tabs
- **Professional UX** - modern design with responsive layout

The dashboard reads directly from your existing data structure (`data/`, `runs/`) and enhances it with automatic tagging and interactive exploration.

### Static HTML Viewer (Legacy)

Build a local static HTML viewer:

```bash
uv run capablebench build-viewer
```

The generated static HTML viewer is written to `runs/viewer.html`. It shows all
tasks, prompt/data previews, latest per-model scores, and calibration summary
data, regraded against the current hidden answers. For each run it also shows
`agent_trace.txt`, `stdout.txt`, `stderr.txt`, the submitted answer artifact,
and the grade. Use `codex exec --json` or Claude's stream JSON output if you
want agent turns and tool calls in the trace.
