"""
Validator for pilot-peptide-ranking-sequence-nps-medium-001.

Re-derives the gold ranking from data/processed/invitro_assays.csv under a
stricter validity criterion: best EC50 is computed only at NPS-family
receptors ({hNPSR1 Asn107, hNPSR1 Ile107, mNPSR1}), excluding rows where
producer == 'Reference' (same-plate calibrant rows). Peptides with no
qualifying NPSR1 record receive best_ec50_nm = inf and sort to the bottom.

Run from repo root:
  uv run python data/validators/pilot-peptide-ranking-sequence-nps-medium-001.py
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

import yaml

TASK_ID = "pilot-peptide-ranking-sequence-nps-medium-001"
NPSR1_RECEPTORS = {"hNPSR1 Asn107", "hNPSR1 Ile107", "mNPSR1"}

REPO = Path(__file__).resolve().parents[2]
TASK_DIR = REPO / "data" / "tasks" / TASK_ID
ANSWER_PATH = REPO / "data" / "answers" / f"{TASK_ID}.yaml"
ASSAY_CSV = REPO / "data" / "processed" / "invitro_assays.csv"
PEPTIDE_CSV = TASK_DIR / "peptide_sequences.csv"


def load_peptide_ids(path: Path) -> list[str]:
    with open(path) as f:
        return [r["peptide_id"] for r in csv.DictReader(f)]


def collect_best_ec50() -> dict[str, float]:
    best: dict[str, float] = {}
    n_rows = 0
    n_kept = 0
    with open(ASSAY_CSV) as f:
        for r in csv.DictReader(f):
            n_rows += 1
            if r["receptor"] not in NPSR1_RECEPTORS:
                continue
            if r["producer"] == "Reference":
                continue
            v = (r.get("ec50_nm") or "").strip()
            if not v:
                continue
            try:
                v = float(v)
            except ValueError:
                continue
            if v <= 0:
                continue
            n_kept += 1
            pid = r["peptide_id"]
            if pid not in best or v < best[pid]:
                best[pid] = v
    print(f"Scanned {n_rows} assay rows; kept {n_kept} NPS-family non-Reference rows.")
    return best


def main() -> None:
    peptide_ids = load_peptide_ids(PEPTIDE_CSV)
    best_all = collect_best_ec50()

    rows = []
    for pid in peptide_ids:
        v = best_all.get(pid, math.inf)
        rows.append((pid, v))
    rows.sort(key=lambda x: (x[1], x[0]))

    print()
    print("=" * 80)
    print(f"DERIVED RANKING — {TASK_ID}")
    print(f"Filter: receptor in {sorted(NPSR1_RECEPTORS)}, producer != 'Reference'")
    print("=" * 80)
    print(f"{'rank':>4}  {'peptide_id':>18}  {'best_ec50_nm':>14}")
    for i, (pid, v) in enumerate(rows, 1):
        s = f"{v:.4f}" if math.isfinite(v) else "inf (no NPSR1 record)"
        print(f"{i:>4}  {pid:>18}  {s:>14}")

    new_ranking = [pid for pid, _ in rows]
    new_top_3 = new_ranking[:3]

    gold = yaml.safe_load(open(ANSWER_PATH))
    old_ranking = gold.get("gold_ranking", [])
    old_top_3 = gold.get("gold_top_3", [])
    print()
    print("OLD gold_top_3:", old_top_3)
    print("NEW gold_top_3:", new_top_3)
    print("OLD gold_ranking:", old_ranking)
    print("NEW gold_ranking:", new_ranking)

    finite = [v for _, v in rows if math.isfinite(v)]
    span = (max(finite) / min(finite)) if finite and min(finite) > 0 else float("nan")

    gold["gold_ranking"] = new_ranking
    gold["gold_top_3"] = new_top_3
    gold["outcome_definition"] = (
        "ranking by ascending best_ec50_nm at NPS-family receptors only "
        "(hNPSR1 Asn107, hNPSR1 Ile107, mNPSR1); excludes producer=Reference "
        "calibrant rows; peptides with no qualifying NPSR1 record receive "
        f"best_ec50_nm = inf and sort to the bottom; finite-sample span {span:.1f}x"
    )

    with open(ANSWER_PATH, "w") as f:
        yaml.safe_dump(gold, f, sort_keys=False)
    print(f"\nWrote: {ANSWER_PATH}")


if __name__ == "__main__":
    main()
