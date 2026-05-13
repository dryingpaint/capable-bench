from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audit import audit_benchmark_quality
from .curate import curate_pilot_tasks
from .grade import grade_attempt
from .ingest import ingest_mastersheet
from .invivo import extract_mouse_data
from .run import run_task
from .suite import run_suite, summarize_runs
from .tasks import list_tasks
from .validate import validate_benchmark
from .viewer import build_viewer


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

    invivo = sub.add_parser("extract-invivo", help="Extract mouse in vivo measurement sheets.")
    invivo.add_argument("mouse_dir", type=Path)
    invivo.add_argument("--out-dir", type=Path, default=PROCESSED_DIR)

    curate = sub.add_parser(
        "curate-pilot",
        help="Build runnable benchmark task bundles from processed tables.",
    )
    curate.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    curate.add_argument("--tasks-dir", type=Path, default=TASKS_DIR)
    curate.add_argument("--answers-dir", type=Path, default=ANSWERS_DIR)
    curate.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing generated task bundles and answer YAMLs first.",
    )

    listing = sub.add_parser("list-tasks", help="List available tasks.")
    listing.add_argument("--tasks-dir", type=Path, default=TASKS_DIR)

    validate = sub.add_parser("validate", help="Validate task bundles and hidden answers.")
    validate.add_argument("--tasks-dir", type=Path, default=TASKS_DIR)
    validate.add_argument("--answers-dir", type=Path, default=ANSWERS_DIR)
    validate.add_argument("--out", type=Path, default=None)

    audit = sub.add_parser("audit-quality", help="Audit benchmark coverage and saturation gates.")
    audit.add_argument("--tasks-dir", type=Path, default=TASKS_DIR)
    audit.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    audit.add_argument("--min-tasks", type=int, default=30)
    audit.add_argument("--min-hard-fraction", type=float, default=0.45)
    audit.add_argument("--saturation-target", type=float, default=0.60)
    audit.add_argument("--out", type=Path, default=None)


    run = sub.add_parser("run", help="Run one task with an arbitrary agent command.")
    run.add_argument("task_id")
    run.add_argument("--agent-command", required=True)
    run.add_argument("--tasks-dir", type=Path, default=TASKS_DIR)
    run.add_argument("--answers-dir", type=Path, default=ANSWERS_DIR)
    run.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    run.add_argument("--timeout-seconds", type=int, default=1800)
    run.add_argument(
        "--remote",
        choices=["local", "modal"],
        default="local",
        help="Execution backend. Default: local.",
    )

    suite = sub.add_parser("run-suite", help="Run every listed task with one agent command.")
    suite.add_argument("--agent-command", required=True)
    suite.add_argument("--tasks-dir", type=Path, default=TASKS_DIR)
    suite.add_argument("--answers-dir", type=Path, default=ANSWERS_DIR)
    suite.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    suite.add_argument("--limit", type=int, default=None)
    suite.add_argument("--task-id", action="append", default=None)
    suite.add_argument("--timeout-seconds", type=int, default=1800)
    suite.add_argument(
        "--remote",
        choices=["local", "modal"],
        default="local",
        help="Execution backend. Default: local.",
    )

    summarize = sub.add_parser("summarize", help="Aggregate grade files under runs/.")
    summarize.add_argument("--runs-dir", type=Path, default=RUNS_DIR)

    viewer = sub.add_parser("build-viewer", help="Build a static HTML task and performance viewer.")
    viewer.add_argument("--tasks-dir", type=Path, default=TASKS_DIR)
    viewer.add_argument("--answers-dir", type=Path, default=ANSWERS_DIR)
    viewer.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    viewer.add_argument("--out", type=Path, default=RUNS_DIR / "viewer.html")
    viewer.add_argument("--include-all-runs", action="store_true")

    grade = sub.add_parser("grade", help="Grade an answer file against a hidden answer YAML.")
    grade.add_argument("answer", type=Path)
    grade.add_argument("gold", type=Path)
    grade.add_argument("--out", type=Path, default=None)

    args = parser.parse_args()

    if args.command == "ingest":
        _print_json(ingest_mastersheet(args.xlsx, args.out_dir))
    elif args.command == "extract-invivo":
        _print_json(extract_mouse_data(args.mouse_dir, args.out_dir))
    elif args.command == "curate-pilot":
        _print_json(
            curate_pilot_tasks(
                args.processed_dir,
                args.tasks_dir,
                args.answers_dir,
                clean=args.clean,
            )
        )
    elif args.command == "list-tasks":
        for task in list_tasks(args.tasks_dir):
            print(f"{task['id']}\t{task['task_type']}\t{task['data_path']}")
    elif args.command == "validate":
        _print_json(validate_benchmark(args.tasks_dir, args.answers_dir, out_path=args.out))
    elif args.command == "audit-quality":
        _print_json(
            audit_benchmark_quality(
                args.tasks_dir,
                args.runs_dir,
                min_tasks=args.min_tasks,
                min_hard_fraction=args.min_hard_fraction,
                saturation_target=args.saturation_target,
                out_path=args.out,
            )
        )
    elif args.command == "run":
        if args.remote == "modal":
            from .modal_runner import run_task_modal

            result = run_task_modal(
                args.task_id,
                args.tasks_dir,
                args.answers_dir,
                args.runs_dir,
                args.agent_command,
                timeout_seconds=args.timeout_seconds,
            )
        else:
            result = run_task(
                args.task_id,
                args.tasks_dir,
                args.answers_dir,
                args.runs_dir,
                args.agent_command,
                timeout_seconds=args.timeout_seconds,
            )
        _print_json(result)
    elif args.command == "run-suite":
        if args.remote == "modal":
            from .modal_runner import run_suite_modal

            result = run_suite_modal(
                args.tasks_dir,
                args.answers_dir,
                args.runs_dir,
                args.agent_command,
                limit=args.limit,
                task_ids=args.task_id,
                timeout_seconds=args.timeout_seconds,
            )
        else:
            result = run_suite(
                args.tasks_dir,
                args.answers_dir,
                args.runs_dir,
                args.agent_command,
                limit=args.limit,
                task_ids=args.task_id,
                timeout_seconds=args.timeout_seconds,
            )
        _print_json(result)
    elif args.command == "summarize":
        _print_json(summarize_runs(args.runs_dir))
    elif args.command == "build-viewer":
        _print_json(
            build_viewer(
                args.tasks_dir,
                args.answers_dir,
                args.runs_dir,
                args.out,
                include_all_runs=args.include_all_runs,
            )
        )
    elif args.command == "grade":
        _print_json(grade_attempt(args.answer, args.gold, args.out))


if __name__ == "__main__":
    main()
