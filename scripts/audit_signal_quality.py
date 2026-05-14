"""Audit gold-answer signal quality across all tasks.

For each task, compute a per-task-type signal score and recommend KEEP / DISCARD / REVIEW.
Sub-noise = gold is within measurement noise of the runner-up; agent has nothing predictable
to predict.

Run from repo root:
  uv run python scripts/audit_signal_quality.py
"""
from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
TASKS = REPO / "data/tasks"
ANSWERS = REPO / "data/answers"
ASSAYS = REPO / "data/processed/invitro_assays.csv"
INVIVO_SIG = REPO / "data/processed/invivo_olden_analysis_significance.csv"


# ---- shared helpers ----

def gmean(xs):
    pos = [x for x in xs if x > 0]
    if not pos:
        return float("nan")
    return math.exp(sum(math.log(x) for x in pos) / len(pos))


def best_ec50(peptide_id: str, receptor_filter=None, exclude_reference=True):
    """Min ec50_nm for a peptide, optionally restricted to receptors and excluding Reference rows."""
    best = float("inf")
    for r in _ASSAYS:
        if r["peptide_id"] != peptide_id:
            continue
        if receptor_filter and r["receptor"] not in receptor_filter:
            continue
        if exclude_reference and r["producer"] == "Reference":
            continue
        try:
            v = float(r.get("ec50_nm", "").strip())
            if v <= 0:
                continue
        except (ValueError, TypeError):
            continue
        if v < best:
            best = v
    return best


_ASSAYS = list(csv.DictReader(open(ASSAYS)))


# ---- per-type checks ----

def check_pairwise(task_dir: Path, ans: dict) -> dict:
    """Pairwise tasks: gold names the more-potent peptide of two. Sub-noise if EC50 ratio < 2x."""
    csv_path = task_dir / "peptide_sequences.csv"
    if not csv_path.exists():
        return {"signal": "review", "note": "no peptide_sequences.csv"}
    rows = list(csv.DictReader(open(csv_path)))
    if len(rows) != 2:
        return {"signal": "review", "note": f"expected 2 peptides, got {len(rows)}"}
    gold = ans.get("gold", {})
    winner_field = next((k for k in ("more_potent", "winner", "better") if k in gold), None)
    if not winner_field:
        # try gold_top_3 / gold_label
        winner = ans.get("gold_label") or ans.get("gold_top", [None])[0]
    else:
        winner = gold[winner_field]
    if not winner:
        return {"signal": "review", "note": "no parseable gold winner"}

    # Find receptor family from task id or csv
    family = rows[0].get("receptor_family", "").upper() or _infer_family(task_dir.name)
    receptors = _family_receptors(family)
    ec50s = {r["peptide_id"]: best_ec50(r["peptide_id"], receptors) for r in rows}
    a, b = rows[0]["peptide_id"], rows[1]["peptide_id"]
    winner_id = winner if winner.startswith("PEP-") else (a if winner == "A" else b)
    loser_id = b if winner_id == a else a
    we, le = ec50s.get(winner_id, float("inf")), ec50s.get(loser_id, float("inf"))
    if we == float("inf") or le == float("inf"):
        return {"signal": "review", "note": f"missing EC50 ({winner_id}={we}, {loser_id}={le})"}
    ratio = le / we
    if ratio < 2:
        sig = "sub_noise"
    elif ratio < 3:
        sig = "noisy"
    else:
        sig = "clean"
    return {"signal": sig, "note": f"winner={winner_id} {we:.2f}nM vs loser {le:.2f}nM (ratio {ratio:.2f}x)"}


