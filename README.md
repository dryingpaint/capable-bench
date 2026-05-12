# Capable Bench

Agentic benchmark harness for translational peptide reasoning tasks. The goal is
to test whether coding agents such as Codex or Claude Code can inspect messy
scientific data, run their own analyses, and make experimentally useful
decisions.

The setup follows the useful parts of BioMysteryBench: each problem has a prompt,
task-specific data files, optional network-domain metadata, and a hidden answer
or rubric. Agents are free to solve the task however they want; the grader scores
the final answer.

## Quick Start

Install the locked dependencies with uv:

```bash
uv sync
```

```bash
uv run capablebench ingest "<path-to-invitro-mastersheet.xlsx>"
uv run capablebench make-tasks --limit 10
uv run capablebench list-tasks
```

For the full private data flow, including in vitro and in vivo extraction, see
[Data Ingestion](docs/DATA_INGESTION.md).

Run an arbitrary agent command against a task:

```bash
uv run capablebench run TASK_ID \
  --agent-command 'codex exec --cd {task_dir} "$(cat {prompt_file})"'
```

For Claude Code, use the same placeholder contract with your preferred CLI
flags:

```bash
uv run capablebench run TASK_ID \
  --agent-command 'claude -p "$(cat {prompt_file})"'
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
  --agent-command 'codex exec --cd {task_dir} "$(cat {prompt_file})"' \
  --limit 10
uv run capablebench summarize
```

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
3. `make-tasks` creates pilot task directories in `data/tasks/` and hidden answer
   YAML files in `data/answers/`.
4. `run` creates an isolated run directory under `runs/`, copies task data, and
   executes the supplied command.
5. `grade` scores an attempt against the hidden answer file.

## Important Status

The current pilot candidate-prioritization tasks use a transparent heuristic
oracle rather than true mouse outcomes. The in vivo extraction now gives us the
local ground-truth source tables needed to replace those pilot labels with
experimental outcome labels.
