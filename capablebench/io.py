from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import yaml


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        value = yaml.safe_load(f) or {}
    if not isinstance(value, dict):
        raise ValueError(f"Expected mapping in {path}")
    return value


def write_yaml(path: Path, value: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(value, f, sort_keys=False, allow_unicode=False)


def write_json(path: Path, value: Any) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, sort_keys=False)
        f.write("\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})