def check_ranking(task_dir: Path, ans: dict) -> dict:
    """Ranking tasks: top-k set. Sub-noise if rank-k vs rank-(k+1) EC50 ratio < 2x."""
    top_k = ans.get("top_k", 3)
    ranking = ans.get("gold_ranking", [])
    if len(ranking) < top_k + 1:
        return {"signal": "review", "note": f"ranking shorter than top_k+1 ({len(ranking)} < {top_k+1})"}
    family = _infer_family(task_dir.name)
    receptors = _family_receptors(family)
    ec50s = [best_ec50(p, receptors) for p in ranking]
    if any(e == float("inf") for e in ec50s[:top_k+1]):
        return {"signal": "review", "note": "missing EC50 within top-k+1"}
    cutoff_ratio = ec50s[top_k] / ec50s[top_k - 1]  # rank-(k+1) / rank-k
    if cutoff_ratio < 2:
        sig = "sub_noise"
    elif cutoff_ratio < 3:
        sig = "noisy"
    else:
        sig = "clean"
    return {"signal": sig, "note": f"rank-{top_k}={ec50s[top_k-1]:.3f}nM vs rank-{top_k+1}={ec50s[top_k]:.3f}nM (ratio {cutoff_ratio:.2f}x)"}


def check_multitarget(task_dir: Path, ans: dict) -> dict:
    """Multitarget activity: gold says active/inactive at 1uM threshold per receptor.
    Sub-noise if best EC50 at the screened receptor is in [300nM, 3uM] (within 3x of threshold)."""
    gold = ans.get("gold", {})
    # screened_families is now hidden from agent but still in answer YAML / outcome
    outcome = ans.get("outcome_definition", "")
    csv_path = task_dir / "peptide_sequence.csv"
    if not csv_path.exists():
        return {"signal": "review", "note": "no peptide_sequence.csv"}
    rows = list(csv.DictReader(open(csv_path)))
    if len(rows) != 1:
        return {"signal": "review", "note": f"expected 1 peptide, got {len(rows)}"}
    peptide_id = rows[0]["peptide_id"]
    notes = []
    margins = []
    for family, call in gold.items():
        receptors = _family_receptors(family)
        ec = best_ec50(peptide_id, receptors)
        if ec == float("inf"):
            notes.append(f"{family}={call}(no data)")
            continue
        # active = best ec50 ≤ 1000 nM
        if call == "active":
            margin_log = math.log10(1000 / ec) if ec > 0 else float("inf")
        else:
            margin_log = math.log10(ec / 1000) if ec > 0 else float("inf")
        margins.append(margin_log)
        notes.append(f"{family}={call} (best {ec:.1f}nM, margin {margin_log:.2f} log)")
    if not margins:
        return {"signal": "review", "note": "; ".join(notes) or "no measurements"}
    min_margin = min(margins)
    # threshold: <0.5 log = within ~3x of 1uM cutoff = noisy
    if min_margin < 0.3:  # within ~2x
        sig = "sub_noise"
    elif min_margin < 0.5:  # within ~3x
        sig = "noisy"
    else:
        sig = "clean"
    return {"signal": sig, "note": "; ".join(notes)}


def check_prioritization(task_dir: Path, ans: dict) -> dict:
    """Prioritization tasks: in vivo. Sub-noise if NO arm reaches p<0.05 with direction=reduced."""
    # Load significance CSV once
    rows = _INVIVO_SIG
    cands_path = task_dir / "candidates.csv"
    if not cands_path.exists():
        # different shape — peptide ranking; defer
        return check_ranking(task_dir, ans)
    cands = list(csv.DictReader(open(cands_path)))
    cand_compounds = {c.get("compound", "") for c in cands}
    # window from task id (last digit segment)
    window_hours = None
    parts = task_dir.name.split("-")
    try:
        window_hours = int(parts[-1])
    except (ValueError, IndexError):
        pass
    if window_hours is None:
        return {"signal": "review", "note": "could not infer window"}

    sig_arms = 0
    for r in rows:
        if r["metric"] != "sleep_time":
            continue
        try:
            w = int(r["window_hours"])
        except (ValueError, KeyError):
            continue
        if w != window_hours:
            continue
        # group format: e.g. "NXNv12.10 100ug"
        compound = r.get("group", "").split()[0]
        if compound not in cand_compounds:
            continue
        if r.get("significant", "").lower() == "true" and r.get("direction") == "reduced":
            sig_arms += 1
    note = f"window={window_hours}h, candidates with sig reduced arm={sig_arms}"
    if sig_arms == 0:
        return {"signal": "sub_noise", "note": note}
    return {"signal": "clean" if sig_arms >= 1 else "noisy", "note": note}


