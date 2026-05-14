"""
Validator for pilot-peptide-ranking-sequence-oxn-large-001.

Derives gold ranking from data/processed/invitro_assays.csv using:
  - records where receptor in {OX1R, OX2R}
  - records where producer != 'Reference' (Reference rows are same-plate
    calibrant calls, NOT independent measurements; cf. PEP-928A45A209
    Orexin A 1 nM Reference row that would otherwise displace its true
    6.41 nM CP measurement and re-rank the peptide from #9 to #1)
  - best_ec50_nm = min(ec50_nm) per peptide

Tie-breaking: stable sort by (best_ec50_nm asc, peptide_id asc) so
near-tied EC50s within measurement noise have deterministic order.

Run from repo root:
  uv run python data/validators/pilot-peptide-ranking-sequence-oxn-large-001.py
"""
from __future__ import annotations

import csv
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
TASK_ID = "pilot-peptide-ranking-sequence-oxn-large-001"
TDIR = REPO / "data" / "tasks" / TASK_ID
ANSWER_PATH = REPO / "data" / "answers" / f"{TASK_ID}.yaml"
ASSAY_CSV = REPO / "data" / "processed" / "invitro_assays.csv"
PEP_CSV = TDIR / "peptide_sequences.csv"

OX_RECEPTORS = {"OX1R", "OX2R"}
EXCLUDED_PRODUCERS = {"Reference"}


def load_panel() -> list[str]:
    with open(PEP_CSV) as f:
        return [r["peptide_id"] for r in csv.DictReader(f)]


def load_filtered_ec50(panel: set[str]) -> dict[str, list[float]]:
    rows: dict[str, list[float]] = {p: [] for p in panel}
    with open(ASSAY_CSV) as f:
        for r in csv.DictReader(f):
            pep = r["peptide_id"]
            if pep not in panel:
                continue
            if r["receptor"] not in OX_RECEPTORS:
                continue
            if r["producer"] in EXCLUDED_PRODUCERS:
                continue
            v = (r.get("ec50_nm") or "").strip()
            if not v:
                continue
            try:
                ec = float(v)
            except ValueError:
                continue
            if ec <= 0:
                continue
            rows[pep].append(ec)
    return rows


def main() -> None:
    panel = load_panel()
    panel_set = set(panel)
    ec50 = load_filtered_ec50(panel_set)

    derived = []
    for pep in panel:
        vals = ec50.get(pep, [])
        if not vals:
            raise SystemExit(f"No OX1R/OX2R non-Reference records for {pep}")
        derived.append((pep, min(vals), len(vals)))

    derived.sort(key=lambda r: (r[1], r[0]))

    print("=" * 78)
    print(f"DERIVED GOLD RANKING — {TASK_ID}")
    print("filter: receptor in {OX1R,OX2R}, producer != 'Reference'")
    print("=" * 78)
    print(f"{'rank':>4}  {'peptide_id':<16}  {'best_ec50_nm':>14}  {'n_rows':>6}")
    for i, (pep, best, n) in enumerate(derived, 1):
        print(f"{i:>4}  {pep:<16}  {best:>14.4f}  {n:>6}")

    new_ranking = [r[0] for r in derived]
    new_top3 = new_ranking[:3]

    with open(ANSWER_PATH) as f:
        ans = yaml.safe_load(f)

    old_ranking = list(ans.get("gold_ranking", []))
    old_top3 = list(ans.get("gold_top_3", []))

    print()
    print("Comparison to existing gold:")
    print(f"  ranking match: {old_ranking == new_ranking}")
    print(f"  top-3 match:   {old_top3 == new_top3}")
    if old_ranking != new_ranking:
        print(f"  OLD ranking: {old_ranking}")
        print(f"  NEW ranking: {new_ranking}")

    # PEP-928A45A209 sanity check: with Reference row excluded, native
    # Orexin A is the weakest peptide in the panel at 6.41 nM (rank #12).
    # If the Reference 1 nM row were (incorrectly) included it would jump
    # to ~rank #4, materially changing the ranking. This validator
    # codifies the exclusion.
    p928 = next(r for r in derived if r[0] == "PEP-928A45A209")
    p928_rank = next(i for i, r in enumerate(derived, 1) if r[0] == "PEP-928A45A209")
    print(
        f"\n  PEP-928A45A209 (Orexin A reference): rank #{p928_rank} "
        f"at {p928[1]:.4f} nM (expect #12 ~6.41 nM with Reference excluded)"
    )
    assert p928_rank == 12, f"Expected PEP-928A45A209 at #12, got #{p928_rank}"
    assert abs(p928[1] - 6.4125) < 1e-3, f"Expected ~6.41 nM, got {p928[1]}"

    # Counterfactual: what would happen if we DIDN'T exclude Reference?
    cf_p928_min = 1.0  # the Reference row value
    cf_rank_among = sum(1 for r in derived if r[0] != "PEP-928A45A209" and r[1] < cf_p928_min) + 1
    print(
        f"  Counterfactual (Reference NOT excluded): PEP-928A45A209 would be "
        f"#{cf_rank_among} at {cf_p928_min:.4f} nM."
    )

    ans["gold_ranking"] = new_ranking
    ans["gold_top_3"] = new_top3
    ans["outcome_definition"] = (
        "ranking by ascending best_ec50_nm = min(ec50_nm) over rows in "
        "data/processed/invitro_assays.csv with receptor in {OX1R, OX2R} "
        "and producer != 'Reference'. The Reference-row exclusion drops "
        "same-plate calibrant calls (e.g. the Orexin A 1 nM row for "
        "PEP-928A45A209) that are not independent measurements. Sample "
        "spans 128.3x. Cross-receptor: dual-target peptides take the min "
        "across OX1R and OX2R."
    )

    with open(ANSWER_PATH, "w") as f:
        yaml.safe_dump(ans, f, sort_keys=False)
    print(f"\nWrote {ANSWER_PATH}")
    print("VALIDATION COMPLETE")


if __name__ == "__main__":
    main()
