"""
Validator for cb-nps-polymorphism-001.

Derives the gold (compound with the strongest hNPSR1 Ile107 preference)
from the raw assay data in data/processed/invitro_assays.csv.

Run from repo root:
  uv run python data/validators/cb-nps-polymorphism-001.py
"""
from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
GOLD = yaml.safe_load(open(REPO / "data" / "answers" / "cb-nps-polymorphism-001.yaml"))
CANDIDATES = sorted(GOLD["answer_space"]["most_Ile107_preferring"])
ASSAY_CSV = REPO / "data" / "processed" / "invitro_assays.csv"


def gmean(xs):
    pos = [x for x in xs if x > 0]
    if not pos:
        return float("nan")
    return math.exp(sum(math.log(x) for x in pos) / len(pos))


ec50 = defaultdict(list)
with open(ASSAY_CSV) as f:
    for r in csv.DictReader(f):
        cmp = r["compound"]
        if cmp not in CANDIDATES:
            continue
        rec = r["receptor"]
        if rec not in ("hNPSR1 Asn107", "hNPSR1 Ile107"):
            continue
        v = (r.get("ec50_nm") or "").strip()
        if not v:
            continue
        try:
            v = float(v)
        except ValueError:
            continue
        ec50[(cmp, rec)].append(v)

rows = []
for cmp in CANDIDATES:
    a = gmean(ec50.get((cmp, "hNPSR1 Asn107"), []))
    b = gmean(ec50.get((cmp, "hNPSR1 Ile107"), []))
    pref = a / b if (b > 0 and not math.isnan(a)) else float("nan")
    rows.append((cmp, a, b, pref,
                 len(ec50.get((cmp, "hNPSR1 Asn107"), [])),
                 len(ec50.get((cmp, "hNPSR1 Ile107"), []))))

rows.sort(key=lambda r: -r[3] if not math.isnan(r[3]) else -1)

print("=" * 100)
print("PANEL — Ile107 preference (= Asn EC50 / Ile EC50)")
print("=" * 100)
print(f"{'compound':>20}  {'Asn_nM':>10}  {'Ile_nM':>10}  {'pref':>8}  {'n_Asn':>6}  {'n_Ile':>6}")
for cmp, a, b, p, nA, nI in rows:
    print(f"{cmp:>20}  {a:>10.3f}  {b:>10.3f}  {p:>8.2f}  {nA:>6}  {nI:>6}")

derived = rows[0][0]
declared = GOLD["gold"]["most_Ile107_preferring"]
runner_up = rows[1][0]
print()
print(f"Derived winner:  {derived}  (pref {rows[0][3]:.1f}x)")
print(f"Declared gold:   {declared}")
print(f"Runner-up:       {runner_up}  (pref {rows[1][3]:.1f}x)")
print(f"Gap to runner-up: {rows[0][3] / rows[1][3]:.2f}x")
assert derived == declared, f"Gold mismatch: derived={derived!r} vs declared={declared!r}"

print(f"\nRandom-guess baseline: 1/{len(CANDIDATES)} = {1/len(CANDIDATES):.4f}")

LITERATURE_TRAPS = {"hNPS(1-10)", "rNPS(1-10)", "NPS"}
for trap in LITERATURE_TRAPS:
    rank = next((i for i, r in enumerate(rows, 1) if r[0] == trap), None)
    if rank is None:
        continue
    pref = next(r[3] for r in rows if r[0] == trap)
    print(f"  literature trap {trap:>14}: rank #{rank}, pref {pref:.2f}x")

print("\n" + "=" * 100)
print("VALIDATION COMPLETE")
print("=" * 100)
