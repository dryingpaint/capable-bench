from __future__ import annotations

import argparse
import json
from pathlib import Path

from .grade import grade_attempt
from .ingest import ingest_mastersheet
from .run import run_task
from .suite import run_suite, summarize_runs
from .tasks import list_tasks, make_pilot_tasks


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
TASKS_DIR = ROOT / "data" / "tasks"
ANSWERS_DIR = ROOT / "data" / "answers"
RUNS_DIR = ROOT / "runs"


def _print_json(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=False))


def main() -> None:
    parser = argparse.ArgumentParser(prog="capablebench")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="Ingest an Excel mastersheet into normalized CSVs.")
    ingest.add_argument("xlsx", type=Path)
    ingest.add_argument("--out-dir", type=Path, default=PROCESSED_DIR)

    make = sub.add_parser("make-tasks", help="Generate pilot tasks from processed data.")
    make.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    make.add_argument("--tasks-dir", type=Path, default=TASKS_DIR)
    make.add_argument("--answers-dir", type=Path, default=ANSWERS_DIR)
    make.add_argument("--limit", type=int, default=None)
    make.add_argument("--min-candidates", type=int, default=6)
    make.add_argument("--max-candidates", type=int, default=12)
    make.add_argument("--top-k", type=int, default=3)
    make.add_argument("--seed", type=int, default=20260511)

    listing = sub.add_parser("list-tasks", help="List generated tasks.")
    listing.add_argument("--tasks-dir", type=Path, default=TASKS_DIR)

    run = sub.add_parser("run", help="Run one task with an arbitrary agent command.")
    run.add_argument("task_id")
    run.add_argument("--agent-command", required=True)
    run.add_argument("--tasks-dir", type=Path, default=TASKS_DIR)
    run.add_argument("--answers-dir", type=Path, default=ANSWERS_DIR)
    run.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    run.add_argument("--timeout-seconds", type=int, default=1800)

    suite = sub.add_parser("run-suite", help="Run every listed task with one agent command.")
    suite.add_argument("--agent-command", required=True)
    suite.add_argument("--tasks-dir", type=Path, default=TASKS_DIR)
    suite.add_argument("--answers-dir", type=Path, default=ANSWERS_DIR)
    suite.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    suite.add_argument("--limit", type=int, default=None)
    suite.add_argument("--timeout-seconds", type=int, default=1800)

    summarize = sub.add_parser("summarize", help="Aggregate grade files under runs/.")
    summarize.add_argument("--runs-dir", type=Path, default=RUNS_DIR)

    grade = sub.add_parser("grade", help="Grade an answer file against a hidden answer YAML.")
    grade.add_argument("answer", type=Path)
    grade.add_argument("gold", type=Path)
    grade.add_argument("--out", type=Path, default=None)

    args = parser.parse_args()

    if args.command == "ingest":
        _print_json(ingest_mastersheet(args.xlsx, args.out_dir))
    elif args.command == "make-tasks":
        _print_json(
            make_pilot_tasks(
                args.processed_dir,
                args.tasks_dir,
                args.answers_dir,
                limit=args.limit,
                min_candidates=args.min_candidates,
                max_candidates=args.max_candidates,
                top_k=args.top_k,
                seed=args.seed,
            )
        )
    elif args.command == "list-tasks":
        for task in list_tasks(args.tasks_dir):
            print(f"{task['id']}\t{task['task_type']}\t{task['data_path']}")
    elif args.command == "run":
        _print_json(
            run_task(
                args.task_id,
                args.tasks_dir,
                args.answers_dir,
                args.runs_dir,
                args.agent_command,
                timeout_seconds=args.timeout_seconds,
            )
        )
    elif args.command == "run-suite":
        _print_json(
            run_suite(
                args.tasks_dir,
                args.answers_dir,
                args.runs_dir,
                args.agent_command,
                limit=args.limit,
                timeout_seconds=args.timeout_seconds,
            )
        )
    elif args.command == "summarize":
        _print_json(summarize_runs(args.runs_dir))
    elif args.command == "grade":
        _print_json(grade_attempt(args.answer, args.gold, args.out))


if __name__ == "__main__":
    main()
