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
        # For stream-json output, search for answer patterns directly in text
        # Search for {"answer": "X"} pattern specifically
        answer_match = re.search(r'\{"answer":\s*"[^"]+"\}', text)
        if answer_match:
            try:
                return json.loads(answer_match.group(0))
            except json.JSONDecodeError:
                pass

        # Look for other answer formats
        for pattern in [
            r'\{"prediction":\s*"[^"]+"\}',
            r'\{"label":\s*"[^"]+"\}',
            r'\{"choice":\s*"[^"]+"\}',
        ]:
            match = re.search(pattern, text)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    continue

        # Try to find JSON objects by parsing line by line (for stream-json)
        answer_candidates = []
        result_obj = None

        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        # Check if this is a result object from claude-code stream output
                        if obj.get("type") == "result" and "result" in obj:
                            result_obj = obj
                        # Check if this is a direct answer object
                        elif any(key in obj for key in ["answer", "prediction", "label", "choice", "ranking", "top_1", "top_2", "top_3"]):
                            return obj  # Return first answer-like object found
                        answer_candidates.append(obj)
                except json.JSONDecodeError:
                    continue

        # If we found a result object, try to extract the answer from its result field
        if result_obj and isinstance(result_obj.get("result"), str):
            result_text = result_obj["result"]
            # Look for {"answer": "X"} pattern in the result text
            answer_match = re.search(r'\{"answer":\s*"[^"]+"\}', result_text)
            if answer_match:
                try:
                    return json.loads(answer_match.group(0))
                except json.JSONDecodeError:
                    pass

        # Check for Codex format - look for agent_message items with answer patterns
        for line in text.split('\n'):
            if '"type":"agent_message"' in line:
                try:
                    obj = json.loads(line.strip())
                    if isinstance(obj, dict) and obj.get("type") == "item.completed":
                        item = obj.get("item", {})
                        if item.get("type") == "agent_message" and "text" in item:
                            message_text = item["text"]
                            # Look for {"answer": "X"} pattern in the message text
                            answer_match = re.search(r'\{"answer":\s*"[^"]+"\}', message_text)
                            if answer_match:
                                try:
                                    return json.loads(answer_match.group(0))
                                except json.JSONDecodeError:
                                    pass
                except json.JSONDecodeError:
                    continue

        # If we found JSON objects but none were answer-like, return the last one
        if answer_candidates:
            return answer_candidates[-1]

        # Fallback: try to find any JSON pattern
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


def _extract_candidate_recommendations(answer: Any) -> list[str]:
    if isinstance(answer, dict):
        for key in ("top_3", "top_candidates", "recommended_candidates", "ranking"):
            value = answer.get(key)
            if isinstance(value, list):
                ids = []
                for item in value:
                    if isinstance(item, dict):
                        candidate = (
                            item.get("candidate_id")
                            or item.get("peptide_id")
                            or item.get("compound")
                            or item.get("proposed_modification")
                            or item.get("name")
                        )
                        if candidate:
                            ids.append(str(candidate))
                    elif item is not None:
                        ids.append(str(item))
                if ids:
                    return ids
        raw = answer.get("raw_text", "")
        if isinstance(raw, str):
            return _extract_ids_from_text(raw)
    if isinstance(answer, list):
        return [str(x) for x in answer]
    return []


def _answer_text(answer: Any) -> str:
    if isinstance(answer, dict):
        raw = answer.get("raw_text")
        if isinstance(raw, str):
            return raw
        return json.dumps(answer, sort_keys=True)
    if isinstance(answer, list):
        return json.dumps(answer)
    return str(answer)


