"""Compute and write `effect_size` tags into every answer YAML.

Tag scheme (based on |log10(separation_ratio)|):
  noise       ratio ≤ 3×        |log10| < 0.5
  small       3× – 10×          |log10| 0.5 – 1.0
  medium      10× – 100×        |log10| 1.0 – 2.0
  large       100× – 1000×      |log10| 2.0 – 3.0
  very_large  > 1000×           |log10| > 3.0

Per-type "separation_ratio":
  pairwise    loser_EC50 / winner_EC50 at family receptors only
  ranking     EC50_at_rank_(k+1) / EC50_at_rank_k
  multitarget (best EC50 vs 1000 nM threshold) — min log-margin across all gold calls
  prioritization-nps  -log10(min p-value across reduced significant arms)
  hit_prediction      bucket from p-value or fold-change in the candidate evidence
  next_experiment singletons   "decision_theoretic"
  cb-* curated     leave existing tags / mark "curated"

The script writes `effect_size` to each `data/answers/<task>.yaml`. Idempotent.
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
ASSAYS_CSV = REPO / "data/processed/invitro_assays.csv"
INVIVO_SIG_CSV = REPO / "data/processed/invivo_olden_analysis_significance.csv"

FAMILY_RECEPTORS = {
    "NPS": ("hNPSR1 Asn107", "hNPSR1 Ile107", "mNPSR1"),
    "OXN": ("OX1R", "OX2R"),
    "MCH": ("MCHR1", "MCHR2"),
}

_ASSAYS = list(csv.DictReader(open(ASSAYS_CSV)))
_INVIVO_SIG = list(csv.DictReader(open(INVIVO_SIG_CSV))) if INVIVO_SIG_CSV.exists() else []


def best_ec50(peptide_id, receptors):
    best = float("inf")
    for r in _ASSAYS:
        if r["peptide_id"] != peptide_id: continue
        if r["receptor"] not in receptors: continue
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


def bucket_ratio(ratio):
    if ratio <= 0 or ratio == float("inf"):
        return "noise"
    log = abs(math.log10(ratio))
    if log < 0.5: return "noise"
    if log < 1.0: return "small"
    if log < 2.0: return "medium"
    if log < 3.0: return "large"
    return "very_large"


def tag_pairwise(task_dir, ans):
    family = infer_family(task_dir.name)
    if not family: return None, "no family"
    rs = FAMILY_RECEPTORS[family]
    rows = list(csv.DictReader(open(task_dir / "peptide_sequences.csv")))
    if len(rows) != 2: return None, "not 2 peptides"
    ec = {r["peptide_id"]: best_ec50(r["peptide_id"], rs) for r in rows}
    winner = (ans.get("gold_top") or [None])[0]
    if not winner or winner not in ec: return None, "no gold winner"
    loser = [p for p in ec if p != winner][0]
    we, le = ec[winner], ec[loser]
    if we == float("inf"):
        return "noise", f"winner has no family data ({winner})"
    if le == float("inf"):
        # winner has data, loser doesn't (loser is presumably inactive at family receptors)
        return "very_large", f"winner {we:.3f}nM at family; loser has no family data → effectively very_large"
    ratio = le / we
    return bucket_ratio(ratio), f"loser {le:.3f}nM / winner {we:.3f}nM = {ratio:.2f}x"


def tag_ranking(task_dir, ans):
    family = infer_family(task_dir.name)
    if not family: return None, "no family"
    rs = FAMILY_RECEPTORS[family]
    rows = list(csv.DictReader(open(task_dir / "peptide_sequences.csv")))
    ec = {r["peptide_id"]: best_ec50(r["peptide_id"], rs) for r in rows}
    top_k = ans.get("top_k", 3)
    ranking = ans.get("gold_ranking", [])
    if len(ranking) <= top_k: return "very_large", f"top_k={top_k} >= ranking size"
    rk = ec.get(ranking[top_k - 1], float("inf"))
    rk1 = ec.get(ranking[top_k], float("inf"))
    if rk == float("inf") or rk1 == float("inf"):
        return None, f"missing EC50 around rank-{top_k}/{top_k+1}"
    ratio = rk1 / rk
    return bucket_ratio(ratio), f"rank-{top_k}={rk:.3f}nM / rank-{top_k+1}={rk1:.3f}nM = {ratio:.2f}x"


def tag_multitarget(task_dir, ans):
    rows = list(csv.DictReader(open(task_dir / "peptide_sequence.csv")))
    if len(rows) != 1: return None, "not 1 peptide"
    pid = rows[0]["peptide_id"]
    gold = ans.get("gold", {})
    if not gold: return None, "no gold"
    margins = []
    notes = []
    for family, call in gold.items():
        rs = FAMILY_RECEPTORS.get(family.upper())
        if not rs:
            notes.append(f"{family}={call}(unknown family)")
            continue
        ec = best_ec50(pid, rs)
        if ec == float("inf"):
            notes.append(f"{family}={call}(no data)")
            continue
        # active = ec50 ≤ 1000 nM; effect_size = log distance from threshold
        if call == "active":
            log_margin = math.log10(1000 / ec) if ec > 0 else float("inf")
        else:
            log_margin = math.log10(ec / 1000) if ec > 0 else float("inf")
        margins.append(log_margin)
        notes.append(f"{family}={call}({ec:.1f}nM, {log_margin:+.2f} log)")
    if not margins:
        return "noise", "; ".join(notes)
    # the WEAKEST call dominates effect size (a multi-call task is only as strong as its weakest margin)
    min_margin = min(margins)
    if min_margin < 0.5: bucket = "noise"
    elif min_margin < 1.0: bucket = "small"
    elif min_margin < 2.0: bucket = "medium"
    elif min_margin < 3.0: bucket = "large"
    else: bucket = "very_large"
    return bucket, "; ".join(notes)


def tag_prioritization(task_dir, ans):
    cands_path = task_dir / "candidates.csv"
    if not cands_path.exists():
        return tag_ranking(task_dir, ans)  # peptide-ranking variant
    cands = list(csv.DictReader(open(cands_path)))
    cand_compounds = {c.get("compound", "") for c in cands}
    parts = task_dir.name.split("-")
    try:
        window_hours = int(parts[-1])
    except (ValueError, IndexError):
        return None, "no window"
    pvals = []
    for r in _INVIVO_SIG:
        if r["metric"] != "sleep_time": continue
        try:
            if int(r["window_hours"]) != window_hours: continue
        except (ValueError, KeyError): continue
        compound = r.get("group", "").split()[0]
        if compound not in cand_compounds: continue
        if r.get("direction") != "reduced": continue
        try:
            p = float(r.get("p_value", "1"))
            pvals.append(p)
        except (ValueError, TypeError): continue
    if not pvals:
        return "noise", f"window={window_hours}h, no reduced arms with p-value"
    p_min = min(pvals)
    log_p = -math.log10(p_min) if p_min > 0 else float("inf")
    if log_p < 1.0: bucket = "noise"   # p > 0.1
    elif log_p < 1.3: bucket = "small"   # 0.05 < p < 0.1
    elif log_p < 2.0: bucket = "medium"  # 0.01 < p < 0.05
    elif log_p < 3.0: bucket = "large"   # 0.001 < p < 0.01
    else: bucket = "very_large"
    return bucket, f"window={window_hours}h, best reduced p={p_min:.4f}"


def tag_hit_prediction(task_dir, ans):
    return None, "needs per-task review"


def tag_next_experiment_singleton(task_dir, ans):
    return "decision_theoretic", "compound-agnostic decision question"


def tag_cb(task_dir, ans):
    return "curated", "cb-* curated task"


def main():
    summary = defaultdict(int)
    for d in sorted(TASKS.iterdir()):
        if not d.is_dir(): continue
        name = d.name
        ans_path = ANSWERS / f"{name}.yaml"
        if not ans_path.exists(): continue
        ans = yaml.safe_load(open(ans_path))

        if name.startswith("pilot-peptide-pairwise-sequence-"):
            tag, note = tag_pairwise(d, ans)
        elif name.startswith("pilot-peptide-ranking-sequence-"):
            tag, note = tag_ranking(d, ans)
        elif name.startswith("pilot-peptide-multitarget-sequence-"):
            tag, note = tag_multitarget(d, ans)
        elif name.startswith("pilot-prioritization-"):
            tag, note = tag_prioritization(d, ans)
        elif name.startswith("pilot-hit-prediction"):
            tag, note = tag_hit_prediction(d, ans)
        elif name.startswith("pilot-next-experiment-"):
            tag, note = tag_next_experiment_singleton(d, ans)
        elif name.startswith("cb-"):
            tag, note = tag_cb(d, ans)
        else:
            tag, note = None, "unknown family"

        if tag is not None:
            ans["effect_size"] = tag
            ans["effect_size_note"] = note
            yaml.safe_dump(ans, open(ans_path, "w"), sort_keys=False, allow_unicode=False)

        summary[tag] += 1
        print(f"  [{tag or 'untagged':>20s}]  {name:60s}  {note}")

    print()
    print("=" * 100)
    print("TAG DISTRIBUTION")
    print("=" * 100)
    for tag in ("noise", "small", "medium", "large", "very_large", "decision_theoretic", "curated", None):
        print(f"  {str(tag) or 'untagged':>20s}: {summary[tag]}")


if __name__ == "__main__":
    main()
