"""Versioned decision/provenance contract for recommendations."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from app.agent.recommendation import recommend_top3
from app.catalog import repository
from app.catalog.registry import get_category

DECISION_SCHEMA_VERSION = "salepilot-decision-v1"
_TRANSIENT_NEED_KEYS = {"raw", "last_skus"}


def _hash_obj(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _semantic_need(need: dict[str, Any]) -> dict[str, Any]:
    """Drop operational memory fields from the reproducible decision input."""
    semantic: dict[str, Any] = {}
    for key, value in need.items():
        if key in _TRANSIENT_NEED_KEYS or value in (None, "", []):
            continue
        if isinstance(value, list):
            semantic[key] = sorted(dict.fromkeys(value))
        else:
            semantic[key] = value
    return semantic


def _constraint_status(need: dict[str, Any], item: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    cat = get_category(need.get("category"))
    out: list[dict[str, Any]] = []
    budget = need.get("budget_vnd")
    if budget is not None:
        status = "unknown"
        if item is not None and item.get("price_vnd") is not None:
            status = "matched" if int(item["price_vnd"]) <= int(budget) else "violated"
        out.append(
            {
                "key": "budget_vnd",
                "hardness": "hard",
                "missing_policy": "exclude",
                "expected": budget,
                "actual": None if item is None else item.get("price_vnd"),
                "status": status,
            }
        )
    if cat is None:
        return out
    for slot in cat.slots:
        expected = need.get(slot.key)
        if expected is None:
            continue
        actual = None
        status = "unknown"
        if item is not None:
            if slot.kind == "range_fit":
                low = item.get(f"{slot.range_key}_min")
                high = item.get(f"{slot.range_key}_max")
                actual = {"min": low, "max": high}
                if low is None and high is None:
                    status = "unknown"
                elif float(expected) >= float(low or float("-inf")) and (
                    high is None or float(expected) <= float(high)
                ):
                    status = "matched"
                else:
                    status = "violated"
            else:
                actual = item.get(slot.spec_key) if slot.spec_key else None
                if actual is None:
                    status = "unknown"
                elif slot.kind == "max_constraint":
                    status = "matched" if float(actual) <= float(expected) else "violated"
                elif slot.kind == "min_constraint":
                    status = "matched" if float(actual) >= float(expected) else "violated"
                else:
                    status = "matched"
            if (
                status == "unknown"
                and slot.hardness == "hard"
                and slot.missing_policy == "exclude"
            ):
                status = "violated"
        out.append(
            {
                "key": slot.key,
                "hardness": slot.hardness,
                "missing_policy": slot.missing_policy,
                "expected": expected,
                "actual": actual,
                "status": status,
            }
        )
    return out


def _score_components(item: dict[str, Any], need: dict[str, Any]) -> dict[str, float]:
    comps: dict[str, float] = {}
    if need.get("budget_vnd") and item.get("price_vnd") is not None:
        budget = int(need["budget_vnd"])
        price = int(item["price_vnd"])
        comps["budget_fit"] = round(max(0.0, 1.0 - abs(budget - price) / max(budget, 1)), 4)
    if item.get("match_score") is not None:
        comps["match_score"] = float(item["match_score"])
    if item.get("rating") is not None:
        comps["rating"] = float(item["rating"])
    return comps


def build_decision(need: dict[str, Any], rec: dict[str, Any] | None = None) -> dict[str, Any]:
    rec = rec if rec is not None else recommend_top3(need)
    catalog = repository.catalog_identity()
    source = str(catalog.get("backend") or repository.source())
    top_items: list[dict[str, Any]] = []
    for item in rec.get("top3") or []:
        public = dict(item)
        # Keep normalized evidence fields so offline evaluators can re-check
        # labeled hard constraints without trusting status strings from the model.
        evidence = {
            key: value
            for key, value in public.items()
            if key
            not in {
                "sku",
                "name",
                "price_vnd",
                "category",
                "category_code",
                "why",
                "match_score",
                "score_components",
                "constraints",
                "provenance",
                "specs",
                "description",
                "search_text",
            }
            and (
                value is None
                or isinstance(value, (str, int, float, bool))
                or (isinstance(value, dict) and set(value.keys()) <= {"min", "max"})
            )
        }
        constraints = _constraint_status(need, public)
        top_items.append(
            {
                "sku": public.get("sku"),
                "name": public.get("name"),
                "price_vnd": public.get("price_vnd"),
                "category": public.get("category"),
                "category_code": public.get("category_code"),
                "why": public.get("why"),
                "match_score": public.get("match_score"),
                "score_components": _score_components(public, need),
                "constraints": constraints,
                "provenance": {
                    "sku": public.get("sku"),
                    "source": public.get("source") or source,
                    "source_row": public.get("source_row"),
                    "catalog_backend": source,
                    "catalog_hash": catalog.get("sha256"),
                },
                **evidence,
            }
        )

    decision = {
        "schema_version": DECISION_SCHEMA_VERSION,
        "ok": bool(rec.get("ok")),
        "need_more": bool(rec.get("need_more")),
        "missing_slots": list(rec.get("missing_slots") or []),
        "ask": list(rec.get("ask") or []),
        "category": rec.get("category"),
        "category_display": rec.get("category_display"),
        "parsed_need": _semantic_need(need),
        "candidate_count": rec.get("candidate_count"),
        "rejection_count": rec.get("rejection_count"),
        "top3": top_items,
        "tradeoffs": list(rec.get("tradeoffs") or []),
        "message": rec.get("message") or "",
        "disclaimer": rec.get("disclaimer") or "",
        "source": {
            "catalog_backend": source,
            "catalog_hash": catalog.get("sha256"),
            "catalog_products": catalog.get("products"),
            "label": rec.get("source") or f"catalog:{source}",
        },
        "constraint_summary": _constraint_status(need, None),
    }
    hash_payload = deepcopy({key: value for key, value in decision.items() if key != "decision_hash"})
    # Backend labels are transport metadata, not semantic decision content.
    hash_payload["source"] = {
        key: value
        for key, value in decision["source"].items()
        if key in {"catalog_hash", "catalog_products"}
    }
    for item in hash_payload.get("top3") or []:
        provenance = item.get("provenance")
        if isinstance(provenance, dict):
            provenance.pop("catalog_backend", None)
    decision["decision_hash"] = _hash_obj(hash_payload)
    return decision
