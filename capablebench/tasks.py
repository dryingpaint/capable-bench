from __future__ import annotations

import csv
import math
import random
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

from .ingest import read_csv_dicts
from .io import ensure_dir, write_csv, write_json, write_yaml


PROBLEMS_FIELDNAMES = [
    "id",
    "task_type",
    "question",
    "answer_rubric",
    "allowed_domains",
    "human_solvable",
    "data_path",
]


def _float(value: str) -> float | None:
    try:
        if value == "":
            return None
        result = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def _score_candidate(rows: list[dict[str, str]]) -> tuple[float, dict[str, Any]]:
    pec50_values = [_float(r.get("pec50", "")) for r in rows]
    pec50_values = [v for v in pec50_values if v is not None]
    best_pec50 = max(pec50_values) if pec50_values else 0.0

    emax_values = [_float(r.get("emax_pct", "")) for r in rows]
    emax_values = [v for v in emax_values if v is not None]
    best_emax = max(emax_values) if emax_values else 0.0

    assays = {r.get("assay", "") for r in rows}
    receptors = {r.get("receptor", "") for r in rows}
    condition_groups = {r.get("condition_group_id", "") for r in rows}
    tested_count = sum(1 for r in rows if r.get("status", "").lower() == "tested")

    # Pilot-only heuristic: reward potency, efficacy, and breadth of comparable evidence.
    score = best_pec50
    score += min(best_emax, 120.0) / 100.0
    score += 0.15 * len([a for a in assays if a])
    score += 0.10 * len([c for c in condition_groups if c])
    score += 0.02 * tested_count

    features = {
        "best_pec50": round(best_pec50, 3),
        "best_emax_pct": round(best_emax, 3),
        "assay_count": len(rows),
        "assays": sorted(a for a in assays if a),
        "receptors": sorted(r for r in receptors if r),
        "condition_group_count": len([c for c in condition_groups if c]),
        "heuristic_score": round(score, 4),
    }
    return score, features


def _write_candidate_file(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "peptide_id",
        "compound",
        "receptor_family",
        "best_pec50",
        "best_emax_pct",
        "assay_count",
        "assays",
        "receptors",
        "condition_group_count",
    ]
    write_csv(path, rows, fieldnames)


def _prompt(task_id: str, candidates_csv: str, top_k: int) -> str:
    return f"""You are helping decide which peptide candidates should advance to mouse testing.

You are in a task directory with candidate-level in vitro pharmacology summaries in:

{candidates_csv}

Rank the candidates from most to least promising for translational follow-up.
Select the top {top_k}.

Use the evidence in the file and be explicit about uncertainty. Prefer candidates
with stronger potency/efficacy and more internally consistent supporting assay
evidence. Do not assume that this pilot task contains mouse outcomes or stability
data unless those fields are present.

Write your final answer to answer.json with this schema:

{{
  "ranking": [
    {{
      "peptide_id": "PEP-...",
      "rank": 1,
      "confidence": 0.0,
      "rationale": "short rationale",
      "main_risk": "short risk"
    }}
  ],
  "top_{top_k}": ["PEP-...", "PEP-...", "PEP-..."]
}}

Task id: {task_id}
"""


