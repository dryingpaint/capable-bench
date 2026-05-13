from __future__ import annotations

import csv
import math
import random
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

from .ingest import read_csv_dicts
from .io import ensure_dir, write_csv, write_json, write_yaml


PROBLEM_FIELDS = [
    "id",
    "task_type",
    "question",
    "answer_rubric",
    "allowed_domains",
    "human_solvable",
    "data_path",
    "capability_targets",
    "evidence_layers",
    "difficulty",
    "label_status",
    "scoring_mode",
]


def curate_pilot_tasks(
    processed_dir: Path,
    tasks_dir: Path,
    answers_dir: Path,
    *,
    clean: bool = False,
) -> dict[str, Any]:
    if clean:
        _clean_generated(tasks_dir, answers_dir)

    peptides = read_csv_dicts(processed_dir / "peptides.csv")
    assays = read_csv_dicts(processed_dir / "invitro_assays.csv")
    bars = _read_optional(processed_dir / "invivo_olden_analysis_bars.csv")
    sig = _read_optional(processed_dir / "invivo_olden_analysis_significance.csv")
    qc = _read_optional(processed_dir / "plate_qc.csv")

    peptide_by_compound = _peptide_by_compound(peptides)
    peptide_by_id = {row["peptide_id"]: row for row in peptides}
    assay_summary = _summarize_assays(assays)
    invivo_rows = _summarize_invivo(bars, sig, peptide_by_compound)
    peptide_resolutions = _load_peptide_resolutions(processed_dir)

    problems: list[dict[str, Any]] = []
    generated: list[str] = []

    builders = [
        _build_candidate_prioritization,
        _build_hit_prediction,
        _build_next_experiment,
        _build_peptide_pairwise_sequence,
        _build_peptide_ranking_sequence,
        _build_peptide_multitarget_sequence,
    ]
    context = {
        "tasks_dir": tasks_dir,
        "answers_dir": answers_dir,
        "peptides": peptides,
        "peptide_by_id": peptide_by_id,
        "assay_summary": assay_summary,
        "assays": assays,
        "invivo_rows": invivo_rows,
        "qc": qc,
        "peptide_resolutions": peptide_resolutions,
    }
    for builder in builders:
        task_ids = builder(context, problems)
        generated.extend(task_ids)

    ensure_dir(tasks_dir)
    write_csv(tasks_dir / "problems.csv", problems, PROBLEM_FIELDS)

    summary = {
        "processed_dir": str(processed_dir),
        "tasks_dir": str(tasks_dir),
        "answers_dir": str(answers_dir),
        "tasks_generated": len(generated),
        "task_ids": generated,
        "task_types": dict(sorted(_counts(p["task_type"] for p in problems).items())),
    }
    write_json(tasks_dir / "curation_summary.json", summary)
    return summary


def _clean_generated(tasks_dir: Path, answers_dir: Path) -> None:
    if tasks_dir.exists():
        for path in tasks_dir.iterdir():
            if path.name in {"README.md", ".gitkeep"}:
                continue
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
    if answers_dir.exists():
        for path in answers_dir.glob("*.yaml"):
            path.unlink()


