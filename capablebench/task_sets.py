from __future__ import annotations

from pathlib import Path

from .io import read_yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASK_SETS_DIR = ROOT / "data" / "task-sets"


def resolve_task_set_path(name_or_path: str, root: Path | None = None) -> Path:
    """Resolve a task-set reference to a manifest file path.

    Accepts either a short name (e.g. `pairwise`) or an explicit path
    (e.g. `data/task-sets/pairwise.yaml`).
    """
    if name_or_path.endswith(".yaml") or "/" in name_or_path or "\\" in name_or_path:
        return Path(name_or_path)
    base = root if root is not None else DEFAULT_TASK_SETS_DIR
    return base / f"{name_or_path}.yaml"


def load_task_set(name_or_path: str, root: Path | None = None) -> list[str]:
    """Load the list of task IDs from a task-set manifest."""
    path = resolve_task_set_path(name_or_path, root=root)
    if not path.exists():
        raise FileNotFoundError(f"task set manifest not found: {path}")
    data = read_yaml(path)
    tasks = data.get("tasks")
    if not isinstance(tasks, list) or not all(isinstance(t, str) for t in tasks):
        raise ValueError(f"task set {path} must define a `tasks:` list of strings")
    return tasks