def make_pilot_tasks(
    processed_dir: Path,
    tasks_dir: Path,
    answers_dir: Path,
    *,
    limit: int | None = None,
    min_candidates: int = 6,
    max_candidates: int = 12,
    top_k: int = 3,
    seed: int = 20260511,
) -> dict[str, Any]:
    assays_path = processed_dir / "invitro_assays.csv"
    peptides_path = processed_dir / "peptides.csv"
    if not assays_path.exists() or not peptides_path.exists():
        raise FileNotFoundError("Run ingest first; expected data/processed/invitro_assays.csv and peptides.csv")

    shutil.rmtree(tasks_dir, ignore_errors=True)
    shutil.rmtree(answers_dir, ignore_errors=True)
    ensure_dir(tasks_dir)
    ensure_dir(answers_dir)

    assay_rows = read_csv_dicts(assays_path)
    peptide_rows = {r["peptide_id"]: r for r in read_csv_dicts(peptides_path)}

    by_family: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
    for row in assay_rows:
        peptide_id = row["peptide_id"]
        family = peptide_rows.get(peptide_id, {}).get("receptor_family", "UNKNOWN")
        if row.get("status", "").lower() == "tested":
            by_family[family][peptide_id].append(row)

    rng = random.Random(seed)
    problems: list[dict[str, str]] = []
    task_count = 0

    for family, peptide_map in sorted(by_family.items()):
        peptide_ids = [pid for pid, rows in peptide_map.items() if rows]
        if len(peptide_ids) < min_candidates:
            continue

        rng.shuffle(peptide_ids)
        chunk_size = min(max_candidates, max(min_candidates, len(peptide_ids)))
        for start in range(0, len(peptide_ids), chunk_size):
            chunk = peptide_ids[start : start + chunk_size]
            if len(chunk) < min_candidates:
                continue
            task_count += 1
            task_id = f"pilot-prioritization-{family.lower()}-{task_count:03d}"
            task_dir = ensure_dir(tasks_dir / task_id)

            candidate_rows: list[dict[str, Any]] = []
            scored: list[tuple[float, str, dict[str, Any]]] = []
            for peptide_id in chunk:
                score, features = _score_candidate(peptide_map[peptide_id])
                peptide = peptide_rows[peptide_id]
                candidate_rows.append(
                    {
                        "peptide_id": peptide_id,
                        "compound": peptide.get("compound", ""),
                        "receptor_family": family,
                        "best_pec50": features["best_pec50"],
                        "best_emax_pct": features["best_emax_pct"],
                        "assay_count": features["assay_count"],
                        "assays": ";".join(features["assays"]),
                        "receptors": ";".join(features["receptors"]),
                        "condition_group_count": features["condition_group_count"],
                    }
                )
                scored.append((score, peptide_id, features))

            candidates_path = task_dir / "candidates.csv"
            _write_candidate_file(candidates_path, candidate_rows)
            prompt_text = _prompt(task_id, "candidates.csv", top_k)
            (task_dir / "prompt.md").write_text(prompt_text, encoding="utf-8")
            write_yaml(
                task_dir / "task.yaml",
                {
                    "id": task_id,
                    "task_type": "candidate_prioritization",
                    "receptor_family": family,
                    "data_files": ["candidates.csv"],
                    "answer_file": "answer.json",
                    "allowed_domains": [],
                    "label_status": "pilot_heuristic_not_final_ground_truth",
                },
            )

            ranked = [pid for _, pid, _ in sorted(scored, reverse=True)]
            write_yaml(
                answers_dir / f"{task_id}.yaml",
                {
                    "id": task_id,
                    "task_type": "candidate_prioritization",
                    "label_status": "pilot_heuristic_not_final_ground_truth",
                    "top_k": top_k,
                    "gold_ranking": ranked,
                    f"gold_top_{top_k}": ranked[:top_k],
                    "scoring_note": "Heuristic oracle for harness validation only; replace with mouse-outcome labels.",
                },
            )

            problems.append(
                {
                    "id": task_id,
                    "task_type": "candidate_prioritization",
                    "question": prompt_text.replace("\n", "\\n"),
                    "answer_rubric": "Hidden heuristic ranking; pilot harness validation only.",
                    "allowed_domains": "",
                    "human_solvable": "unknown",
                    "data_path": str(task_dir.relative_to(tasks_dir.parent)),
                }
            )

            if limit is not None and len(problems) >= limit:
                write_csv(tasks_dir / "problems.csv", problems, PROBLEMS_FIELDNAMES)
                return {"tasks_created": len(problems), "tasks_dir": str(tasks_dir)}

    write_csv(tasks_dir / "problems.csv", problems, PROBLEMS_FIELDNAMES)
    write_json(tasks_dir / "task_generation_summary.json", {"tasks_created": len(problems)})
    return {"tasks_created": len(problems), "tasks_dir": str(tasks_dir)}


def list_tasks(tasks_dir: Path) -> list[dict[str, str]]:
    problems_path = tasks_dir / "problems.csv"
    if not problems_path.exists():
        return []
    with problems_path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

