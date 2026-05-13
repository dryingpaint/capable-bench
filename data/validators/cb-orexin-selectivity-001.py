"""
Validator for cb-orexin-selectivity-001.

Derives the gold (most OX2R-selective analog) from the raw assay data in
data/processed/invitro_assays.csv. No data fabrication.

Run from repo root:
  uv run python data/validators/cb-orexin-selectivity-001.py
"""
from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
TDIR = REPO / "data" / "tasks" / "cb-orexin-selectivity-001"
GOLD = yaml.safe_load(open(REPO / "data" / "answers" / "cb-orexin-selectivity-001.yaml"))

CANDIDATES = sorted(GOLD["answer_space"]["most_R2_preferring"])
ASSAY_CSV = REPO / "data" / "processed" / "invitro_assays.csv"


def gmean(xs):
    pos = [x for x in xs if x > 0]
    if not pos:
        return float("nan")
    return math.exp(sum(math.log(x) for x in pos) / len(pos))


# Aggregate EC50 by (compound, receptor) across all assay records
ec50 = defaultdict(list)
with open(ASSAY_CSV) as f:
    for r in csv.DictReader(f):
        cmp = r["compound"]
        if cmp not in CANDIDATES:
            continue
        recep = r["receptor"]
        if recep not in ("OX1R", "OX2R"):
            continue
        v = (r.get("ec50_nm") or "").strip()
        if not v:
            continue
        try:
            v = float(v)
        except ValueError:
            continue
        ec50[(cmp, recep)].append(v)

# Derive selectivity per candidate
rows = []
for cmp in CANDIDATES:
    ox1 = gmean(ec50.get((cmp, "OX1R"), []))
    ox2 = gmean(ec50.get((cmp, "OX2R"), []))
    sel = ox1 / ox2 if (ox2 > 0 and not math.isnan(ox1)) else float("nan")
    rows.append((cmp, ox1, ox2, sel,
                 len(ec50.get((cmp, "OX1R"), [])),
                 len(ec50.get((cmp, "OX2R"), []))))

rows.sort(key=lambda r: -r[3] if not math.isnan(r[3]) else -1)

print("=" * 100)
print("CANDIDATE PANEL — selectivity derived from data/processed/invitro_assays.csv")
print("=" * 100)
print(f"{'compound':>12}  {'OX1R_nM':>10}  {'OX2R_nM':>10}  {'sel':>10}  {'n_OX1R':>7}  {'n_OX2R':>7}")
for cmp, ox1, ox2, sel, n1, n2 in rows:
    print(f"{cmp:>12}  {ox1:>10.3f}  {ox2:>10.4f}  {sel:>10.1f}  {n1:>7}  {n2:>7}")

derived_winner = rows[0][0]
declared_winner = GOLD["gold"]["most_R2_preferring"]
runner_up = rows[1][0]
print()
print(f"Derived winner:  {derived_winner}  (selectivity {rows[0][3]:.1f})")
print(f"Declared gold:   {declared_winner}")
print(f"Runner-up:       {runner_up}  (selectivity {rows[1][3]:.1f})")
print(f"Gap to runner-up: {rows[0][3] / rows[1][3]:.1f}x")
assert derived_winner == declared_winner, (
    f"Gold mismatch: derived={derived_winner!r} vs declared={declared_winner!r}"
)


# Trap analysis: what happens if the agent picks the literature-obvious choice?
LITERATURE_TRAP = "OXNv2"  # = Asahi 2003 [Ala11,D-Leu15] / "hardened OXB: D-Leu15"
lit_trap_sel = next(r[3] for r in rows if r[0] == LITERATURE_TRAP)
lit_trap_rank = next(i for i, r in enumerate(rows, 1) if r[0] == LITERATURE_TRAP)
print(f"\nLiterature-recognition trap: {LITERATURE_TRAP} ranks #{lit_trap_rank} "
      f"with selectivity {lit_trap_sel:.1f}x.")
print(f"An agent that pattern-matches OXNv2 to Asahi 2003 will pick the runner-up "
      f"and score 0/1.")

print("\n" + "=" * 100)
print("VALIDATION COMPLETE")
print("=" * 100)
