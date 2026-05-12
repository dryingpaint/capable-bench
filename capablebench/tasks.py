from __future__ import annotations

import csv
from pathlib import Path


def list_tasks(tasks_dir: Path) -> list[dict[str, str]]:
    problems_path = tasks_dir / "problems.csv"
    if not problems_path.exists():
        return []
    with problems_path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

