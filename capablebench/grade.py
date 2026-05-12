from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .io import read_yaml, write_json


def _load_answer(path: Path) -> Any:
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return {"raw_text": text}


def _extract_ranking(answer: Any) -> list[str]:
    if isinstance(answer, dict):
        for key, value in answer.items():
            if key.startswith("top_") and isinstance(value, list):
                return [str(x) for x in value]
        ranking = answer.get("ranking")
        if isinstance(ranking, list):
            ids = []
            for item in ranking:
                if isinstance(item, dict) and "peptide_id" in item:
                    ids.append(str(item["peptide_id"]))
                elif isinstance(item, str):
                    ids.append(item)
            if ids:
                return ids
        raw = answer.get("raw_text", "")
        if isinstance(raw, str):
            return _extract_ids_from_text(raw)
    if isinstance(answer, list):
        return [str(x) for x in answer]
    return []


def _extract_ids_from_text(text: str) -> list[str]:
    seen = set()
    ids = []
    for match in re.findall(r"PEP-[A-F0-9]{10}", text):
        if match not in seen:
            seen.add(match)
            ids.append(match)
    return ids


def _ndcg_at_k(predicted: list[str], gold: list[str], k: int) -> float:
    gold_gain = {pid: 1.0 / (rank + 1) for rank, pid in enumerate(gold)}
    dcg = 0.0
    for i, pid in enumerate(predicted[:k]):
        dcg += gold_gain.get(pid, 0.0) / (1.0 if i == 0 else (math_log2(i + 2)))
    ideal = 0.0
    for i, pid in enumerate(gold[:k]):
        ideal += gold_gain.get(pid, 0.0) / (1.0 if i == 0 else (math_log2(i + 2)))
    return dcg / ideal if ideal else 0.0


def math_log2(value: float) -> float:
    import math

    return math.log(value, 2)


def grade_attempt(answer_path: Path, gold_path: Path, out_path: Path | None = None) -> dict[str, Any]:
    gold = read_yaml(gold_path)
    answer = _load_answer(answer_path)
    task_type = gold.get("task_type")

    if task_type != "candidate_prioritization":
        raise ValueError(f"No grader registered for task_type={task_type!r}")

    top_k = int(gold.get("top_k", 3))
    gold_ranking = list(gold.get("gold_ranking", []))
    gold_top = set(gold.get(f"gold_top_{top_k}", gold_ranking[:top_k]))
    predicted = _extract_ranking(answer)
    predicted_top = predicted[:top_k]

    hits = [pid for pid in predicted_top if pid in gold_top]
    result = {
        "task_id": gold.get("id"),
        "task_type": task_type,
        "label_status": gold.get("label_status"),
        "answer_path": str(answer_path),
        "gold_path": str(gold_path),
        "predicted_top_k": predicted_top,
        "gold_top_k": list(gold_top),
        "precision_at_k": len(hits) / top_k if top_k else 0.0,
        "top1_exact": bool(predicted and gold_ranking and predicted[0] == gold_ranking[0]),
        "top1_in_gold_top_k": bool(predicted and predicted[0] in gold_top),
        "ndcg_at_k": round(_ndcg_at_k(predicted, gold_ranking, top_k), 4),
        "parsed_answer": bool(predicted),
    }
    if out_path is not None:
        write_json(out_path, result)
    return result

