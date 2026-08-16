"""Backward-compatible facade for catalog queries and recommendation policy."""

from __future__ import annotations

from app.agent.catalog_queries import (
    compare,
    get_by_sku,
    load_products,
    product_public,
    reload_products,
    search,
)
from app.agent.recommendation import (
    _extract_budget,
    extract_need_from_text,
    merge_needs,
    pending_slots,
    recommend_top3,
    recommendation_need,
    resolve_followup_answer,
)
from app.catalog.registry import (
    detect_category,
    detect_negated_categories,
    detect_unsupported,
)

__all__ = [
    "search",
    "compare",
    "recommend_top3",
    "recommendation_need",
    "extract_need_from_text",
    "merge_needs",
    "pending_slots",
    "resolve_followup_answer",
    "detect_category",
    "detect_negated_categories",
    "detect_unsupported",
    "get_by_sku",
    "product_public",
    "load_products",
    "reload_products",
]
