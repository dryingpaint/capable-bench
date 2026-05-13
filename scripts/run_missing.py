"""Driver: run every task in a task-ID file against a given agent command,
logging progress per task. Avoids constructing 77 --task-id CLI flags."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from capablebench.run import run_task

TASKS_DIR = REPO / "data" / "tasks"
ANSWERS_DIR = REPO / "data" / "answers"
RUNS_DIR = REPO / "runs"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--task-list", required=True, type=Path)
    p.add_argument("--agent-command", required=True)
    p.add_argument("--timeout-seconds", type=int, default=900)
    p.add_argument("--label", required=True, help="claude or codex, for log prefix")
    args = p.parse_args()

    task_ids = [t.strip() for t in args.task_list.read_text().splitlines() if t.strip()]
    print(f"[{args.label}] starting {len(task_ids)} tasks", flush=True)
    t0 = time.time()
    ok = 0
    fail = 0
    for i, tid in enumerate(task_ids, 1):
        start = time.time()
        try:
            result = run_task(
                tid,
                TASKS_DIR,
                ANSWERS_DIR,
                RUNS_DIR,
                args.agent_command,
                timeout_seconds=args.timeout_seconds,
            )
            grade = result.get("grade") or {}
            score = grade.get("score")
            dur = time.time() - start
            print(
                f"[{args.label}] {i:>3d}/{len(task_ids)}  "
                f"{tid:<60s}  score={score}  {dur:>6.1f}s",
                flush=True,
            )
            ok += 1
        except Exception as exc:
            dur = time.time() - start
            print(
                f"[{args.label}] {i:>3d}/{len(task_ids)}  "
                f"{tid:<60s}  ERROR: {exc!r}  {dur:>6.1f}s",
                flush=True,
            )
            fail += 1
    total = time.time() - t0
    print(
        f"[{args.label}] done: ok={ok} fail={fail} total={total:.0f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
