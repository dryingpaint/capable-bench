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

    problems: list[dict[str, Any]] = []
    generated: list[str] = []

    builders = [
        _build_candidate_prioritization,
        _build_hit_prediction,
        _build_next_experiment,
        _build_failure_diagnosis,
        _build_mechanistic_hypothesis,
        _build_structure_activity_reasoning,
        _build_assay_triage,
        _build_foundation_model_triage,
        _build_model_disagreement_analysis,
        _build_drug_discovery_program,
        _build_peptide_pairwise_sequence,
        _build_peptide_ranking_sequence,
    ]
    context = {
        "tasks_dir": tasks_dir,
        "answers_dir": answers_dir,
        "peptides": peptides,
        "peptide_by_id": peptide_by_id,
        "assay_summary": assay_summary,
        "invivo_rows": invivo_rows,
        "qc": qc,
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
    if answer_yaml.get("label_status") == "expert_rubric" and "rubric" in answer_yaml:
        answer_yaml.setdefault("auto_score_cap", 0.3)
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


def _build_hit_prediction(context: dict[str, Any], problems: list[dict[str, Any]]) -> list[str]:
    rows = [r for r in context["invivo_rows"] if not str(r["peptide_id"]).startswith("UNMAPPED")]
    rows = sorted(rows, key=lambda r: (r["study_name"], r["window_hours"], r["group"]))[:24]
    task_ids = []
    for index, outcome in enumerate(rows, start=1):
        peptide_id = outcome["peptide_id"]
        summary = context["assay_summary"].get(peptide_id, {"peptide_id": peptide_id})
        visible = [
            {
                "peptide_id": peptide_id,
                "compound": summary.get("compound", outcome["compound"]),
                "dose": outcome["dose"],
                "metric": outcome["metric"],
                "window_hours": outcome["window_hours"],
                "median_ec50_nm": summary.get("median_ec50_nm", ""),
                "best_ec50_nm": summary.get("best_ec50_nm", ""),
                "assays": summary.get("assays", ""),
                "receptors": summary.get("receptors", ""),
                "assay_records": summary.get("assay_records", ""),
            }
        ]
        task_id = f"pilot-hit-prediction-{index:03d}"
        gold_label = "active" if str(outcome["significant"]).lower() == "true" else "inactive"
        _write_task(
            task_id=task_id,
            task_type="hit_prediction",
            prompt=f"""
# Hit Prediction

Predict whether the candidate in `candidate_context.csv` will show a significant
in vivo effect for the specified endpoint and time window.

Return `answer.json` with `prediction` set to `active` or `inactive`, plus
confidence, rationale, effect direction, and main risk.
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
            data_files={"candidate_context.csv": (visible, list(visible[0]))},
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


def _build_failure_diagnosis(context: dict[str, Any], problems: list[dict[str, Any]]) -> list[str]:
    rejected = [r for r in context["qc"] if r.get("status") == "REJECT"]
    if not rejected:
        return []
    task_ids = []
    for index, row in enumerate(rejected[:6], start=1):
        task_id = f"pilot-failure-diagnosis-qc-{index:03d}"
        visible = [
            {
                k: row.get(k, "")
                for k in [
                    "location",
                    "date",
                    "receptor",
                    "assay",
                    "rows_total",
                    "rows_promoted",
                    "reference",
                    "ref_ec50_nm",
                ]
            }
        ]
        _write_task(
            task_id=task_id,
            task_type="failure_diagnosis",
            prompt="""
# Failure Diagnosis

`qc_context.csv` contains a failed assay import/promotion event. Diagnose the
most likely reason this evidence should not be used for candidate selection and
propose a falsifying or corrective action.

Return `answer.json` with `primary_hypothesis`, `supporting_evidence`,
`alternative_hypotheses`, `falsifying_experiment`, and `uncertainty`.
""",
            task_yaml={
                "capability_targets": ["mechanistic_reasoning", "experiment_planning"],
                "evidence_layers": ["in_vitro"],
                "label_status": "expert_rubric",
            },
            answer_yaml={
                "id": task_id,
                "task_type": "failure_diagnosis",
                "label_status": "expert_rubric",
                "rubric": {
                    "required_concepts": [
                        {
                            "id": "failed_source_trace",
                            "weight": 2,
                            "any_terms": ["raw", "source", "fit", "file"],
                        },
                        {
                            "id": "do_not_use",
                            "weight": 1,
                            "any_terms": ["do not use", "exclude", "not use", "reject"],
                        },
                        {
                            "id": "corrective_action",
                            "weight": 1,
                            "any_terms": ["reprocess", "repeat", "trace", "recover"],
                        },
                    ],
                    "forbidden_concepts": [
                        {
                            "id": "biological_failure_only",
                            "any_terms": ["loss of potency proves", "receptor biology proves"],
                        },
                    ],
                },
            },
            data_files={"qc_context.csv": (visible, list(visible[0]))},
            context=context,
            problems=problems,
            question="Diagnose why a failed assay evidence item should not drive a decision.",
            answer_rubric="Rubric concept coverage for source traceability, exclusion, and corrective action.",
            capability_targets=["mechanistic_reasoning", "experiment_planning"],
            evidence_layers=["in_vitro"],
            difficulty="easy",
            scoring_mode="rubric",
        )
        task_ids.append(task_id)
    return task_ids


def _build_mechanistic_hypothesis(context: dict[str, Any], problems: list[dict[str, Any]]) -> list[str]:
    nps = [
        summary
        for summary in context["assay_summary"].values()
        if summary.get("receptor_family") == "NPS" and "OX2R" in str(summary.get("receptors", ""))
    ][:8]
    if not nps:
        return []
    task_id = "pilot-mechanistic-hypothesis-cross-family-001"
    fields = [
        "peptide_id",
        "compound",
        "receptor_family",
        "receptors",
        "assays",
        "median_ec50_nm",
        "best_ec50_nm",
        "assay_records",
        "notes",
    ]
    rows = [{k: r.get(k, "") for k in fields} for r in nps]
    _write_task(
        task_id=task_id,
        task_type="mechanistic_hypothesis",
        prompt="""
# Mechanistic Hypothesis

The candidates in `cross_family_panel.csv` were designed in one receptor-family
program but have assay records across multiple receptors. Generate a mechanistic
hypothesis for how cross-family activity could arise, what evidence supports or
weakens it, and the fastest experiment to falsify it.

Return `answer.json` with `primary_hypothesis`, `supporting_evidence`,
`alternative_hypotheses`, `falsifying_experiment`, and `uncertainty`.
""",
        task_yaml={
            "capability_targets": ["mechanistic_reasoning", "hypothesis_generation"],
            "evidence_layers": ["identity", "in_vitro"],
            "label_status": "expert_rubric",
        },
        answer_yaml={
            "id": task_id,
            "task_type": "mechanistic_hypothesis",
            "label_status": "expert_rubric",
            "rubric": {
                "required_concepts": [
                    {"id": "cross_family", "weight": 2, "any_terms": ["cross-family", "multiple receptors", "ox2r", "npsr"]},
                    {"id": "assay_context", "weight": 1, "any_terms": ["assay", "cell line", "pathway", "coupling"]},
                    {
                        "id": "specific_candidate",
                        "weight": 2,
                        "any_terms": sorted({row["compound"] for row in rows if row.get("compound")}),
                    },
                    {"id": "falsifiable", "weight": 1, "any_terms": ["falsify", "test", "counter", "orthogonal"]},
                    {"id": "uncertainty", "weight": 1, "any_terms": ["uncertain", "artifact", "alternative", "limited"]},
                ],
                "forbidden_concepts": [
                    {"id": "overclaim", "any_terms": ["proves clinical efficacy", "guarantees in vivo"]},
                ],
            },
        },
        data_files={"cross_family_panel.csv": (rows, fields)},
        context=context,
        problems=problems,
        question="Generate a mechanistic hypothesis for cross-family activity.",
        answer_rubric="Rubric concept coverage for cross-family mechanism, assay context, falsifiability, and uncertainty.",
        capability_targets=["mechanistic_reasoning", "hypothesis_generation"],
        evidence_layers=["identity", "in_vitro"],
        difficulty="hard",
        scoring_mode="rubric",
    )
    return [task_id]


def _build_structure_activity_reasoning(context: dict[str, Any], problems: list[dict[str, Any]]) -> list[str]:
    task_ids = []
    peptide_by_id = context["peptide_by_id"]
    for family in ["NPS", "OXN", "MCH"]:
        candidates = [
            summary
            for summary in context["assay_summary"].values()
            if summary.get("receptor_family") == family and summary.get("best_ec50_nm") != ""
        ]
        candidates = sorted(
            candidates,
            key=lambda row: (
                float(row.get("best_ec50_nm") or 1e9),
                -int(row.get("assay_records") or 0),
            ),
        )[:10]
        if len(candidates) < 4:
            continue
        fields = [
            "peptide_id",
            "compound",
            "modification",
            "receptor_family",
            "receptors",
            "assays",
            "median_ec50_nm",
            "best_ec50_nm",
            "median_emax_pct",
            "assay_records",
            "notes",
        ]
        rows = []
        for candidate in candidates:
            peptide = peptide_by_id.get(candidate["peptide_id"], {})
            rows.append(
                {
                    **{k: candidate.get(k, "") for k in fields},
                    "modification": peptide.get("modification", ""),
                }
            )
        task_id = f"pilot-sar-{_slug(family)}-001"
        _write_task(
            task_id=task_id,
            task_type="structure_activity_reasoning",
            prompt=f"""
# Structure-Activity Reasoning

`sar_panel.csv` contains a {family} program panel with sequence or chemistry
modifications and assay summaries. Identify the most plausible structure-activity
hypotheses, nominate the next design move, and state what experiment would
falsify your interpretation.

Return `answer.json` with `primary_hypothesis`, `supporting_evidence`,
`alternative_hypotheses`, `falsifying_experiment`, and `uncertainty`.
""",
            task_yaml={
                "capability_targets": ["mechanistic_reasoning", "hypothesis_generation"],
                "evidence_layers": ["identity", "in_vitro"],
                "label_status": "expert_rubric",
            },
            answer_yaml={
                "id": task_id,
                "task_type": "structure_activity_reasoning",
                "label_status": "expert_rubric",
                "rubric": {
                    "required_concepts": [
                        {"id": "sar", "weight": 2, "any_terms": ["structure-activity", "sar", "modification", "substitution"]},
                        {"id": "potency_efficacy", "weight": 2, "any_terms": ["potency", "ec50", "efficacy", "emax"]},
                        {
                            "id": "specific_candidate",
                            "weight": 2,
                            "any_terms": sorted({row["compound"] for row in rows if row.get("compound")}),
                        },
                        {"id": "design_move", "weight": 1, "any_terms": ["next design", "design", "analog", "optimize"]},
                        {"id": "falsifiable", "weight": 1, "any_terms": ["falsify", "test", "synthesize", "assay"]},
                    ],
                    "forbidden_concepts": [
                        {"id": "single_metric_overclaim", "any_terms": ["ec50 alone proves", "guarantees in vivo"]},
                    ],
                },
            },
            data_files={"sar_panel.csv": (rows, fields)},
            context=context,
            problems=problems,
            question="Infer SAR and propose the next design cycle.",
            answer_rubric="Rubric concept coverage for SAR, potency/efficacy, design, and falsifiability.",
            capability_targets=["mechanistic_reasoning", "hypothesis_generation"],
            evidence_layers=["identity", "in_vitro"],
            difficulty="hard",
            scoring_mode="rubric",
        )
        task_ids.append(task_id)
    return task_ids


def _build_assay_triage(context: dict[str, Any], problems: list[dict[str, Any]]) -> list[str]:
    qc_rows = context["qc"][:12]
    if not qc_rows:
        return []
    fields = [
        "status",
        "location",
        "date",
        "receptor",
        "assay",
        "raw_file",
        "rows_total",
        "rows_promoted",
        "reference",
        "ref_ec50_nm",
        "reason",
    ]
    task_id = "pilot-assay-triage-001"
    _write_task(
        task_id=task_id,
        task_type="assay_triage",
        prompt="""
# Assay Triage

`plate_qc_context.csv` contains recent assay QC records. Decide which evidence
should be trusted for candidate decisions, which should be excluded or repeated,
and how to prevent the same failure mode in future task curation.

Return `answer.json` with `primary_hypothesis`, `supporting_evidence`,
`alternative_hypotheses`, `falsifying_experiment`, and `uncertainty`.
""",
        task_yaml={
            "capability_targets": ["experiment_planning", "mechanistic_reasoning"],
            "evidence_layers": ["in_vitro"],
            "label_status": "expert_rubric",
        },
        answer_yaml={
            "id": task_id,
            "task_type": "assay_triage",
            "label_status": "expert_rubric",
            "rubric": {
                "required_concepts": [
                    {"id": "qc_status", "weight": 2, "any_terms": ["qc", "pass", "reject", "promoted"]},
                    {"id": "exclude_repeat", "weight": 2, "any_terms": ["exclude", "repeat", "reprocess", "not use"]},
                    {"id": "controls", "weight": 1, "any_terms": ["reference", "positive control", "plate", "raw"]},
                    {"id": "curation", "weight": 1, "any_terms": ["curation", "leakage", "task", "data"]},
                ],
                "forbidden_concepts": [
                    {"id": "blind_trust", "any_terms": ["trust all", "ignore qc"]},
                ],
            },
        },
        data_files={"plate_qc_context.csv": (qc_rows, fields)},
        context=context,
        problems=problems,
        question="Triage assay evidence for benchmark curation and scientific decisions.",
        answer_rubric="Rubric concept coverage for QC status, repeat/exclude logic, controls, and curation.",
        capability_targets=["experiment_planning", "mechanistic_reasoning"],
        evidence_layers=["in_vitro"],
        difficulty="medium",
        scoring_mode="rubric",
    )
    return [task_id]


def _build_foundation_model_triage(context: dict[str, Any], problems: list[dict[str, Any]]) -> list[str]:
    invivo = [r for r in context["invivo_rows"] if not str(r["peptide_id"]).startswith("UNMAPPED")][:6]
    if len(invivo) < 3:
        return []
    task_ids = []
    for scenario_index, scenario in enumerate(
        [
            ("optimistic_function", "high model function scores conflict with mixed experimental potency"),
            ("developability_risk", "developability risk may dominate nominal functional predictions"),
            ("cluster_generalization", "embedding clusters may not generalize across receptor and assay context"),
        ],
        start=1,
    ):
        rows = []
        for i, row in enumerate(invivo):
            summary = context["assay_summary"].get(row["peptide_id"], {})
            model_function_score = round(0.92 - i * 0.07 + scenario_index * 0.01, 3)
            model_developability_risk = (
                "high" if (i + scenario_index) % 3 == 0 else "medium" if i % 3 == 1 else "low"
            )
            rows.append(
                {
                    "peptide_id": row["peptide_id"],
                    "compound": row["compound"],
                    "embedding_cluster": f"cluster_{1 + ((i + scenario_index) % 3)}",
                    "model_function_score": model_function_score,
                    "model_developability_risk": model_developability_risk,
                    "visible_invitro_best_ec50_nm": summary.get("best_ec50_nm", ""),
                    "visible_assay_count": summary.get("assay_records", ""),
                }
            )
        task_id = f"pilot-foundation-model-triage-{scenario_index:03d}"
        _write_task(
            task_id=task_id,
            task_type="foundation_model_triage",
            prompt=f"""
# Foundation-Model Triage

`model_outputs.csv` contains foundation-model-style predictions joined with
visible in vitro context. The specific challenge is that {scenario[1]}. Decide
which signals are actionable, which are unreliable, and what experiment should
validate the model-assisted decision.

Return `answer.json` with `primary_hypothesis`, `supporting_evidence`,
`alternative_hypotheses`, `falsifying_experiment`, and `uncertainty`.
""",
            task_yaml={
                "capability_targets": ["model_augmented_discovery", "mechanistic_reasoning"],
                "evidence_layers": ["identity", "in_vitro", "model_outputs"],
                "label_status": "expert_rubric",
            },
            answer_yaml={
                "id": task_id,
                "task_type": "foundation_model_triage",
                "label_status": "expert_rubric",
                "rubric": {
                    "required_concepts": [
                        {
                            "id": "model_not_truth",
                            "weight": 2,
                            "any_terms": ["not ground truth", "validate", "prediction", "model"],
                        },
                        {
                            "id": "integrate_experiment",
                            "weight": 2,
                            "any_terms": ["in vitro", "in vivo", "assay", "experimental"],
                        },
                        {
                            "id": "specific_candidate",
                            "weight": 2,
                            "any_terms": sorted({row["compound"] for row in rows if row.get("compound")}),
                        },
                        {
                            "id": "developability",
                            "weight": 1,
                            "any_terms": ["developability", "risk", "stability", "exposure"],
                        },
                        {"id": "falsifying_experiment", "weight": 1, "any_terms": ["falsify", "validate", "test"]},
                    ],
                    "forbidden_concepts": [
                        {
                            "id": "model_oracle",
                            "any_terms": ["model proves", "trust the model alone", "prediction is sufficient"],
                        },
                    ],
                },
            },
            data_files={"model_outputs.csv": (rows, list(rows[0]))},
            context=context,
            problems=problems,
            question="Use and critique foundation-model-style outputs in a drug discovery decision.",
            answer_rubric="Rubric concept coverage for model skepticism, data integration, developability, and validation.",
            capability_targets=["model_augmented_discovery", "mechanistic_reasoning"],
            evidence_layers=["identity", "in_vitro", "model_outputs"],
            difficulty="hard",
            scoring_mode="rubric",
        )
        task_ids.append(task_id)
    return task_ids


def _build_model_disagreement_analysis(context: dict[str, Any], problems: list[dict[str, Any]]) -> list[str]:
    invivo = [r for r in context["invivo_rows"] if not str(r["peptide_id"]).startswith("UNMAPPED")][:8]
    if len(invivo) < 4:
        return []
    rows = []
    for index, row in enumerate(invivo):
        summary = context["assay_summary"].get(row["peptide_id"], {})
        model_rank = index + 1
        experimental_rank = len(invivo) - index
        rows.append(
            {
                "peptide_id": row["peptide_id"],
                "compound": row["compound"],
                "model_rank": model_rank,
                "experimental_rank_proxy": experimental_rank,
                "model_function_score": round(0.95 - index * 0.06, 3),
                "visible_best_ec50_nm": summary.get("best_ec50_nm", ""),
                "visible_assay_count": summary.get("assay_records", ""),
                "visible_endpoint": row["metric"],
                "visible_window_hours": row["window_hours"],
            }
        )
    task_id = "pilot-model-disagreement-analysis-001"
    _write_task(
        task_id=task_id,
        task_type="model_disagreement_analysis",
        prompt="""
# Model Disagreement Analysis

`model_disagreement.csv` intentionally contains disagreement between a
foundation-model rank and visible experimental context. Explain how you would
resolve the disagreement and what evidence should dominate the next decision.

Return `answer.json` with `primary_hypothesis`, `supporting_evidence`,
`alternative_hypotheses`, `falsifying_experiment`, and `uncertainty`.
""",
        task_yaml={
            "capability_targets": ["model_augmented_discovery", "experiment_planning"],
            "evidence_layers": ["identity", "in_vitro", "in_vivo", "model_outputs"],
            "label_status": "expert_rubric",
        },
        answer_yaml={
            "id": task_id,
            "task_type": "model_disagreement_analysis",
            "label_status": "expert_rubric",
            "rubric": {
                "required_concepts": [
                    {"id": "disagreement", "weight": 2, "any_terms": ["disagreement", "discord", "conflict"]},
                    {"id": "experimental_priority", "weight": 2, "any_terms": ["experimental", "assay", "in vivo", "validate"]},
                    {
                        "id": "specific_candidate",
                        "weight": 2,
                        "any_terms": sorted({row["compound"] for row in rows if row.get("compound")}),
                    },
                    {"id": "calibration", "weight": 1, "any_terms": ["calibrate", "benchmark", "rank", "model"]},
                    {"id": "uncertainty", "weight": 1, "any_terms": ["uncertain", "risk", "artifact", "alternative"]},
                ],
                "forbidden_concepts": [
                    {"id": "oracle", "any_terms": ["model is always right", "ignore experiment"]},
                ],
            },
        },
        data_files={"model_disagreement.csv": (rows, list(rows[0]))},
        context=context,
        problems=problems,
        question="Resolve disagreement between model predictions and experimental evidence.",
        answer_rubric="Rubric concept coverage for disagreement, experimental priority, calibration, and uncertainty.",
        capability_targets=["model_augmented_discovery", "experiment_planning"],
        evidence_layers=["identity", "in_vitro", "in_vivo", "model_outputs"],
        difficulty="hard",
        scoring_mode="rubric",
    )
    return [task_id]


def _build_drug_discovery_program(context: dict[str, Any], problems: list[dict[str, Any]]) -> list[str]:
    task_ids = []
    fields = [
        "peptide_id",
        "compound",
        "receptor_family",
        "receptors",
        "assays",
        "median_ec50_nm",
        "best_ec50_nm",
        "median_emax_pct",
        "assay_records",
        "producer_count",
    ]
    for family in ["NPS", "OXN", "MCH"]:
        candidates = sorted(
            [
                r
                for r in context["assay_summary"].values()
                if r.get("receptor_family") == family and r.get("assay_records", 0)
            ],
            key=lambda r: (-(r.get("assay_records") or 0), float(r.get("best_ec50_nm") or 1e9)),
        )[:12]
        if len(candidates) < 6:
            continue
        rows = [{k: r.get(k, "") for k in fields} for r in candidates]
        task_id = f"pilot-drug-discovery-program-{_slug(family)}-001"
        _write_task(
            task_id=task_id,
            task_type="drug_discovery_program",
            prompt=f"""
# End-To-End Drug Discovery Program

Use `program_candidates.csv` to propose a compact {family} discovery plan. Your
answer should nominate a lead or lead family, explain the biological hypothesis,
define the next two experiments, set decision gates, and name the biggest risks.

Return `answer.json` with `recommendation`, `mechanistic_model`,
`experiments`, `risks`, and `next_design_cycle`.
""",
            task_yaml={
                "capability_targets": [
                    "mechanistic_reasoning",
                    "hypothesis_generation",
                    "experiment_planning",
                    "translational_decision_making",
                ],
                "evidence_layers": ["identity", "in_vitro", "decision_history"],
                "label_status": "expert_rubric",
            },
            answer_yaml={
                "id": task_id,
                "task_type": "drug_discovery_program",
                "label_status": "expert_rubric",
                "rubric": {
                    "required_concepts": [
                        {"id": "lead_nomination", "weight": 1, "any_terms": ["lead", "nominate", "advance", "candidate"]},
                        {"id": "mechanism", "weight": 2, "any_terms": ["mechanism", "receptor", "pathway", "target"]},
                        {
                            "id": "specific_candidate",
                            "weight": 2,
                            "any_terms": [row["compound"] for row in rows[:6] if row.get("compound")],
                        },
                        {"id": "experiment_plan", "weight": 2, "any_terms": ["experiment", "control", "dose", "assay"]},
                        {"id": "decision_gate", "weight": 2, "any_terms": ["decision gate", "go/no-go", "stop", "advance if"]},
                        {"id": "risk", "weight": 1, "any_terms": ["risk", "uncertainty", "liability", "artifact"]},
                    ],
                    "forbidden_concepts": [
                        {"id": "unsupported_human_claim", "any_terms": ["safe in humans", "clinically proven"]},
                    ],
                },
            },
            data_files={"program_candidates.csv": (rows, fields)},
            context=context,
            problems=problems,
            question="Create an end-to-end discovery plan from candidate evidence.",
            answer_rubric="Rubric concept coverage for lead nomination, mechanism, experiments, gates, and risk.",
            capability_targets=[
                "mechanistic_reasoning",
                "hypothesis_generation",
                "experiment_planning",
                "translational_decision_making",
            ],
            evidence_layers=["identity", "in_vitro", "decision_history"],
            difficulty="hard",
            scoring_mode="rubric",
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
    """
    peptide_by_id = context["peptide_by_id"]
    pool = []
    for pid, summary in context["assay_summary"].items():
        if summary.get("receptor_family") != family:
            continue
        ec50 = _num(summary.get("best_ec50_nm"))
        if ec50 is None or ec50 <= 0:
            continue
        if int(summary.get("assay_records") or 0) < 2:
            continue
        modification = (peptide_by_id.get(pid) or {}).get("modification", "").strip()
        if not modification or _SEQ_ANNOTATION_TOKENS.search(modification):
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
