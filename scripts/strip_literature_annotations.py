"""Strip named-compound annotations from the `modification` / `full_sequence_resolved`
columns in the benchmark source data. These annotations (e.g.,
'(Bednarek 2001 compound 19 scaffold...)', '(human orexin B 28-mer)') were a curation
leak — they let agents pattern-match to memorized literature instead of reasoning
from sequence. They should never have been in the agent-visible modification field.

This script:
  1. Rewrites data/processed/peptide_full_sequences.csv in place.
  2. Rewrites every data/tasks/<pairwise-or-cb>/peptide_sequences.csv that has the
     annotations baked in.

Run from repo root:
  uv run python scripts/strip_literature_annotations.py
"""
from __future__ import annotations
import csv
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

LIT_SIGNALS = re.compile(
    r"\b\d{4}\b"
    r"|\bcompound\s+\d+\b"
    r"|\bscaffold\b"
    r"|\bet\s+al\b"
    r"|\b(?:Bednarek|Asahi|Sakurai|Reinscheid|Camarda|Kageyama)\b"
    r"|\b(?:human|murine|rat|mouse)\s+(?:orexin|NPS|MCH)"
    r"|\bnative\s+(?:NPS|orexin|MCH)"
    r"|\bpublished\b|\breported\b"
    r"|\b\d{1,3}-mer\b",
    re.IGNORECASE,
)


def _balanced_parens(s: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    depth = 0
    start = None
    for i, ch in enumerate(s):
        if ch == "(":
            if depth == 0:
                start = i
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0 and start is not None:
                spans.append((start, i + 1))
                start = None
            elif depth < 0:
                depth = 0
                start = None
    return spans


def sanitize(mod: str) -> str:
    parts = []
    cursor = 0
    for start, end in _balanced_parens(mod):
        parts.append(mod[cursor:start])
        chunk = mod[start:end]
        if not LIT_SIGNALS.search(chunk):
            parts.append(chunk)
        cursor = end
    parts.append(mod[cursor:])
    out = re.sub(r"\s+", " ", "".join(parts))
    return re.sub(r"\s*-\s*$", "", out).strip()


def rewrite_csv(path: Path, column: str) -> int:
    rows = list(csv.DictReader(open(path)))
    if not rows:
        return 0
    fieldnames = list(rows[0].keys())
    changed = 0
    for r in rows:
        before = r.get(column, "")
        after = sanitize(before)
        if after != before:
            r[column] = after
            changed += 1
    if changed:
        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow(r)
    return changed


def main() -> None:
    # 1. Source resolution table
    src = REPO / "data/processed/peptide_full_sequences.csv"
    n = rewrite_csv(src, "full_sequence_resolved")
    print(f"peptide_full_sequences.csv: rewrote {n} rows")

    # 2. Curated task CSVs
    task_csvs = sorted(REPO.glob("data/tasks/*/peptide_sequences.csv"))
    total = 0
    for csv_path in task_csvs:
        n = rewrite_csv(csv_path, "modification")
        if n:
            print(f"  {csv_path.relative_to(REPO)}: {n} rows")
            total += 1
    print(f"\nTotal task CSVs touched: {total}")


if __name__ == "__main__":
    main()
