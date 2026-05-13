# Modal Runner

The benchmark can execute each task as a Modal Function rather than as a local
subprocess.

## Setup

Install dependencies and authenticate Modal:

```bash
uv sync
modal setup
```

For Codex, expose your OpenAI key before invoking the runner:

```bash
export OPENAI_API_KEY=...
```

For Claude Code:

```bash
export ANTHROPIC_API_KEY=...
```

The Modal app creates a secret from these local environment variables at app
startup. The keys are injected into the remote container environment and are not
written to run artifacts.

## Single Task

```bash
uv run capablebench run TASK_ID \
  --remote modal \
  --agent-command 'codex exec --json --cd {task_dir} "$(cat {prompt_file})"'
```

## Suite

```bash
uv run capablebench run-suite \
  --remote modal \
  --agent-command 'codex exec --json --cd {task_dir} "$(cat {prompt_file})"' \
  --limit 10
```

`run-suite --remote modal` submits the task bundle list through Modal `Function.starmap`,
so tasks can run as parallel serverless function calls.

## How It Works

1. The local CLI reads `data/tasks/<task_id>/`.
2. It bundles task files plus the hidden answer YAML, if present.
3. The Modal function reconstructs the task in `/tmp/capable-bench-task/...`.
4. It expands the standard placeholders:
   - `{task_dir}`
   - `{prompt_file}`
   - `{answer_file}`
   - `{task_id}`
5. It runs the command in the remote task directory.
6. It grades `answer.json` or stdout.
7. It returns artifacts to the local machine under `runs/<task_id>/<run_id>/`.

## Image

The image is defined in `capablebench/modal_app.py`:

```python
modal.Image.debian_slim(python_version="3.11")
  .apt_install("curl", "git", "nodejs", "npm", "ripgrep")
  .pip_install("pyyaml>=6.0")
  .run_commands("npm install -g @openai/codex @anthropic-ai/claude-code")
  .add_local_python_source("capablebench")
```

Modal images are defined through factory methods like `Image.debian_slim`, and
local Python packages should be included explicitly with
`Image.add_local_python_source` in current Modal versions.
