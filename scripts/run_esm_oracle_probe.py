"""ESM-2 oracle probe over narrow-ratio pairwise-sequence tasks.

For each `pilot-peptide-pairwise-sequence-{family}-{bucket}-*` task:
  1. Load both peptides' modification strings.
  2. Strip to canonical 20-AA sequence.
  3. Score with ESM-2-650M (mean masked PLL per residue).
  4. Predict winner = peptide with higher mean PLL.
  5. Compare prediction to gold; aggregate by family × bucket.

Outputs per-task CSV and prints an accuracy table to stdout. Compare against
the agent baselines in
docs/findings/pairwise-sequence-calibration/pairwise_paired_by_family.csv.

Usage:
    uv run python scripts/run_esm_oracle_probe.py
    uv run python scripts/run_esm_oracle_probe.py --buckets hard medium
    uv run python scripts/run_esm_oracle_probe.py --buckets trivial easy medium hard
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

import yaml

import modal

REPO = Path(__file__).resolve().parents[1]
ANS = REPO / "data" / "answers"
TASKS = REPO / "data" / "tasks"
OUT = REPO / "docs" / "findings" / "pairwise-sequence-calibration" / "esm_oracle_probe.csv"

_TID_RE = re.compile(r"pilot-peptide-pairwise-sequence-(\w+)-(\w+)-")


def _load_pair(tid: str) -> tuple[dict, dict, str]:
    rows = list(csv.DictReader(open(TASKS / tid / "peptide_sequences.csv")))
    gold = yaml.safe_load(open(ANS / f"{tid}.yaml"))["gold_top"][0]
    return rows[0], rows[1], gold


def _parse_id(tid: str) -> tuple[str, str]:
    m = _TID_RE.match(tid)
    if not m:
        raise ValueError(tid)
    return m.group(1).upper(), m.group(2)


def main(buckets: list[str], task_ids: list[str] | None = None) -> None:
    from capablebench.esm_modal_app import EsmScorer, app, strip_to_canonical

    if task_ids:
        tids = sorted(task_ids)
    else:
        tids = sorted(
            f.stem
            for f in ANS.glob("pilot-peptide-pairwise-sequence-*.yaml")
            if any(f"-{b}-" in f.stem for b in buckets)
        )
    if not tids:
        raise SystemExit(f"No tasks matched buckets={buckets} task_ids={task_ids}")
    print(f"ESM probe: {len(tids)} tasks across buckets={buckets}")

    requests = []
    flat_sequences: list[str] = []
    for tid in tids:
        p1, p2, gold = _load_pair(tid)
        family, bucket = _parse_id(tid)
        c1, d1 = strip_to_canonical(p1["modification"])
        c2, d2 = strip_to_canonical(p2["modification"])
        requests.append(
            {
                "task_id": tid,
                "family": family,
                "bucket": bucket,
                "pep1_id": p1["peptide_id"],
                "pep1_mod": p1["modification"],
                "pep1_canonical": c1,
                "pep1_dropped": ";".join(d1),
                "pep2_id": p2["peptide_id"],
                "pep2_mod": p2["modification"],
                "pep2_canonical": c2,
                "pep2_dropped": ";".join(d2),
                "gold": gold,
                "tied_after_strip": c1 == c2,
            }
        )
        flat_sequences.append(c1)
        flat_sequences.append(c2)

    print(f"Scoring {len(flat_sequences)} sequences via ESM-2-650M on Modal…")
    with modal.enable_output(), app.run():
        scorer = EsmScorer()
        scored = scorer.score.remote(flat_sequences)

    rows = []
    for i, req in enumerate(requests):
        s1, s2 = scored[2 * i], scored[2 * i + 1]
        pll1, pll2 = s1.get("mean_pll"), s2.get("mean_pll")
        if pll1 is None or pll2 is None:
            pred = None
            gap = None
        else:
            pred = req["pep1_id"] if pll1 >= pll2 else req["pep2_id"]
            gap = pll1 - pll2
        correct = (pred == req["gold"]) if pred is not None else None
        rows.append(
            {
                **req,
                "pep1_pll": pll1,
                "pep2_pll": pll2,
                "pll_gap_p1_minus_p2": gap,
                "predicted": pred,
                "correct": correct,
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    agg: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0, 0])
    tied = 0
    for r in rows:
        if r["tied_after_strip"]:
            tied += 1
        if r["correct"] is None:
            continue
        k, n_total, _n_tied = agg[(r["family"], r["bucket"])]
        agg[(r["family"], r["bucket"])] = [
            k + (1 if r["correct"] else 0),
            n_total + 1,
            _n_tied + (1 if r["tied_after_strip"] else 0),
        ]

    print()
    print(f"{'family':<6s} {'bucket':<8s} {'esm_acc':<10s} {'n':<3s} {'tied':<5s}")
    for (family, bucket), (k, n, t) in sorted(agg.items()):
        print(f"{family:<6s} {bucket:<8s} {k / n:<10.2f} {n:<3d} {t:<5d}")
    overall_correct = sum(1 for r in rows if r["correct"])
    overall_scored = sum(1 for r in rows if r["correct"] is not None)
    if overall_scored:
        print(
            f"\noverall: {overall_correct}/{overall_scored} "
            f"= {overall_correct / overall_scored:.2f} (tied after strip: {tied})"
        )
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--buckets",
        nargs="+",
        default=["hard", "medium"],
        help="Pairwise difficulty buckets to include (default: hard medium)",
    )
    parser.add_argument(
        "--task",
        action="append",
        default=None,
        help="Specific task_id to score (repeatable). Overrides --buckets.",
    )
    args = parser.parse_args()
    main(args.buckets, args.task)