def _normalize_label(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _extract_label(answer: Any) -> str:
    if isinstance(answer, dict):
        for key in (
            "prediction",
            "label",
            "answer",
            "decision",
            "selected_option",
            "choice",
            "top_choice",
        ):
            value = answer.get(key)
            if isinstance(value, str) and value.strip():
                return _normalize_label(value)
        raw = answer.get("raw_text")
        if isinstance(raw, str):
            return _normalize_label(raw.splitlines()[0] if raw.splitlines() else raw)
    if isinstance(answer, str):
        return _normalize_label(answer.splitlines()[0] if answer.splitlines() else answer)
    return ""


def _extract_options(answer: Any) -> list[str]:
    if isinstance(answer, dict):
        for key in ("selected_options", "ranking", "ranked_options", "top_options"):
            value = answer.get(key)
            if isinstance(value, list):
                options = []
                for item in value:
                    if isinstance(item, dict):
                        option = (
                            item.get("option_id")
                            or item.get("id")
                            or item.get("choice")
                        )
                        if option:
                            options.append(_normalize_label(option))
                    else:
                        options.append(_normalize_label(item))
                if options:
                    return options
        label = _extract_label(answer)
        return [label] if label else []
    label = _extract_label(answer)
    return [label] if label else []


def _extract_ids_from_text(text: str) -> list[str]:
    seen = set()
    ids = []
    for match in re.findall(r"PEP-[A-F0-9]{10}", text):
        if match not in seen:
            seen.add(match)
            ids.append(match)
    return ids


def _grade_label_task(
    *,
    answer: Any,
    gold: dict[str, Any],
    answer_path: Path,
    gold_path: Path,
) -> dict[str, Any]:
    predicted = _extract_label(answer)
    accepted = [
        _normalize_label(label)
        for label in gold.get("accepted_labels", [gold.get("gold_label")])
        if label is not None
    ]
    exact = bool(predicted and predicted in accepted)
    return {
        "task_id": gold.get("id"),
        "task_type": gold.get("task_type"),
        "label_status": gold.get("label_status"),
        "answer_path": str(answer_path),
        "gold_path": str(gold_path),
        "predicted_label": predicted,
        "accepted_labels": accepted,
        "exact_match": exact,
        "score": 1.0 if exact else 0.0,
        "parsed_answer": bool(predicted),
    }


def _grade_multi_field_exact_match(
    *,
    answer: Any,
    gold: dict[str, Any],
    answer_path: Path,
    gold_path: Path,
) -> dict[str, Any]:
    gold_fields = gold.get("gold", {})
    if not isinstance(answer, dict):
        answer = {}
    per_field: dict[str, dict[str, Any]] = {}
    correct = 0
    for field, expected in gold_fields.items():
        predicted = answer.get(field)
        pred_norm = _normalize_label(predicted) if predicted is not None else ""
        gold_norm = _normalize_label(expected)
        ok = bool(pred_norm) and pred_norm == gold_norm
        if ok:
            correct += 1
        per_field[field] = {
            "predicted": predicted,
            "gold": expected,
            "exact_match": ok,
        }
    total = len(gold_fields) or 1
    score = correct / total
    return {
        "task_id": gold.get("id"),
        "task_type": gold.get("task_type"),
        "label_status": gold.get("label_status"),
        "answer_path": str(answer_path),
        "gold_path": str(gold_path),
        "fields": per_field,
        "correct_fields": correct,
        "total_fields": total,
        "exact_match": correct == total,
        "score": score,
        "parsed_answer": bool(answer),
    }


def _grade_option_task(
    *,
    answer: Any,
    gold: dict[str, Any],
    answer_path: Path,
    gold_path: Path,
) -> dict[str, Any]:
    predicted = _extract_options(answer)
    gold_ranking = [_normalize_label(x) for x in gold.get("gold_ranking", [])]
    gold_top = {
        _normalize_label(x)
        for x in gold.get("gold_top", gold.get("accepted_options", gold_ranking[:1]))
    }
    top1 = predicted[0] if predicted else ""
    reciprocal_rank = 0.0
    for rank, option in enumerate(predicted, start=1):
        if option in gold_top:
            reciprocal_rank = 1.0 / rank
            break
    return {
        "task_id": gold.get("id"),
        "task_type": gold.get("task_type"),
        "label_status": gold.get("label_status"),
        "answer_path": str(answer_path),
        "gold_path": str(gold_path),
        "predicted_options": predicted,
        "gold_top": sorted(gold_top),
        "top1_in_gold": bool(top1 and top1 in gold_top),
        "mean_reciprocal_rank": round(reciprocal_rank, 4),
        "score": round(reciprocal_rank, 4),
        "parsed_answer": bool(predicted),
    }



def _grade_pending_validation_task(
    *,
    answer: Any,
    gold: dict[str, Any],
    answer_path: Path,
    gold_path: Path,
) -> dict[str, Any]:
    recommendations = _extract_candidate_recommendations(answer)
    return {
        "task_id": gold.get("id"),
        "task_type": gold.get("task_type"),
        "label_status": gold.get("label_status"),
        "scoring_mode": gold.get("scoring_mode"),
        "answer_path": str(answer_path),
        "gold_path": str(gold_path),
        "predicted_recommendations": recommendations,
        "top_k_requested": gold.get("top_k"),
        "parsed_answer": bool(recommendations or _answer_text(answer).strip()),
        "scored": False,
        "score": None,
        "validation_status": gold.get("validation_status", "pending_wet_lab_validation"),
        "outcome_definition": gold.get("outcome_definition"),
    }


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


def grade_attempt(
    answer_path: Path, gold_path: Path, out_path: Path | None = None
) -> dict[str, Any]:
    gold = read_yaml(gold_path)
    answer = _load_answer(answer_path)
    task_type = gold.get("task_type")
    label_status = gold.get("label_status")
    scoring_mode = gold.get("scoring_mode")

    if label_status in {"wet_lab_validation_pending", "wet_lab_pending"} or scoring_mode in {
        "wet_lab_validation_pending",
        "pending_wet_lab_validation",
        "unscored_pending_validation",
    }:
        result = _grade_pending_validation_task(
            answer=answer, gold=gold, answer_path=answer_path, gold_path=gold_path
        )
        if out_path is not None:
            write_json(out_path, result)
        return result

    if task_type != "candidate_prioritization":
        if task_type == "hit_prediction":
            result = _grade_label_task(
                answer=answer, gold=gold, answer_path=answer_path, gold_path=gold_path
            )
        elif task_type == "next_experiment":
            result = _grade_option_task(
                answer=answer, gold=gold, answer_path=answer_path, gold_path=gold_path
            )
        elif task_type in {"program_lead_selection", "multitarget_activity"}:
            result = _grade_multi_field_exact_match(
                answer=answer, gold=gold, answer_path=answer_path, gold_path=gold_path
            )
        else:
            raise ValueError(f"No grader registered for task_type={task_type!r}")
        if out_path is not None:
            write_json(out_path, result)
        return result

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
        "top1_exact": bool(
            predicted and gold_ranking and predicted[0] == gold_ranking[0]
        ),
        "top1_in_gold_top_k": bool(predicted and predicted[0] in gold_top),
        "ndcg_at_k": round(_ndcg_at_k(predicted, gold_ranking, top_k), 4),
        "parsed_answer": bool(predicted),
    }
    if out_path is not None:
        write_json(out_path, result)
    return result
