"""Frozen metric implementations for SalePilot-R.

The benchmark labels are the source of truth for hard constraints.  A model
cannot make a violating item valid by returning a friendly-looking constraint
status in its own output.
"""

from __future__ import annotations

from typing import Any

SLOT_METADATA_FIELDS = {
    "raw",
    "category",
    "priority",
    "priorities",
    "last_skus",
    "force",
    "budget_flexible",
}


def category_correct(expected: str | None, predicted: str | None) -> bool:
    if expected in (None, ""):
        return predicted in (None, "", "null")
    return expected == predicted


def slot_micro_f1(expected: dict[str, Any], predicted: dict[str, Any]) -> dict[str, float]:
    exp_items = {k: expected[k] for k in expected if expected[k] not in (None, "", [])}
    pred_items = {
        k: predicted.get(k)
        for k in predicted
        if k not in SLOT_METADATA_FIELDS and predicted.get(k) not in (None, "", [])
    }
    tp = sum(1 for key, value in exp_items.items() if pred_items.get(key) == value)
    # A wrong value is both an unsupported prediction and a missed gold slot.
    fp = sum(1 for key, value in pred_items.items() if key not in exp_items or exp_items[key] != value)
    fn = sum(1 for key, value in exp_items.items() if key not in pred_items or pred_items[key] != value)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def _item_value(item: dict[str, Any], key: str) -> Any:
    """Resolve a benchmark constraint key to a public product field.

    Need slots intentionally use customer-facing names (for example
    ``max_width_cm`` and ``budget_vnd``), while product rows expose the actual
    measured field (``width_cm`` and ``price_vnd``).
    """
    aliases = {
        "budget_vnd": "price_vnd",
        "max_width_cm": "width_cm",
        "max_height_cm": "height_cm",
        "max_depth_cm": "depth_cm",
        "capacity_l": "usable_capacity_l",
    }
    field = aliases.get(key, key)
    if field in item:
        return item.get(field)

    norm = item.get("norm") or {}
    if field in norm:
        return norm.get(field)

    # Range-valued catalog specs are represented as <key>_min/<key>_max.
    range_prefixes = {
        "area_m2": "area",
        "household_size": "household",
    }
    prefix = range_prefixes.get(key)
    if prefix:
        low = item.get(f"{prefix}_min", norm.get(f"{prefix}_min"))
        high = item.get(f"{prefix}_max", norm.get(f"{prefix}_max"))
        if low is not None or high is not None:
            return {"min": low, "max": high}
    return None


def _same_value(left: Any, right: Any) -> bool:
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return float(left) == float(right)
    if isinstance(left, str) and isinstance(right, str):
        return left.strip().casefold() == right.strip().casefold()
    return left == right


def _constraint_matches(actual: Any, op: str, expected: Any) -> bool | None:
    """Return True/False, or None when the catalog value is unavailable."""
    if actual is None:
        return None
    try:
        if op == "eq":
            return _same_value(actual, expected)
        if op == "lte":
            return float(actual) <= float(expected)
        if op == "gte":
            return float(actual) >= float(expected)
        if op == "range_fit":
            if isinstance(actual, dict):
                low = actual.get("min")
                high = actual.get("max")
                value = float(expected)
                return (low is None or value >= float(low)) and (
                    high is None or value <= float(high)
                )
            return float(actual) == float(expected)
    except (TypeError, ValueError):
        return False
    return False


def hard_constraint_violations(
    constraints: list[dict[str, Any]],
    top_items: list[dict[str, Any]],
) -> dict[str, Any]:
    """Count label-grounded hard violations across recommended items.

    ``constraints`` comes from the benchmark label and contains ``key``,
    ``op``, ``value`` and ``missing_policy``.  Returned item metadata is used
    only as evidence for the comparison, never as the definition of success.
    """
    if not constraints:
        return {"checked": 0, "violations": 0, "rate": 0.0}
    if not top_items:
        # abstain/no match is not a violation of returned items
        return {"checked": 0, "violations": 0, "unknown": 0, "rate": 0.0, "no_items": True}

    checked = 0
    violations = 0
    unknown = 0
    for item in top_items:
        for cons in constraints:
            if cons.get("hardness", "hard") != "hard":
                continue
            checked += 1
            key = str(cons.get("key") or "")
            op = str(cons.get("op") or "")
            expected = cons.get("value")
            policy = str(cons.get("missing_policy") or "exclude")
            actual = _item_value(item, key)
            matched = _constraint_matches(actual, op, expected)
            if matched is False:
                violations += 1
            elif matched is None:
                unknown += 1
                # Returning an item with an unavailable hard field violates
                # every fail-closed policy; allow_unknown is the sole opt-out.
                if policy != "allow_unknown":
                    violations += 1
    rate = violations / checked if checked else 0.0
    return {"checked": checked, "violations": violations, "unknown": unknown, "rate": rate}


def action_match(expected: str, predicted: str) -> bool:
    return expected == predicted


def aggregate(episode_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(episode_metrics) or 1
    cat_acc = sum(1 for m in episode_metrics if m.get("category_correct")) / n
    act_acc = sum(1 for m in episode_metrics if m.get("action_correct")) / n
    slot_counts = {
        key: sum(int((m.get("slot_f1") or {}).get(key) or 0) for m in episode_metrics)
        for key in ("tp", "fp", "fn")
    }
    slot_precision = (
        slot_counts["tp"] / (slot_counts["tp"] + slot_counts["fp"])
        if slot_counts["tp"] + slot_counts["fp"]
        else 1.0
    )
    slot_recall = (
        slot_counts["tp"] / (slot_counts["tp"] + slot_counts["fn"])
        if slot_counts["tp"] + slot_counts["fn"]
        else 1.0
    )
    slot_f1 = (
        2 * slot_precision * slot_recall / (slot_precision + slot_recall)
        if slot_precision + slot_recall
        else 0.0
    )
    checked = sum(int((m.get("hard_constraints") or {}).get("checked") or 0) for m in episode_metrics)
    violations = sum(int((m.get("hard_constraints") or {}).get("violations") or 0) for m in episode_metrics)
    return {
        "episodes": len(episode_metrics),
        "category_accuracy": round(cat_acc, 4),
        "action_accuracy": round(act_acc, 4),
        "slot_micro_f1": round(slot_f1, 4),
        "slot_tp": slot_counts["tp"],
        "slot_fp": slot_counts["fp"],
        "slot_fn": slot_counts["fn"],
        "hard_constraints_checked": checked,
        "hard_constraint_violations": violations,
        "hard_constraint_violation_rate": round(violations / checked if checked else 0.0, 4),
    }
