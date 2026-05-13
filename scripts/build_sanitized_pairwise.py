"""Build sanitized variants of pairwise tasks whose `modification` field
contains literature anchors. Removes parenthetical text matching literature
signals (year, scaffold, compound N, author surnames, native-peptide names)
while preserving legitimate chemistry annotations like (hArg), (D-Arg), etc.

Outputs new task directories under data/tasks/probe-lit-sanitized-* and
copies the gold YAML to data/answers/. Original tasks are NOT modified.

After this runs, kick off both agents on the new task IDs to test whether
removing literature anchors changes accuracy."""
from __future__ import annotations
import csv, re, shutil
from pathlib import Path
import yaml

REPO = Path(__file__).resolve().parents[1]
TASKS = REPO / "data/tasks"
ANS = REPO / "data/answers"

# Literature / compound-name signals that mark a parenthetical as a retrieval handle
LIT_SIGNALS = re.compile(
    r"\b\d{4}\b"                                  # year (e.g., 2001)
    r"|\bcompound\s+\d+\b"                        # "compound 19"
    r"|\bscaffold\b"                              # "scaffold"
    r"|\bet\s+al\b"                               # "et al"
    r"|\b(?:Bednarek|Asahi|Sakurai|Reinscheid|Camarda|Kageyama)\b"  # author surnames
    r"|\b(?:human|murine|rat|mouse)\s+(?:orexin|NPS|MCH)"           # "human orexin A"
    r"|\bnative\s+(?:NPS|orexin|MCH)"             # "native NPS"
    r"|\bpublished\b|\breported\b",
    re.IGNORECASE,
)


def _find_balanced_parens(s: str) -> list[tuple[int, int]]:
    """Return [(start, end_exclusive)] of every top-level balanced () group."""
    spans = []
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
                # Unbalanced; reset
                depth = 0
                start = None
    return spans


def sanitize(mod: str) -> str:
    """Strip outer-paren groups containing literature signals; keep chemistry."""
    out_parts = []
    cursor = 0
    for start, end in _find_balanced_parens(mod):
        out_parts.append(mod[cursor:start])
        chunk = mod[start:end]
        if not LIT_SIGNALS.search(chunk):
            out_parts.append(chunk)  # keep legitimate chemistry parens
        # else drop the whole balanced group
        cursor = end
    out_parts.append(mod[cursor:])
    out = "".join(out_parts)
    # Tidy: collapse whitespace, strip trailing punctuation/dashes
    out = re.sub(r"\s+", " ", out)
    out = re.sub(r"\s*-\s*$", "", out)
    return out.strip()


def main() -> None:
    pairwise_dirs = sorted(
        d for d in TASKS.iterdir()
        if d.name.startswith("pilot-peptide-pairwise-sequence-") and d.is_dir()
    )
    created = []
    for src in pairwise_dirs:
        csv_path = src / "peptide_sequences.csv"
        if not csv_path.exists():
            continue
        rows = list(csv.DictReader(open(csv_path)))
        sanitized_rows = []
        any_change = False
        for r in rows:
            new_mod = sanitize(r["modification"])
            if new_mod != r["modification"]:
                any_change = True
            sanitized_rows.append({**r, "modification": new_mod})
        if not any_change:
            continue
        # New task ID — preserves the original suffix so we can pair results
        new_id = src.name.replace("pilot-peptide-pairwise-sequence-",
                                  "probe-lit-sanitized-pairwise-")
        new_dir = TASKS / new_id
        if new_dir.exists():
            shutil.rmtree(new_dir)
        new_dir.mkdir(parents=True)
        # Copy prompt.md and task.yaml verbatim
        for fname in ("prompt.md", "task.yaml"):
            srcf = src / fname
            if srcf.exists():
                shutil.copy(srcf, new_dir / fname)
        # Patch task.yaml's `id` field so the harness writes under the new id
        ty_path = new_dir / "task.yaml"
        ty = yaml.safe_load(open(ty_path))
        ty["id"] = new_id
        with open(ty_path, "w") as fh:
            yaml.safe_dump(ty, fh, sort_keys=False)
        # Write sanitized CSV
        with open(new_dir / "peptide_sequences.csv", "w") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            for r in sanitized_rows:
                w.writerow(r)
        # Copy answer YAML
        src_ans = ANS / f"{src.name}.yaml"
        dst_ans = ANS / f"{new_id}.yaml"
        if src_ans.exists():
            g = yaml.safe_load(open(src_ans))
            g["id"] = new_id
            with open(dst_ans, "w") as fh:
                yaml.safe_dump(g, fh, sort_keys=False)
        created.append(new_id)
        print(f"  {new_id}")
        for r_orig, r_new in zip(rows, sanitized_rows):
            if r_orig["modification"] != r_new["modification"]:
                print(f"    {r_orig['peptide_id']}:")
                print(f"      before: {r_orig['modification'][:90]}")
                print(f"      after:  {r_new['modification'][:90]}")

    print(f"\nCreated {len(created)} sanitized task variants")
    out_list = REPO / "logs/missing-tasks-sanitized.txt"
    out_list.write_text("\n".join(created) + "\n")
    print(f"Task ID list -> {out_list}")


if __name__ == "__main__":
    main()
