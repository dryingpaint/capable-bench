"""
Validator for pilot-prioritization-nps-001 (window=1h).

Bypasses capablebench/curate.py:_effect_score (which mistakenly rewards HIGH
mean_value -- the wrong sign for sleep_time, where the prompt asks the agent to
prioritize sleep-REDUCING leads).

Derivation rule (corrected):
    score(peptide) = max over dose arms at the task window of:
        signed_effect = placebo_mean - peptide_mean         # +ve = sleep-reducing
        + sig_bonus (only if significant AND direction == "reduced")
    Peptides with no in vivo arms get score = -inf (ranked last; no evidence
    they are sleep-reducing).

Run:  uv run python data/validators/pilot-prioritization-nps-001.py
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

import yaml

TASK_ID = "pilot-prioritization-nps-001"
WINDOW_HOURS = "1"
TOP_K = 3
SIG_BONUS = 5.0  # awarded only if significant AND direction == "reduced"

REPO = Path(__file__).resolve().parent.parent.parent
TASK_DIR = REPO / "data" / "tasks" / TASK_ID
ANSWER_PATH = REPO / "data" / "answers" / f"{TASK_ID}.yaml"
BARS_CSV = REPO / "data" / "processed" / "invivo_olden_analysis_bars.csv"
SIG_CSV = REPO / "data" / "processed" / "invivo_olden_analysis_significance.csv"

STUDY_PREFIX = "NXNv10.15 (100ug vs. 50ug) vs. NXNv10.16"  # filter to the NXN study only


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open() as fh:
        return list(csv.DictReader(fh))


def _load_candidates() -> list[dict[str, str]]:
    return _read_csv(TASK_DIR / "candidates.csv")


def _build_arm_index(rows: list[dict[str, str]], window: str) -> dict[str, list[dict]]:
    """{compound_name_lower: [{dose, mean, ...}, ...]} for a given window."""
    out: dict[str, list[dict]] = {}
    for r in rows:
        if r.get("window_hours") != window:
            continue
        if not r.get("study_name", "").startswith(STUDY_PREFIX):
            continue
        if r.get("metric") != "sleep_time":
            continue
        group = r["group"]
        if group.lower() == "placebo":
            continue
        # group looks like "NXNv12.10 100ug"
        toks = group.rsplit(" ", 1)
        if len(toks) != 2:
            continue
        compound, dose = toks
        out.setdefault(compound.lower(), []).append(
            {
                "compound": compound,
                "dose": dose,
                "mean": float(r["mean_value"]),
                "n": r["n"],
            }
        )
    return out


def _placebo_mean(rows: list[dict[str, str]], window: str) -> float:
    for r in rows:
        if (
            r.get("window_hours") == window
            and r.get("study_name", "").startswith(STUDY_PREFIX)
            and r.get("metric") == "sleep_time"
            and r["group"].lower() == "placebo"
        ):
            return float(r["mean_value"])
    raise RuntimeError(f"No placebo at window {window}")


def _build_sig_index(rows: list[dict[str, str]], window: str) -> dict[tuple[str, str], dict]:
    """{(compound_lower, dose): {p, sig, direction}} for window."""
    out: dict[tuple[str, str], dict] = {}
    for r in rows:
        if r.get("window_hours") != window:
            continue
        if not r.get("study_name", "").startswith(STUDY_PREFIX):
            continue
        if r.get("metric") != "sleep_time":
            continue
        group = r["group"]
        if group.lower() == "placebo":
            continue
        toks = group.rsplit(" ", 1)
        if len(toks) != 2:
            continue
        compound, dose = toks
        out[(compound.lower(), dose)] = {
            "p": float(r["p_value"]),
            "sig": r["significant"].lower() == "true",
            "direction": r["direction"],
        }
    return out


def _score_peptide(
    compound: str, arms: list[dict], sig_idx: dict, placebo_mean: float
) -> tuple[float, dict | None]:
    """Return (score, best_arm_record) — picks the arm with the largest sleep
    reduction (placebo - peptide), with bonus for significant reductions."""
    best_score = -math.inf
    best_record = None
    for arm in arms:
        signed_effect = placebo_mean - arm["mean"]  # +ve when peptide reduces sleep
        sig = sig_idx.get((compound.lower(), arm["dose"]), {})
        bonus = 0.0
        if sig.get("sig") and sig.get("direction") == "reduced":
            # add a small bonus tied to -log10(p) so very-significant beats marginally-sig
            bonus = SIG_BONUS + max(0.0, -math.log10(max(sig.get("p", 1.0), 1e-12)))
        score = signed_effect + bonus
        record = {**arm, **sig, "signed_effect": signed_effect, "bonus": bonus, "score": score}
        if score > best_score:
            best_score = score
            best_record = record
    return best_score, best_record


def main() -> None:
    candidates = _load_candidates()
    bars = _read_csv(BARS_CSV)
    sigs = _read_csv(SIG_CSV)

    placebo_mean = _placebo_mean(bars, WINDOW_HOURS)
    arm_idx = _build_arm_index(bars, WINDOW_HOURS)
    sig_idx = _build_sig_index(sigs, WINDOW_HOURS)

    print(f"\n=== {TASK_ID}  (window={WINDOW_HOURS}h) ===")
    print(f"Placebo mean sleep_time = {placebo_mean:.3f}%")
    print(f"\nPer-candidate scoring (best arm shown):")
    print(f"  {'peptide_id':<18} {'compound':<12} {'arm':<6} {'mean':>7} {'Δvplc':>7} "
          f"{'p':>9} {'sig':>5} {'dir':<10} {'bonus':>6} {'score':>7}")

    scored: list[tuple[float, str, dict | None]] = []
    for c in candidates:
        compound = c["compound"]
        pid = c["peptide_id"]
        arms = arm_idx.get(compound.lower(), [])
        if not arms:
            print(f"  {pid:<18} {compound:<12} {'--':<6} {'--':>7} {'--':>7} "
                  f"{'--':>9} {'--':>5} {'--':<10} {'--':>6} {'NA':>7}  (no in vivo arms)")
            scored.append((-math.inf, pid, None))
            continue
        score, record = _score_peptide(compound, arms, sig_idx, placebo_mean)
        print(f"  {pid:<18} {compound:<12} {record['dose']:<6} "
              f"{record['mean']:>7.2f} {record['signed_effect']:>+7.2f} "
              f"{record.get('p', float('nan')):>9.4f} "
              f"{str(record.get('sig', False)):>5} "
              f"{record.get('direction', ''):<10} "
              f"{record['bonus']:>6.2f} {score:>+7.2f}")
        scored.append((score, pid, record))

    scored.sort(key=lambda t: (-t[0], t[1]))  # descending by score, stable on pid
    gold_ranking = [pid for _, pid, _ in scored]
    gold_top = gold_ranking[:TOP_K]

    print(f"\nDerived gold_top_{TOP_K}:  {gold_top}")
    print(f"Derived gold_ranking:    {gold_ranking}")

    # Sanity check: top pick must have peptide_mean < placebo_mean (sleep-reducing)
    top_score, top_pid, top_record = scored[0]
    if top_record is not None and top_record["mean"] >= placebo_mean:
        raise RuntimeError(
            f"REJECT: top pick {top_pid} has mean {top_record['mean']:.2f} "
            f">= placebo {placebo_mean:.2f} (would reward sleep-INCREASING arm). "
            f"This task should be DISCARD-ed at this window."
        )

    # Preserve other fields in the existing answer YAML
    existing = yaml.safe_load(ANSWER_PATH.read_text()) or {}
    new_outcome = (
        f"rank by largest signed sleep_time reduction (placebo_mean - peptide_mean) "
        f"at window={WINDOW_HOURS}h, with significance bonus for significant "
        f"`direction=reduced` arms"
    )
    new_payload = {
        "id": TASK_ID,
        "task_type": existing.get("task_type", "candidate_prioritization"),
        "label_status": existing.get("label_status", "experimental_ground_truth"),
        "top_k": TOP_K,
        "gold_ranking": gold_ranking,
        "gold_top_3": gold_top,
        "outcome_definition": new_outcome,
    }
    # Preserve any extra fields (notes, random_guess_baseline, etc.)
    for k, v in existing.items():
        if k not in new_payload:
            new_payload[k] = v

    ANSWER_PATH.write_text(yaml.safe_dump(new_payload, sort_keys=False))
    print(f"\nWrote {ANSWER_PATH.relative_to(REPO)}")


if __name__ == "__main__":
    main()