def check_hit_prediction(task_dir: Path, ans: dict) -> dict:
    """Hit prediction tasks: too varied to mechanically check from CSV alone. Default REVIEW."""
    return {"signal": "review", "note": "hit_prediction needs per-task evidence check"}


def check_next_experiment_singleton(task_dir: Path, ans: dict) -> dict:
    """Decision-theoretic next-experiment tasks (artifact, cross-family, exposure).
    Already validated PROMOTE in wave 1; keep."""
    return {"signal": "clean", "note": "decision-theoretic, validated"}


# ---- family/receptor helpers ----

def _infer_family(task_id: str) -> str:
    for f in ("nps", "oxn", "mch"):
        if f"-{f}-" in task_id or task_id.endswith(f"-{f}"):
            return f.upper()
    return ""


def _family_receptors(family: str):
    return {
        "NPS": ("hNPSR1 Asn107", "hNPSR1 Ile107", "mNPSR1"),
        "OXN": ("OX1R", "OX2R"),
        "MCH": ("MCHR1", "MCHR2"),
    }.get(family.upper())


# ---- dispatch ----

_INVIVO_SIG = list(csv.DictReader(open(INVIVO_SIG))) if INVIVO_SIG.exists() else []


def audit_task(task_dir: Path) -> dict:
    task_yaml = task_dir / "task.yaml"
    ans_yaml = ANSWERS / f"{task_dir.name}.yaml"
    if not task_yaml.exists():
        return {"task_id": task_dir.name, "signal": "review", "note": "no task.yaml"}
    if not ans_yaml.exists():
        return {"task_id": task_dir.name, "signal": "review", "note": "no answer YAML"}
    task = yaml.safe_load(open(task_yaml))
    ans = yaml.safe_load(open(ans_yaml))
    task_type = task.get("task_type", "unknown")

    # Dispatch by task family rather than just task_type, since pairwise/ranking share next_experiment
    name = task_dir.name
    if name.startswith("pilot-peptide-pairwise-sequence-"):
        result = check_pairwise(task_dir, ans)
    elif name.startswith("pilot-peptide-ranking-sequence-"):
        result = check_ranking(task_dir, ans)
    elif name.startswith("pilot-peptide-multitarget-sequence-"):
        result = check_multitarget(task_dir, ans)
    elif name.startswith("pilot-prioritization-"):
        result = check_prioritization(task_dir, ans)
    elif name.startswith("pilot-hit-prediction"):
        result = check_hit_prediction(task_dir, ans)
    elif name.startswith("pilot-next-experiment-"):
        result = check_next_experiment_singleton(task_dir, ans)
    elif name.startswith("cb-"):
        # already curated; default keep
        result = {"signal": "clean", "note": "curated cb-* task"}
    else:
        result = {"signal": "review", "note": f"unknown family for {name}"}

    return {
        "task_id": name,
        "task_type": task_type,
        "family": name.rsplit("-", 1)[0] if name.split("-")[-1].isdigit() else name,
        **result,
    }


def main():
    rows = []
    for task_dir in sorted(TASKS.iterdir()):
        if not task_dir.is_dir():
            continue
        rows.append(audit_task(task_dir))

    by_signal = defaultdict(list)
    for r in rows:
        by_signal[r["signal"]].append(r)

    print(f"\n{'='*100}")
    print(f"SIGNAL QUALITY AUDIT — {len(rows)} tasks")
    print(f"{'='*100}\n")
    for sig in ("sub_noise", "noisy", "clean", "review"):
        print(f"\n--- {sig.upper()} ({len(by_signal[sig])}) ---")
        for r in by_signal[sig]:
            print(f"  {r['task_id']:60s}  {r['note']}")

    print(f"\n{'='*100}")
    print(f"SUMMARY: {len(by_signal['sub_noise'])} sub_noise (DISCARD), "
          f"{len(by_signal['noisy'])} noisy (review), "
          f"{len(by_signal['clean'])} clean (KEEP), "
          f"{len(by_signal['review'])} need manual review")
    print(f"{'='*100}\n")


if __name__ == "__main__":
    main()
