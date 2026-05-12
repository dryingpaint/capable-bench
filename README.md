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
uv run capablebench extract-invivo "<path-to-mouse-data-directory>"
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

Run on Modal instead of locally:

```bash
export OPENAI_API_KEY=...
modal setup
uv run capablebench run TASK_ID \
  --remote modal \
  --agent-command 'codex exec --cd {task_dir} "$(cat {prompt_file})"'
```

Run a task set as parallel Modal function calls:

```bash
uv run capablebench run-suite \
  --remote modal \
  --agent-command 'codex exec --cd {task_dir} "$(cat {prompt_file})"' \
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
3. Curated or outcome-linked task bundles live in `data/tasks/`, with hidden
   answer/rubric files in `data/answers/`.
4. `run` creates an isolated run directory under `runs/`, copies task data, and
   executes the supplied command.
5. `grade` scores an attempt against the hidden answer file.

## Task Curation

Tasks should be curated from linked in vitro/in vivo evidence and should use
experimental outcome labels or explicit expert rubrics.
