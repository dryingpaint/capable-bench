from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .io import read_yaml, write_json


def write_baseline_answer(task_dir: Path, answer_path: Path | None = None) -> dict[str, Any]:
    metadata = read_yaml(task_dir / "task.yaml")
    task_type = metadata.get("task_type")
    answer_path = answer_path or task_dir / metadata.get("answer_file", "answer.json")

    if task_type == "candidate_prioritization":
        answer = _prioritize_by_potency(task_dir / "candidates.csv")
    elif task_type == "hit_prediction":
        answer = _predict_hit_by_potency(task_dir / "candidate_context.csv")
    elif task_type == "next_experiment":
        answer = _choose_exposure_experiment(task_dir / "experiment_options.csv")
    elif task_type in {
        "failure_diagnosis",
        "mechanistic_hypothesis",
        "experiment_plan",
        "drug_discovery_program",
        "foundation_model_triage",
        "artifact_detection",
        "structure_activity_reasoning",
        "counterfactual_biology",
        "assay_triage",
        "data_acquisition_plan",
        "rescue_strategy",
        "portfolio_tradeoff",
        "lead_optimization_loop",
        "model_disagreement_analysis",
        "generated_candidate_review",
        "functional_prediction",
    }:
        answer = _generic_scientific_answer(task_type)
    else:
        raise ValueError(f"No baseline registered for task_type={task_type!r}")

    write_json(answer_path, answer)
    return answer


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _float(value: str) -> float:
    try:
        if value == "":
            return float("inf")
        return float(value)
    except ValueError:
        return float("inf")


def _prioritize_by_potency(path: Path) -> dict[str, Any]:
    rows = _read_csv(path)
    ranked = sorted(
        rows,
        key=lambda row: (
            _float(row.get("best_ec50_nm", "")),
            _float(row.get("median_ec50_nm", "")),
            -_float(row.get("assay_records", "0")),
        ),
    )
    ranking = [
        {
            "peptide_id": row["peptide_id"],
            "rank": index,
            "confidence": 0.35,
            "rationale": "Naive baseline rank by visible in vitro potency and assay count.",
            "main_risk": "Ignores held-out in vivo translation and developability.",
        }
        for index, row in enumerate(ranked, start=1)
    ]
    return {"ranking": ranking, "top_3": [row["peptide_id"] for row in ranked[:3]]}


def _predict_hit_by_potency(path: Path) -> dict[str, Any]:
    row = _read_csv(path)[0]
    best_ec50 = _float(row.get("best_ec50_nm", ""))
    prediction = "active" if best_ec50 <= 10 else "inactive"
    return {
        "prediction": prediction,
        "confidence": 0.35,
        "effect_direction": "unknown",
        "rationale": "Naive baseline threshold on visible best EC50.",
        "main_risk": "Potency alone may not translate to the requested in vivo endpoint.",
    }


def _choose_exposure_experiment(path: Path) -> dict[str, Any]:
    rows = _read_csv(path)
    ranked = sorted(
        rows,
        key=lambda row: (
            0 if "exposure" in row.get("experiment", "").lower() else 1,
            _float(row.get("cost_units", "")),
        ),
    )
    return {
        "selected_option": ranked[0]["option_id"],
        "ranked_options": [row["option_id"] for row in ranked],
        "rationale": "Naive baseline prefers experiments mentioning exposure, then lower cost.",
        "decision_gate": "Advance only if exposure and endpoint evidence are concordant.",
    }


def _generic_scientific_answer(task_type: str) -> dict[str, Any]:
    if task_type == "drug_discovery_program":
        return {
            "recommendation": "Nominate a lead candidate only after confirming potency and assay breadth.",
            "mechanistic_model": "The candidate should act through the intended receptor and pathway.",
            "experiments": [
                {
                    "id": "EXP-BASELINE",
                    "purpose": "Run a dose experiment with controls and matching in vitro assay.",
                    "controls": ["vehicle", "positive_control"],
                    "decision_gate": "Advance if potency, dose response, and safety risk are acceptable.",
                }
            ],
            "risks": ["uncertainty", "artifact", "exposure"],
            "next_design_cycle": "Improve potency and exposure while monitoring liabilities.",
        }
    return {
        "primary_hypothesis": "The result should be interpreted with uncertainty and validated experimentally.",
        "supporting_evidence": [
            "Visible assay evidence may support the decision but is not ground truth.",
            "Model predictions or single assays require validation.",
        ],
        "alternative_hypotheses": ["assay artifact", "exposure limitation", "pathway context"],
        "falsifying_experiment": "Run an orthogonal assay or in vivo test with controls to validate the prediction.",
        "uncertainty": "The baseline does not deeply reason over all biological context.",
    }
