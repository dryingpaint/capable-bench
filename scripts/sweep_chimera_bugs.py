"""Sweep the corpus for off-target-receptor labeling bugs.

For each pairwise / ranking / multitarget task, recompute the gold under
strict family-receptor restriction (NPS tasks → NPSR1 only, OXN → OX1R/OX2R,
MCH → MCHR1/MCHR2). Compare to existing gold. Flag mismatches.

Run from repo root:
  uv run python scripts/sweep_chimera_bugs.py
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
TASKS = REPO / "data/tasks"
ANSWERS = REPO / "data/answers"
ASSAYS_CSV = REPO / "data/processed/invitro_assays.csv"

FAMILY_RECEPTORS = {
    "NPS": ("hNPSR1 Asn107", "hNPSR1 Ile107", "mNPSR1"),
    "OXN": ("OX1R", "OX2R"),
    "MCH": ("MCHR1", "MCHR2"),
}

_ASSAYS = list(csv.DictReader(open(ASSAYS_CSV)))


def best_ec50(peptide_id: str, receptor_filter):
    best = float("inf")
    for r in _ASSAYS:
        if r["peptide_id"] != peptide_id: continue
        if r["receptor"] not in receptor_filter: continue
        if r["producer"] == "Reference": continue
        try:
            v = float(r.get("ec50_nm", "").strip())
            if v <= 0: continue
        except (ValueError, TypeError): continue
        if v < best: best = v
    return best


def infer_family(task_id):
    for f in ("nps", "oxn", "mch"):
        if f"-{f}-" in task_id or task_id.endswith(f"-{f}"):
            return f.upper()
    return None


def sweep_pairwise():
    bugs = []
    for d in sorted(TASKS.glob("pilot-peptide-pairwise-sequence-*")):
        ans_path = ANSWERS / f"{d.name}.yaml"
        if not ans_path.exists(): continue
        ans = yaml.safe_load(open(ans_path))
        family = infer_family(d.name)
        if not family: continue
        receptors = FAMILY_RECEPTORS[family]
        peptides = list(csv.DictReader(open(d / "peptide_sequences.csv")))
        if len(peptides) != 2: continue
        ec50s = {p["peptide_id"]: best_ec50(p["peptide_id"], receptors) for p in peptides}
        ranked = sorted(ec50s, key=ec50s.get)
        derived_winner = ranked[0]
        gold_winner = (ans.get("gold_top") or [None])[0]
        if gold_winner != derived_winner and ec50s[ranked[0]] != float("inf"):
            bugs.append({
                "task": d.name,
                "gold_winner": gold_winner,
                "gold_winner_family_ec50": ec50s.get(gold_winner, "?"),
                "derived_winner": derived_winner,
                "derived_winner_family_ec50": ec50s[derived_winner],
                "family": family,
            })
    return bugs


def sweep_ranking():
    bugs = []
    for d in sorted(TASKS.glob("pilot-peptide-ranking-sequence-*")):
        ans_path = ANSWERS / f"{d.name}.yaml"
        if not ans_path.exists(): continue
        ans = yaml.safe_load(open(ans_path))
        family = infer_family(d.name)
        if not family: continue
        receptors = FAMILY_RECEPTORS[family]
        peptides = list(csv.DictReader(open(d / "peptide_sequences.csv")))
        ec50s = {p["peptide_id"]: best_ec50(p["peptide_id"], receptors) for p in peptides}
        derived_ranking = sorted(ec50s, key=ec50s.get)
        gold_ranking = ans.get("gold_ranking", [])
        top_k = ans.get("top_k", 3)
        gold_top = set(gold_ranking[:top_k])
        derived_top = set(derived_ranking[:top_k])
        if gold_top != derived_top:
            bugs.append({
                "task": d.name,
                "gold_top": list(gold_top),
                "derived_top": list(derived_top),
                "ec50s_at_family": {p: ec50s[p] for p in gold_top | derived_top},
                "family": family,
            })
    return bugs


def main():
    print("=" * 100)
    print("PAIRWISE CHIMERA SWEEP")
    print("=" * 100)
    pairwise_bugs = sweep_pairwise()
    if not pairwise_bugs:
        print("(no pairwise labeling bugs)")
    for b in pairwise_bugs:
        print(f"\n{b['task']} ({b['family']}):")
        print(f"  gold winner:    {b['gold_winner']}  (family EC50 = {b['gold_winner_family_ec50']})")
        print(f"  derived winner: {b['derived_winner']}  (family EC50 = {b['derived_winner_family_ec50']:.4f})")

    print()
    print("=" * 100)
    print("RANKING TOP-K SWEEP")
    print("=" * 100)
    ranking_bugs = sweep_ranking()
    if not ranking_bugs:
        print("(no ranking top-k mismatches)")
    for b in ranking_bugs:
        print(f"\n{b['task']} ({b['family']}):")
        print(f"  gold top-k:    {sorted(b['gold_top'])}")
        print(f"  derived top-k: {sorted(b['derived_top'])}")
        print(f"  EC50s at family receptors:")
        for p, ec in sorted(b['ec50s_at_family'].items(), key=lambda x: x[1]):
            ec_str = f"{ec:.4f} nM" if ec != float("inf") else "inf (no family data)"
            print(f"    {p}: {ec_str}")

    print()
    print("=" * 100)
    print(f"SUMMARY: {len(pairwise_bugs)} pairwise + {len(ranking_bugs)} ranking labeling bugs")
    print("=" * 100)


if __name__ == "__main__":
    main()