def _read_optional(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return read_csv_dicts(path)


def _counts(values: Any) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for value in values:
        counts[str(value)] += 1
    return counts


def _num(value: Any) -> float | None:
    try:
        if value in {"", None}:
            return None
        parsed = float(value)
        if math.isnan(parsed):
            return None
        return parsed
    except (TypeError, ValueError):
        return None


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "task"


def _compound_from_group(group: str) -> str:
    group = group.strip()
    if group.lower().startswith("placebo"):
        return "placebo"
    match = re.match(r"([A-Za-z]+v?\d+(?:\.\d+)?)", group)
    if match:
        return match.group(1)
    match = re.match(r"(aMCH)", group, flags=re.IGNORECASE)
    if match:
        return "aMCH"
    return group.split()[0] if group else ""


def _peptide_by_compound(peptides: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    by_compound = {}
    for row in peptides:
        compound = row.get("compound", "")
        if compound:
            by_compound[compound.lower()] = row
    mch_reference = sorted(
        (
            row
            for row in peptides
            if row.get("receptor_family") == "MCH" and row.get("assay_count", "0").isdigit()
        ),
        key=lambda row: int(row.get("assay_count", "0")),
        reverse=True,
    )
    if mch_reference:
        by_compound.setdefault("amch", mch_reference[0])
    return by_compound


def _summarize_assays(assays: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in assays:
        grouped[row["peptide_id"]].append(row)

    summaries = {}
    for peptide_id, rows in grouped.items():
        ec50s = [_num(r.get("ec50_nm")) for r in rows]
        ec50s = [x for x in ec50s if x and x > 0]
        emaxes = [_num(r.get("emax_pct")) for r in rows]
        emaxes = [x for x in emaxes if x is not None]
        summaries[peptide_id] = {
            "peptide_id": peptide_id,
            "compound": rows[0].get("compound", ""),
            "receptor_family": _family_from_source(rows[0].get("source_sheet", "")),
            "assay_records": len(rows),
            "receptors": ";".join(sorted({r.get("receptor", "") for r in rows if r.get("receptor")})),
            "assays": ";".join(sorted({r.get("assay", "") for r in rows if r.get("assay")})),
            "median_ec50_nm": _median(ec50s),
            "best_ec50_nm": min(ec50s) if ec50s else "",
            "median_emax_pct": _median(emaxes),
            "producer_count": len({r.get("producer", "") for r in rows if r.get("producer")}),
            "latest_date": max((r.get("date", "") for r in rows), default=""),
            "notes": _join_limited([r.get("notes", "") for r in rows if r.get("notes")], 240),
        }
    return summaries


def _family_from_source(source: str) -> str:
    upper = source.upper()
    if "NPS" in upper:
        return "NPS"
    if "OXN" in upper or "OREXIN" in upper:
        return "OXN"
    if "MCH" in upper:
        return "MCH"
    return ""


def _median(values: list[float]) -> float | str:
    if not values:
        return ""
    values = sorted(values)
    mid = len(values) // 2
    if len(values) % 2:
        return round(values[mid], 4)
    return round((values[mid - 1] + values[mid]) / 2, 4)


def _join_limited(values: list[str], limit: int) -> str:
    text = " | ".join(dict.fromkeys(values))
    return text[:limit]


def _summarize_invivo(
    bars: list[dict[str, str]],
    sig: list[dict[str, str]],
    peptide_by_compound: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    sig_by_key = {
        (r.get("study_name", ""), r.get("metric", ""), r.get("window_hours", ""), r.get("group", "")): r
        for r in sig
    }
    rows = []
    for row in bars:
        group = row.get("group", "")
        compound = _compound_from_group(group)
        if compound.lower() == "placebo":
            continue
        peptide = peptide_by_compound.get(compound.lower(), {})
        key = (
            row.get("study_name", ""),
            row.get("metric", ""),
            row.get("window_hours", ""),
            group,
        )
        sig_row = sig_by_key.get(key, {})
        mean_value = _num(row.get("mean_value"))
        p_value = _num(sig_row.get("p_value"))
        rows.append(
            {
                "study_name": row.get("study_name", ""),
                "metric": row.get("metric", ""),
                "window_hours": row.get("window_hours", ""),
                "group": group,
                "compound": compound,
                "peptide_id": peptide.get("peptide_id", f"UNMAPPED-{_slug(compound).upper()}"),
                "dose": _dose_from_group(group),
                "mean_value": mean_value if mean_value is not None else "",
                "n": row.get("n", ""),
                "p_value": p_value if p_value is not None else "",
                "significant": sig_row.get("significant", ""),
                "direction": sig_row.get("direction", ""),
                "effect_score": _effect_score(mean_value, p_value, sig_row.get("significant", "")),
            }
        )
    return rows


def _dose_from_group(group: str) -> str:
    match = re.search(r"(\d+)\s*ug", group, flags=re.IGNORECASE)
    return f"{match.group(1)} ug" if match else ""


def _effect_score(mean_value: float | None, p_value: float | None, significant: str) -> float:
    if mean_value is None:
        return 0.0
    score = mean_value
    if str(significant).lower() == "true":
        score += 10.0
    if p_value is not None:
        score += max(0.0, -math.log10(max(p_value, 1e-12)))
    return round(score, 6)


def _candidate_rows(
    peptide_ids: list[str],
    assay_summary: dict[str, dict[str, Any]],
    invivo_by_peptide: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows = []
    for peptide_id in peptide_ids:
        summary = assay_summary.get(peptide_id, {"peptide_id": peptide_id})
        invivo = (invivo_by_peptide or {}).get(peptide_id, {})
        rows.append(
            {
                "peptide_id": peptide_id,
                "compound": summary.get("compound", invivo.get("compound", "")),
                "receptor_family": summary.get("receptor_family", ""),
                "assay_records": summary.get("assay_records", ""),
                "receptors": summary.get("receptors", ""),
                "assays": summary.get("assays", ""),
                "median_ec50_nm": summary.get("median_ec50_nm", ""),
                "best_ec50_nm": summary.get("best_ec50_nm", ""),
                "median_emax_pct": summary.get("median_emax_pct", ""),
                "producer_count": summary.get("producer_count", ""),
                "notes": summary.get("notes", ""),
            }
        )
    return rows


def _write_task(
    *,
    task_id: str,
    task_type: str,
    prompt: str,
    task_yaml: dict[str, Any],
    answer_yaml: dict[str, Any],
    data_files: dict[str, tuple[list[dict[str, Any]], list[str]]],
    context: dict[str, Any],
    problems: list[dict[str, Any]],
    question: str,
    answer_rubric: str,
    capability_targets: list[str],
    evidence_layers: list[str],
    difficulty: str,
    scoring_mode: str,
) -> None:
    task_dir = context["tasks_dir"] / task_id
    ensure_dir(task_dir)
    task_yaml = {
        "id": task_id,
        "task_type": task_type,
        "answer_file": "answer.json",
        **task_yaml,
        "data_files": list(data_files),
    }
    write_yaml(task_dir / "task.yaml", task_yaml)
    scoped_prompt = f"""
Safety and scope: this is a non-clinical benchmark over anonymized internal
research data. Do not provide therapeutic advice, wet-lab protocols, synthesis
instructions, or real-world dosing instructions. Answer at the scientific
reasoning, evidence integration, and decision-gate level using only the files in
this task directory.

{prompt.strip()}
"""
    (task_dir / "prompt.md").write_text(scoped_prompt.strip() + "\n", encoding="utf-8")
    for filename, (rows, fields) in data_files.items():
        write_csv(task_dir / filename, rows, fields)
    write_yaml(context["answers_dir"] / f"{task_id}.yaml", answer_yaml)
    problems.append(
        {
            "id": task_id,
            "task_type": task_type,
            "question": question,
            "answer_rubric": answer_rubric,
            "allowed_domains": "",
            "human_solvable": "true",
            "data_path": task_id,
            "capability_targets": ";".join(capability_targets),
            "evidence_layers": ";".join(evidence_layers),
            "difficulty": difficulty,
            "label_status": answer_yaml.get("label_status", ""),
            "scoring_mode": scoring_mode,
        }
    )


def _build_candidate_prioritization(context: dict[str, Any], problems: list[dict[str, Any]]) -> list[str]:
    invivo = [r for r in context["invivo_rows"] if not str(r["peptide_id"]).startswith("UNMAPPED")]
    if len(invivo) < 3:
        return []
    by_window: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in invivo:
        by_window[(row["study_name"], row["metric"], row["window_hours"])].append(row)

    task_ids = []
    for index, ((study_name, metric, window), rows_for_window) in enumerate(
        sorted(by_window.items()), start=1
    ):
        unique = {}
        for row in sorted(rows_for_window, key=lambda r: r["effect_score"], reverse=True):
            unique.setdefault(row["peptide_id"], dict(row))
        if len(unique) < 3:
            continue
        gold = list(unique)
        family = context["assay_summary"].get(gold[0], {}).get("receptor_family", "")
        same_family = [
            pid
            for pid, summary in context["assay_summary"].items()
            if summary.get("receptor_family") == family and pid not in unique
        ]
        selected = (gold + same_family[: max(0, 8 - len(gold))])[:8]
        rows = _candidate_rows(selected, context["assay_summary"], unique)
        task_id = f"pilot-prioritization-{_slug(family or 'mixed')}-{index:03d}"
        _write_task(
            task_id=task_id,
            task_type="candidate_prioritization",
            prompt=f"""
# Candidate Prioritization

You are advising a translational peptide program. Rank the candidates in
`candidates.csv` for advancement into the next in vivo {metric} study with a
{window}-hour observation window.

Use the in vitro pharmacology, assay breadth, receptor and assay coverage,
producer counts, and QC notes to reason about which candidates are most likely
to translate. Do not assume held-out outcome labels are visible. Write
`answer.json` with the `ranking` array and `top_3` peptide IDs.
""",
            task_yaml={
                "capability_targets": ["translational_decision_making", "mechanistic_reasoning"],
                "evidence_layers": ["identity", "in_vitro", "in_vivo"],
                "label_status": "experimental_ground_truth",
                "top_k": 3,
                "heldout_metric": metric,
                "heldout_window_hours": window,
            },
            answer_yaml={
                "id": task_id,
                "task_type": "candidate_prioritization",
                "label_status": "experimental_ground_truth",
                "top_k": 3,
                "gold_ranking": gold,
                "gold_top_3": gold[:3],
                "outcome_definition": (
                    f"{metric} effect_score from held-out in vivo analysis exports, "
                    f"window_hours={window}"
                ),
            },
            data_files={"candidates.csv": (rows, list(rows[0]))},
            context=context,
            problems=problems,
            question="Rank candidates for translational advancement.",
            answer_rubric="Precision/NDCG against held-out in vivo effect ranking.",
            capability_targets=["translational_decision_making", "mechanistic_reasoning"],
            evidence_layers=["identity", "in_vitro", "in_vivo"],
            difficulty="hard",
            scoring_mode="ranking",
        )
        task_ids.append(task_id)
    return task_ids


_HIT_PREDICTION_ASSAYS = [
    ("Ca2+", "ca2"),
    ("IP-1", "ip1"),
    ("b-Arrestin", "arrestin"),
    ("cAMP", "camp"),
]
_HIT_PREDICTION_FIELDS = [
    "peptide_id", "modification", "receptors",
    "dose", "metric", "window_hours",
    *(f"ec50_{key}_nm" for _, key in _HIT_PREDICTION_ASSAYS),
    *(f"emax_{key}_pct" for _, key in _HIT_PREDICTION_ASSAYS),
]


def _peptide_per_assay_stats(
    assays: list[dict[str, str]],
) -> dict[str, dict[str, dict[str, float]]]:
    """Per-(peptide_id, assay) median EC50 and median Emax from raw records."""
    by_key: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(
        lambda: {"ec50": [], "emax": []}
    )
    for r in assays:
        pid = (r.get("peptide_id") or "").strip()
        assay = (r.get("assay") or "").strip()
        if not pid or not assay:
            continue
        ec50 = _num(r.get("ec50_nm"))
        emax = _num(r.get("emax_pct"))
        if ec50 is not None and ec50 > 0:
            by_key[(pid, assay)]["ec50"].append(ec50)
        if emax is not None:
            by_key[(pid, assay)]["emax"].append(emax)
    out: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    for (pid, assay), bins in by_key.items():
        entry = {"n": max(len(bins["ec50"]), len(bins["emax"]))}
        if bins["ec50"]:
            entry["ec50_med_nm"] = round(sorted(bins["ec50"])[len(bins["ec50"]) // 2], 4)
        if bins["emax"]:
            entry["emax_med_pct"] = round(sorted(bins["emax"])[len(bins["emax"]) // 2], 2)
        out[pid][assay] = entry
    return out


def _build_hit_prediction(context: dict[str, Any], problems: list[dict[str, Any]]) -> list[str]:
    rows = [r for r in context["invivo_rows"] if not str(r["peptide_id"]).startswith("UNMAPPED")]
    rows = sorted(rows, key=lambda r: (r["study_name"], r["window_hours"], r["group"]))[:24]
    per_assay = _peptide_per_assay_stats(context.get("assays") or [])
    peptide_by_id = context["peptide_by_id"]
    task_ids = []
    fields = _HIT_PREDICTION_FIELDS
    for index, outcome in enumerate(rows, start=1):
        peptide_id = outcome["peptide_id"]
        summary = context["assay_summary"].get(peptide_id, {"peptide_id": peptide_id})
        meta = peptide_by_id.get(peptide_id) or {}
        stats = per_assay.get(peptide_id, {})
        row = {
            "peptide_id": peptide_id,
            "modification": meta.get("modification", "").strip(),
            "receptors": summary.get("receptors", ""),
            "dose": outcome["dose"],
            "metric": outcome["metric"],
            "window_hours": outcome["window_hours"],
        }
        for assay_label, key in _HIT_PREDICTION_ASSAYS:
            entry = stats.get(assay_label, {})
            row[f"ec50_{key}_nm"] = entry.get("ec50_med_nm", "")
            row[f"emax_{key}_pct"] = entry.get("emax_med_pct", "")
        visible = [row]
        task_id = f"pilot-hit-prediction-{index:03d}"
        gold_label = "active" if str(outcome["significant"]).lower() == "true" else "inactive"
        _write_task(
            task_id=task_id,
            task_type="hit_prediction",
            prompt=f"""
# Hit Prediction

`candidate_context.csv` describes one anonymized peptide and one in vivo
experimental condition (dose, endpoint, time window). The visible columns are:

- `peptide_id`, `modification` (sequence + chemistry), `receptors` (target panel).
- `dose`, `metric`, `window_hours` (the experimental condition).
- `ec50_<assay>_nm` and `emax_<assay>_pct` for each functional readout
  (Ca²⁺, IP-1, β-arrestin, cAMP). Empty cells indicate the assay was not run.

Predict whether the peptide will produce a **significant** in vivo effect at
the specified endpoint and time window. Integrate the modification chemistry
(PK liabilities, lipidation, non-natural residues), the per-assay pharmacology
(potency, efficacy, biased agonism across G-protein vs arrestin pathways), and
the dose / window. The compound code is intentionally withheld.

Return `answer.json` with `prediction` set to `active` or `inactive`, plus
`confidence`, `rationale`, `effect_direction`, and `main_risk`.
""",
            task_yaml={
                "capability_targets": ["translational_decision_making"],
                "evidence_layers": ["identity", "in_vitro", "in_vivo"],
                "label_status": "experimental_ground_truth",
            },
            answer_yaml={
                "id": task_id,
                "task_type": "hit_prediction",
                "label_status": "experimental_ground_truth",
                "gold_label": gold_label,
                "accepted_labels": [gold_label],
                "outcome_definition": "significant=True in held-out in vivo analysis_significance row",
            },
            data_files={"candidate_context.csv": (visible, fields)},
            context=context,
            problems=problems,
            question="Predict active/inactive in vivo outcome.",
            answer_rubric="Exact label match against held-out significance call.",
            capability_targets=["translational_decision_making"],
            evidence_layers=["identity", "in_vitro", "in_vivo"],
            difficulty="hard",
            scoring_mode="label",
        )
        task_ids.append(task_id)
    return task_ids


def _build_next_experiment(context: dict[str, Any], problems: list[dict[str, Any]]) -> list[str]:
    scenarios = [
        {
            "task_id": "pilot-next-experiment-exposure-001",
            "uncertainty": "whether the in vivo sleep-time signal is exposure-limited, dose-responsive, or a false positive",
            "gold": ["exp_002", "exp_001", "exp_003", "exp_004"],
            "options": [
                ("EXP-001", "Repeat the same endpoint with the same dose only.", 1, "replication"),
                ("EXP-002", "Run a dose-response in vivo study with exposure sampling across the endpoint window.", 3, "target coverage and dose-response translation"),
                ("EXP-003", "Add another in vitro potency plate only.", 1, "biochemical repeatability"),
                ("EXP-004", "Run a broad unrelated counterscreen before any exposure work.", 2, "off-target liability"),
            ],
        },
        {
            "task_id": "pilot-next-experiment-artifact-002",
            "uncertainty": "whether a surprising assay result is true biology or plate/import artifact",
            "gold": ["exp_003", "exp_001", "exp_004", "exp_002"],
            "options": [
                ("EXP-001", "Run a new in vivo study immediately.", 4, "translation"),
                ("EXP-002", "Trust the promoted value and start lead optimization.", 1, "none"),
                ("EXP-003", "Repeat the assay from raw source with plate QC, positive control, and orthogonal readout.", 2, "assay validity"),
                ("EXP-004", "Dock the sequence into a generic receptor structure.", 1, "structural plausibility"),
            ],
        },
        {
            "task_id": "pilot-next-experiment-cross-family-003",
            "uncertainty": "whether cross-family activity reflects receptor pharmacology or nonspecific assay behavior",
            "gold": ["exp_004", "exp_002", "exp_001", "exp_003"],
            "options": [
                ("EXP-001", "Advance the most potent cross-family compound to in vivo immediately.", 4, "translation"),
                ("EXP-002", "Run concentration-response curves in the same cell line only.", 1, "same-assay reproducibility"),
                ("EXP-003", "Ask a foundation model to choose the receptor without new data.", 1, "model preference"),
                ("EXP-004", "Run orthogonal pathway assays across receptor subtypes with antagonist controls.", 3, "specific receptor mechanism"),
            ],
        },
        {
            "task_id": "pilot-next-experiment-model-disagreement-004",
            "uncertainty": "whether a high foundation-model score should outweigh weak experimental potency",
            "gold": ["exp_002", "exp_004", "exp_001", "exp_003"],
            "options": [
                ("EXP-001", "Select the candidate solely from the model score.", 0, "none"),
                ("EXP-002", "Generate a focused experimental validation panel for model-high and model-low matched candidates.", 2, "model calibration"),
                ("EXP-003", "Discard all model outputs.", 0, "none"),
                ("EXP-004", "Run developability and stability assays before in vivo nomination.", 2, "developability risk"),
            ],
        },
    ]
    task_ids = []
    for scenario in scenarios:
        options = [
            {
                "option_id": option_id,
                "experiment": experiment,
                "cost_units": cost,
            }
            for option_id, experiment, cost, _uncertainty in scenario["options"]
        ]
        task_id = scenario["task_id"]
        _write_task(
            task_id=task_id,
            task_type="next_experiment",
            prompt=f"""
# Next Experiment

The candidate-prioritization packet contains promising in vitro potency but the
program needs to resolve {scenario["uncertainty"]}. Choose and rank the next
experiment from `experiment_options.csv`.

Return `answer.json` with `selected_option`, `ranked_options`, `rationale`, and
`decision_gate`.
""",
            task_yaml={
                "capability_targets": ["experiment_planning", "hypothesis_generation"],
                "evidence_layers": ["in_vitro", "in_vivo", "decision_history"],
                "label_status": "expert_utility_ranking",
            },
            answer_yaml={
                "id": task_id,
                "task_type": "next_experiment",
                "label_status": "expert_utility_ranking",
                "gold_top": [scenario["gold"][0]],
                "gold_ranking": scenario["gold"],
                "outcome_definition": "expert utility ranking for uncertainty reduction",
            },
            data_files={"experiment_options.csv": (options, list(options[0]))},
            context=context,
            problems=problems,
            question="Select the most informative next experiment.",
            answer_rubric="Mean reciprocal rank against expert utility ranking.",
            capability_targets=["experiment_planning", "hypothesis_generation"],
            evidence_layers=["in_vitro", "in_vivo", "decision_history"],
            difficulty="hard",
            scoring_mode="option_ranking",
        )
        task_ids.append(task_id)
    return task_ids


# ---------------------------------------------------------------------------
# Peptide sequence-only effectiveness tasks
# ---------------------------------------------------------------------------
#
# Both task families share the same input contract: the agent sees ONLY the
# peptide_id, the chemical modification string (sequence + modifications), and
# the receptor family. Measured potency / efficacy / record counts are hidden.
# This probes structure->activity prediction from sequence rather than CSV
# integration. The named `compound` field is intentionally excluded so the
# model cannot win by recognizing a published series name.

_SEQ_INPUT_FIELDS = ["peptide_id", "modification", "receptor_family", "receptors"]

# Words that should never appear in a real chemistry/sequence string. If any
# of these are present, the field is a free-text annotation that leaked into
# the modification column and would also leak outcome information to the
# agent. Reject those peptides from sequence-only task pools.
_SEQ_ANNOTATION_TOKENS = re.compile(
    r"\b(mice|mouse|slept|sleep|sleeping|active|inactive|potent|weak|"
    r"verified|excluded|see|note|test(?:ed)?|tbd)\b",
    re.IGNORECASE,
)


def _load_peptide_resolutions(processed_dir: Path) -> dict[str, dict[str, str]]:
    """Load the manual peptide_full_sequences.csv resolution table, if present.

    Maps peptide_id -> {full_sequence_resolved, pharmacology, confidence, parent_compound}.
    Used by the sequence-only task builders to (a) materialize delta-only
    modification strings into full sequences and (b) drop peptides whose
    pharmacology doesn't match the agonist-only task semantics.
    """
    path = processed_dir / "peptide_full_sequences.csv"
    if not path.exists():
        return {}
    out: dict[str, dict[str, str]] = {}
    import csv as _csv
    with open(path, encoding="utf-8") as f:
        for r in _csv.DictReader(f):
            pid = r.get("peptide_id", "")
            if pid:
                out[pid] = r
    return out


_AA1 = "ACDEFGHIKLMNPQRSTVWY"
_SINGLE_RUN_8 = re.compile(rf"[{_AA1}]{{8,}}")
_SINGLE_RUN_4 = re.compile(rf"[{_AA1}]{{4,}}")
_AA3 = (r"Ala|Arg|Asn|Asp|Cys|Gln|Glu|Gly|His|Ile|Leu|Lys|Met|Phe|Pro|Ser|"
        r"Thr|Trp|Tyr|Val|Sar|Nle|Aib|Hyp|Orn|Dab|Dap|hArg|hLys|hVal|hAla|"
        r"hLeu|hThr|Gua|Gla|Gba|betaAla|betaHoVal|Acpc")
_THREE_LETTER_CHAIN = re.compile(rf"(?:(?:D-)?(?:{_AA3})-){{4,}}(?:D-)?(?:{_AA3})")

# Markers that flag antagonist scaffolds (S38151 / aMCH / GPS18169) or
# multi-pharmacophore fusion peptides (MOX, NXN, NPM, etc.) - any of these
# in the raw modification string means "drop from agonist-only sequence pool"
# unless the peptide has an explicit agonist resolution.
_NON_AGONIST_MARKERS = re.compile(
    r"(^Gba-|^Gua-|"            # S38151 / GPS18169 / aMCH antagonist N-cap
    r"Ac-\(Gva\)|Ac-\(Gpr\)|"   # Bednarek 2002 ring-variant antagonist N-caps
    r"-RSGPP|-GLQGR|"           # OXN tail tacked onto MCH or NPS core (MOX, NXN)
    r"-\(AEEA\)-|-\(Ahx\)-|"    # explicit fusion linkers
    r"-GSG-|-GSGKGSG-|"         # peptide-stub fusion linkers
    r"-\(βAla\)-|-\(betaAla\)-|"# beta-alanine fusion linkers
    r"NPS×OXN|NPS x OXN)",      # explicit fusion labels (from resolved seqs)
    re.IGNORECASE,
)


def _looks_like_full_sequence(s: str) -> bool:
    """Heuristic: a string represents a full peptide sequence if it contains
    either (a) a run of >=8 consecutive single-letter amino acids,
    (b) a chain of >=5 three-letter amino acid codes joined by hyphens, or
    (c) >=3 runs of >=4 consecutive single-letter amino acids (spaced).
    Catches both single-letter (`SFRNGVGTGM...`) and three-letter
    (`Asp-Phe-Asp-Met-...`) sequence notations.
    """
    if not s:
        return False
    if _SINGLE_RUN_8.search(s):
        return True
    if _THREE_LETTER_CHAIN.search(s):
        return True
    return len(_SINGLE_RUN_4.findall(s)) >= 3


def _resolved_modification_for_seq(
    pid: str, raw_modification: str, resolutions: dict[str, dict[str, str]]
) -> str | None:
    """Return the modification string to show to the agent for sequence-only
    agonist tasks, or None if this peptide should be dropped from the pool.

    Drop rules (any of these -> drop):
      - In resolutions table with pharmacology != 'agonist' (antagonist /
        fusion / small-molecule)
      - In resolutions table with confidence == 'EXCLUDE'
      - Raw modification contains antagonist or fusion markers (Gba- / Gua-
        prefix, embedded -RSGPP-/-GLQGR-/linker tokens, etc.) AND the
        peptide isn't explicitly resolved as agonist
      - Not in resolutions table AND raw modification is empty / contains
        annotation tokens / doesn't look like a complete sequence

    Otherwise return either the resolved full sequence (if available) or
    the raw modification (already a clean full sequence).
    """
    entry = resolutions.get(pid)
    raw = (raw_modification or "").strip()

    if entry is not None:
        pharm = (entry.get("pharmacology") or "").lower()
        conf = (entry.get("confidence") or "").upper()
        if conf == "EXCLUDE":
            return None
        if pharm and pharm != "agonist":  # antagonist, fusion, small-molecule
            return None
        full_seq = entry.get("full_sequence_resolved", "").strip()
        if full_seq and not full_seq.upper().startswith("REVIEW"):
            return full_seq
        # Resolution row exists but has no usable sequence; fall through

    # Not in resolutions table (or row was empty): apply stricter raw filter
    if not raw or _SEQ_ANNOTATION_TOKENS.search(raw):
        return None
    if _NON_AGONIST_MARKERS.search(raw):
        return None
    if not _looks_like_full_sequence(raw):
        return None
    return raw

# Potency ratio buckets for pairwise difficulty stratification. The "easy"
# bin (>=30x) is a floor test; "hard" (2-5x) probes log-scale reasoning under
# assay noise; <2x is excluded because gold labels become noisy.
_PAIRWISE_BUCKETS = [
    ("hard", 2.0, 5.0),
    ("medium", 5.0, 30.0),
    ("easy", 30.0, 100.0),
    ("trivial", 100.0, float("inf")),
]


def _seq_candidate_pool(context: dict[str, Any], family: str) -> list[dict[str, Any]]:
    """Return peptides in `family` with a valid sequence and EC50, suitable for
    sequence-only prediction tasks. Filters by minimum evidence so gold labels
    are robust: >=2 assay records and a non-trivial best_ec50_nm.

    Resolution table (data/processed/peptide_full_sequences.csv) is consulted
    if present:
      - delta-only modifications are replaced by the resolved full sequence
      - non-agonist peptides (antagonist / fusion / small-molecule) are dropped
      - peptides marked EXCLUDE are dropped
    """
    peptide_by_id = context["peptide_by_id"]
    resolutions = context.get("peptide_resolutions") or {}
    pool = []
    for pid, summary in context["assay_summary"].items():
        if summary.get("receptor_family") != family:
            continue
        ec50 = _num(summary.get("best_ec50_nm"))
        if ec50 is None or ec50 <= 0:
            continue
        if int(summary.get("assay_records") or 0) < 2:
            continue
        raw_modification = (peptide_by_id.get(pid) or {}).get("modification", "")
        modification = _resolved_modification_for_seq(pid, raw_modification, resolutions)
        if modification is None:
            continue
        pool.append(
            {
                "peptide_id": pid,
                "best_ec50_nm": ec50,
                "modification": modification,
                "receptor_family": family,
                "receptors": summary.get("receptors", ""),
            }
        )
    pool.sort(key=lambda r: r["best_ec50_nm"])
    return pool


def _build_peptide_pairwise_sequence(
    context: dict[str, Any], problems: list[dict[str, Any]]
) -> list[str]:
    """For each family, sample pairwise comparisons stratified by the log-ratio
    of best_ec50_nm. Reuses the next_experiment task type so the existing option
    grader scores top-1 selection.
    """
    rng = random.Random(20260512)
    task_ids: list[str] = []
    for family in ["NPS", "OXN", "MCH"]:
        pool = _seq_candidate_pool(context, family)
        if len(pool) < 4:
            continue
        seen_pairs: set[tuple[str, str]] = set()
        items_per_bucket = 5
        for bucket_label, lo, hi in _PAIRWISE_BUCKETS:
            # Find pairs whose potency ratio falls in [lo, hi).
            candidate_pairs = []
            for i, a in enumerate(pool):
                for b in pool[i + 1 :]:
                    ratio = b["best_ec50_nm"] / a["best_ec50_nm"]
                    if lo <= ratio < hi:
                        candidate_pairs.append((a, b, ratio))
            rng.shuffle(candidate_pairs)
            taken = 0
            for a, b, ratio in candidate_pairs:
                if taken >= items_per_bucket:
                    break
                key = tuple(sorted([a["peptide_id"], b["peptide_id"]]))
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                taken += 1
                # Randomize row order so the more-potent peptide isn't always
                # first. The agent must reason, not pick row index 0.
                order = [a, b]
                rng.shuffle(order)
                rows = [{k: row.get(k, "") for k in _SEQ_INPUT_FIELDS} for row in order]
                winner_id = a["peptide_id"]  # a is more potent (lower EC50)
                task_index = len([t for t in task_ids if family.lower() in t]) + 1
                task_id = (
                    f"pilot-peptide-pairwise-sequence-{family.lower()}-"
                    f"{bucket_label}-{task_index:03d}"
                )
                _write_task(
                    task_id=task_id,
                    task_type="next_experiment",
                    prompt=f"""
# Pairwise Potency Prediction from Sequence

`peptide_sequences.csv` contains two peptides targeting the {family} receptor
family. Each row gives the anonymized peptide identifier, the chemical
modification string (sequence plus any non-standard residues, lipidation, or
backbone modifications), the receptor family, and the receptor variants on
which the peptide series is tested. **No measured potency, efficacy, or assay
counts are provided.**

Using only the sequence and chemical modifications, predict which peptide is
more potent in functional in vitro assays at this receptor (lower EC50). Write
`answer.json` with `selected_option` set to the `peptide_id` of the more
potent peptide.
""",
                    task_yaml={
                        "capability_targets": [
                            "structure_activity_reasoning",
                            "sequence_to_function_prediction",
                        ],
                        "evidence_layers": ["identity"],
                        "label_status": "experimental_ground_truth",
                        "difficulty_bucket": bucket_label,
                        "potency_ratio": round(ratio, 2),
                    },
                    answer_yaml={
                        "id": task_id,
                        "task_type": "next_experiment",
                        "label_status": "experimental_ground_truth",
                        "gold_top": [winner_id],
                        "gold_ranking": [winner_id, b["peptide_id"]],
                        "outcome_definition": (
                            "lower best_ec50_nm in held-out in vitro functional "
                            f"assays (potency ratio {round(ratio, 2)}x)"
                        ),
                    },
                    data_files={
                        "peptide_sequences.csv": (rows, _SEQ_INPUT_FIELDS),
                    },
                    context=context,
                    problems=problems,
                    question=(
                        "Predict which of two peptides is more potent given only "
                        "sequence and target."
                    ),
                    answer_rubric=(
                        "Exact match: selected_option equals the peptide_id with "
                        "lower best_ec50_nm."
                    ),
                    capability_targets=[
                        "structure_activity_reasoning",
                        "sequence_to_function_prediction",
                    ],
                    evidence_layers=["identity"],
                    difficulty=bucket_label,
                    scoring_mode="option",
                )
                task_ids.append(task_id)
    return task_ids


def _build_peptide_ranking_sequence(
    context: dict[str, Any], problems: list[dict[str, Any]]
) -> list[str]:
    """Rank N peptides by predicted potency given only sequence + target.
    Uses the candidate_prioritization task type so the existing top-k ranking
    grader scores precision@3 and NDCG@3.
    """
    rng = random.Random(20260513)
    task_ids: list[str] = []
    for family in ["NPS", "OXN", "MCH"]:
        pool = _seq_candidate_pool(context, family)
        if len(pool) < 12:
            continue
        # Sample N peptides spanning the EC50 distribution so the ordering is
        # not collapsed at one end. Take stratified samples across deciles.
        for size_label, size in [("small", 5), ("medium", 8), ("large", 12)]:
            if len(pool) < size:
                continue
            # Pick `size` peptides whose EC50 values span at least 10x to keep
            # the gold ranking robust.
            attempts = 0
            chosen: list[dict[str, Any]] = []
            while attempts < 50:
                attempts += 1
                sample = rng.sample(pool, size)
                lo = min(r["best_ec50_nm"] for r in sample)
                hi = max(r["best_ec50_nm"] for r in sample)
                if hi / lo >= 10.0:
                    chosen = sample
                    break
            if not chosen:
                continue
            ranked = sorted(chosen, key=lambda r: r["best_ec50_nm"])
            gold_ranking = [r["peptide_id"] for r in ranked]
            display = list(chosen)
            rng.shuffle(display)
            rows = [
                {k: row.get(k, "") for k in _SEQ_INPUT_FIELDS} for row in display
            ]
            task_id = (
                f"pilot-peptide-ranking-sequence-{family.lower()}-{size_label}-001"
            )
            _write_task(
                task_id=task_id,
                task_type="candidate_prioritization",
                prompt=f"""
# Potency Ranking from Sequence

`peptide_sequences.csv` lists {size} peptides targeting the {family} receptor
family. Each row provides the anonymized peptide identifier, the chemical
modification string (sequence with any non-standard residues, lipidation, or
backbone modifications), the receptor family, and the receptor variants tested.
**No measured potency, efficacy, or assay counts are provided.**

Using only the sequence and chemical modifications, rank the peptides from
most to least potent in functional in vitro assays at this receptor (most
potent = lowest EC50 first). Write `answer.json` with `ranking` as the full
ordered list of peptide_ids and `top_3` as the three peptide_ids predicted to
be most potent.
""",
                task_yaml={
                    "capability_targets": [
                        "structure_activity_reasoning",
                        "sequence_to_function_prediction",
                    ],
                    "evidence_layers": ["identity"],
                    "label_status": "experimental_ground_truth",
                    "top_k": 3,
                    "n_candidates": size,
                },
                answer_yaml={
                    "id": task_id,
                    "task_type": "candidate_prioritization",
                    "label_status": "experimental_ground_truth",
                    "top_k": 3,
                    "gold_ranking": gold_ranking,
                    "gold_top_3": gold_ranking[:3],
                    "outcome_definition": (
                        "ranking by ascending best_ec50_nm in held-out in vitro "
                        f"functional assays; sample spans {round(ranked[-1]['best_ec50_nm'] / ranked[0]['best_ec50_nm'], 1)}x"
                    ),
                },
                data_files={
                    "peptide_sequences.csv": (rows, _SEQ_INPUT_FIELDS),
                },
                context=context,
                problems=problems,
                question=(
                    f"Rank {size} peptides by predicted potency given only sequence "
                    "and target."
                ),
                answer_rubric=(
                    "Top-k precision and NDCG against ascending best_ec50_nm "
                    "ranking."
                ),
                capability_targets=[
                    "structure_activity_reasoning",
                    "sequence_to_function_prediction",
                ],
                evidence_layers=["identity"],
                difficulty=size_label,
                scoring_mode="ranking",
            )
            task_ids.append(task_id)
    return task_ids


_FAMILY_OF_RECEPTOR = {
    "NPSR1": "NPS", "hNPSR1": "NPS", "hNPSR1 Asn107": "NPS",
    "hNPSR1 Ile107": "NPS", "mNPSR1": "NPS",
    "OX1R": "OXN", "OX2R": "OXN",
    "MCHR1": "MCH", "MCHR2": "MCH",
}

_MULTITARGET_ACTIVE_NM = 1000.0  # ≤1 µM = active for multi-target panel
_MULTITARGET_PANEL = ("NPS", "OXN", "MCH")
_MULTITARGET_INPUT_FIELDS = ["peptide_id", "modification", "panel"]


def _peptide_family_potency(
    assays: list[dict[str, str]],
) -> dict[str, dict[str, float]]:
    """Aggregate min(EC50) per (peptide_id, receptor_family) across assay records.

    Only positive numeric EC50s are kept. Returns {peptide_id: {family: best_ec50_nm}};
    families absent for a peptide are not present in the inner dict.
    """
    best: dict[str, dict[str, float]] = defaultdict(dict)
    for r in assays:
        fam = _FAMILY_OF_RECEPTOR.get((r.get("receptor") or "").strip())
        if not fam:
            continue
        ec50 = _num(r.get("ec50_nm"))
        if ec50 is None or ec50 <= 0:
            continue
        pid = r.get("peptide_id") or ""
        if not pid:
            continue
        cur = best[pid].get(fam)
        if cur is None or ec50 < cur:
            best[pid][fam] = ec50
    return best


def _build_peptide_multitarget_sequence(
    context: dict[str, Any], problems: list[dict[str, Any]]
) -> list[str]:
    """Predict per-target activity (active/inactive) across the {NPS, OXN, MCH}
    panel from sequence alone. Stratified into buckets that probe selectivity
    vs polypharm reasoning, not just intra-family ranking which the existing
    pairwise/ranking tasks already cover.

    Buckets:
      - dual-active: peptide screened in 2 families, active (≤1 µM) in both.
        Tests recognition of chimeric / polypharm sequence design.
      - dual-mono-active: peptide screened in 2 families, active in only one.
        Tests selectivity reasoning — the most diagnostic case because
        the visible sequence must explain why only one target engages.
      - mono-active: peptide screened in 1 family and active there. The
        question becomes: does the model predict 'inactive' at the untested
        families based on sequence motifs? Gold for untested families is
        derived from compound-class convention (kept conservative: only
        labeled 'active' / 'inactive' for screened families; unscreened
        families are omitted from the gold so the agent isn't penalized
        for speculating about data we don't have).
    """
    rng = random.Random(20260513)
    assays = context.get("assays") or []
    peptide_by_id = context["peptide_by_id"]
    best_by_pep = _peptide_family_potency(assays)

    def _classify(pid: str) -> tuple[str, dict[str, str]]:
        fam_to_ec50 = best_by_pep.get(pid, {})
        screened = set(fam_to_ec50)
        active = {f for f, v in fam_to_ec50.items() if v <= _MULTITARGET_ACTIVE_NM}
        if len(screened) >= 2 and len(active) >= 2:
            bucket = "dual-active"
        elif len(screened) >= 2 and len(active) == 1:
            bucket = "dual-mono-active"
        elif len(screened) == 1 and len(active) == 1:
            bucket = "mono-active"
        elif len(screened) == 1 and len(active) == 0:
            bucket = "mono-inactive"
        else:
            bucket = "skip"
        gold = {f: ("active" if f in active else "inactive") for f in screened}
        return bucket, gold

    resolutions = context.get("peptide_resolutions") or {}
    candidates: dict[str, list[tuple[str, dict[str, str]]]] = defaultdict(list)
    for pid in best_by_pep:
        meta = peptide_by_id.get(pid)
        if not meta:
            continue
        raw_modification = meta.get("modification") or ""
        modification = _resolved_modification_for_seq(pid, raw_modification, resolutions)
        if modification is None:
            continue
        bucket, gold = _classify(pid)
        if bucket == "skip":
            continue
        candidates[bucket].append((pid, gold))

    targets_per_bucket = {
        "dual-active": 12,
        "dual-mono-active": 10,  # use all available if fewer than 10
        "mono-active": 15,
        "mono-inactive": 6,
    }
    task_ids: list[str] = []
    for bucket, items in candidates.items():
        rng.shuffle(items)
        take = items[: targets_per_bucket.get(bucket, 10)]
        for index, (pid, gold) in enumerate(take, start=1):
            meta = peptide_by_id[pid]
            raw_modification = meta.get("modification", "")
            modification = _resolved_modification_for_seq(pid, raw_modification, resolutions) or raw_modification.strip()
            receptors = meta.get("receptors", "")
            # The panel shown to the agent is always the full 3-family panel,
            # but only screened families are graded. The agent is told this so
            # speculating about unscreened families is harmless.
            screened = sorted(gold.keys())
            row = {
                "peptide_id": pid,
                "modification": modification,
                "panel": ";".join(_MULTITARGET_PANEL),
            }
            task_id = f"pilot-peptide-multitarget-sequence-{bucket}-{index:03d}"
            screened_str = ", ".join(screened)
            _write_task(
                task_id=task_id,
                task_type="multitarget_activity",
                prompt=f"""
# Multi-Target Activity Prediction from Sequence

`peptide_sequence.csv` contains a single peptide: its anonymized identifier,
the chemical modification string (sequence plus any non-standard residues,
lipidation, or backbone modifications), and the receptor-family panel under
consideration (`NPS`, `OXN`, `MCH`).

Using only the sequence and chemical modifications, predict whether the
peptide is **active** (best functional EC50 ≤ 1 µM) at each receptor family
in the panel. For families the lab did not screen this peptide against, the
grader ignores your prediction — so it is safe to give your best guess for
all three families.

Return `answer.json` with one top-level field per family in the panel
(`NPS`, `OXN`, `MCH`), each set to `"active"` or `"inactive"`. Include a
short `rationale` describing the sequence features that drove the call.
""",
                task_yaml={
                    "capability_targets": [
                        "structure_activity_reasoning",
                        "sequence_to_function_prediction",
                        "cross_target_selectivity",
                    ],
                    "evidence_layers": ["identity"],
                    "label_status": "experimental_ground_truth",
                    "difficulty_bucket": bucket,
                    "screened_families": screened,
                },
                answer_yaml={
                    "id": task_id,
                    "task_type": "multitarget_activity",
                    "label_status": "experimental_ground_truth",
                    "gold": gold,
                    "outcome_definition": (
                        "active = min(ec50_nm) ≤ 1000 nM across in vitro functional "
                        f"assays at that receptor family; screened families: {screened_str}"
                    ),
                },
                data_files={
                    "peptide_sequence.csv": ([row], _MULTITARGET_INPUT_FIELDS),
                },
                context=context,
                problems=problems,
                question=(
                    "Predict per-target activity (active/inactive at ≤1 µM) on the "
                    "NPS/OXN/MCH panel from sequence alone."
                ),
                answer_rubric=(
                    "Per-family exact-match accuracy over screened families only."
                ),
                capability_targets=[
                    "structure_activity_reasoning",
                    "sequence_to_function_prediction",
                    "cross_target_selectivity",
                ],
                evidence_layers=["identity"],
                difficulty=bucket,
                scoring_mode="multi_label",
            )
            task_ids.append(task_id)
    return task_ids
