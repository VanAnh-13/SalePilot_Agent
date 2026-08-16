"""Score common result JSONL against benchmark labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from experiments.evaluate.metrics import (
    action_match,
    aggregate,
    category_correct,
    hard_constraint_violations,
    slot_micro_f1,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONDITIONS = ROOT / "experiments" / "conditions.json"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def score_episode(label: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    if not pred:
        return {
            "episode_id": label.get("episode_id"),
            "prediction_missing": True,
            "category_correct": False,
            "action_correct": False,
            "slot_f1": slot_micro_f1(label.get("expected_slots") or {}, {}),
            "hard_constraints": {
                "checked": 0,
                "violations": 0,
                "unknown": 0,
                "rate": 0.0,
                "no_prediction": True,
            },
            "predicted_action": None,
            "predicted_category": None,
        }
    decision = pred.get("decision") or {}
    predicted_need = decision.get("parsed_need") or pred.get("parsed_need") or {}
    predicted_cat = decision.get("category") or predicted_need.get("category") or pred.get("category")
    predicted_action = pred.get("predicted_action") or decision.get("predicted_action")
    if predicted_action is None:
        if decision.get("need_more"):
            predicted_action = "clarify"
        elif decision.get("ok") and decision.get("top3"):
            predicted_action = "recommend"
        elif pred.get("used_agents") and "knowledge" in (pred.get("used_agents") or []):
            predicted_action = "faq"
        else:
            predicted_action = "abstain"

    metrics = {
        "episode_id": label.get("episode_id"),
        "category_correct": category_correct(label.get("category"), predicted_cat),
        "action_correct": action_match(label.get("expected_action") or "", predicted_action),
        "slot_f1": slot_micro_f1(label.get("expected_slots") or {}, predicted_need),
        "hard_constraints": hard_constraint_violations(
            label.get("hard_constraints") or [],
            decision.get("top3") or pred.get("top3") or [],
        ),
        "predicted_action": predicted_action,
        "predicted_category": predicted_cat,
    }
    return metrics


def score_conditions(
    labels: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    expected_conditions: list[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Score every label against every condition without cross-condition overwrite."""
    observed_conditions = sorted(
        {
            str(row.get("condition") or row.get("system_id") or "default")
            for row in predictions
        }
    )
    condition_names = list(dict.fromkeys(expected_conditions or observed_conditions or ["default"]))
    unexpected = sorted(set(observed_conditions) - set(condition_names))
    if unexpected:
        raise ValueError(f"unexpected prediction conditions: {unexpected}")

    label_ids = [str(label.get("episode_id") or "") for label in labels]
    if any(not episode_id for episode_id in label_ids):
        raise ValueError("every label requires a non-empty episode_id")
    if len(label_ids) != len(set(label_ids)):
        raise ValueError("duplicate episode_id in labels")

    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for row in predictions:
        condition = str(row.get("condition") or row.get("system_id") or "default")
        key = (condition, str(row.get("episode_id") or ""))
        if key in by_key:
            raise ValueError(f"duplicate prediction for condition={condition!r} episode_id={key[1]!r}")
        by_key[key] = row

    expected_keys = {(condition, episode_id) for condition in condition_names for episode_id in label_ids}
    extra = sorted(set(by_key) - expected_keys)
    if extra:
        preview = ", ".join(f"{condition}/{episode_id}" for condition, episode_id in extra[:8])
        suffix = "..." if len(extra) > 8 else ""
        raise ValueError(f"unexpected {len(extra)} condition/episode predictions: {preview}{suffix}")
    missing = sorted(expected_keys - set(by_key))
    if missing:
        preview = ", ".join(f"{condition}/{episode_id}" for condition, episode_id in missing[:8])
        suffix = "..." if len(missing) > 8 else ""
        raise ValueError(f"missing {len(missing)} condition/episode predictions: {preview}{suffix}")

    rows: list[dict[str, Any]] = []
    aggregates: dict[str, Any] = {}
    for condition in condition_names:
        condition_rows: list[dict[str, Any]] = []
        for label in labels:
            episode_id = str(label.get("episode_id") or "")
            row = score_episode(label, by_key.get((condition, episode_id), {}))
            row["condition"] = condition
            condition_rows.append(row)
        rows.extend(condition_rows)
        aggregates[condition] = aggregate(condition_rows)
    return aggregates, rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--conditions-config", type=Path, default=DEFAULT_CONDITIONS)
    args = parser.parse_args()
    predictions = _load_jsonl(args.input)
    labels = _load_jsonl(args.labels)
    if not args.conditions_config.is_file():
        print(f"INVALID predictions: conditions config missing: {args.conditions_config}")
        return 1
    try:
        config = json.loads(args.conditions_config.read_text(encoding="utf-8"))
        expected_conditions = config.get("conditions")
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INVALID predictions: conditions config unreadable: {exc}")
        return 1
    if not isinstance(expected_conditions, list) or not expected_conditions or not all(
        isinstance(condition, str) and condition for condition in expected_conditions
    ):
        print("INVALID predictions: conditions config must contain a non-empty string list")
        return 1
    try:
        aggregates, rows = score_conditions(labels, predictions, expected_conditions)
    except ValueError as exc:
        print(f"INVALID predictions: {exc}")
        return 1
    print(json.dumps({"conditions": aggregates}, ensure_ascii=False, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps({"aggregates": aggregates, "episodes": rows}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
