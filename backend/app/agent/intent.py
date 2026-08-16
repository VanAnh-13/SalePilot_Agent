"""Shared intent detection and multi-turn need accumulation.

Single source of truth for the keyword-intent tuples and the need-merge
pipeline used by BOTH serving routes (LLM fast-path in graph.py and the
rule-based offline path). The tuples below are the union of the two
previously drifting copies; keep them as tuples with both diacritic and
non-diacritic spellings.
"""

from __future__ import annotations

import re
from typing import Any

from app.agent.catalog_domain import (
    detect_category,
    extract_need_from_text,
    merge_needs,
    resolve_followup_answer,
)
from app.agent.memory.store import load_profile

FAQ_KEYWORDS = (
    "bảo hành", "bao hanh", "giao hàng", "giao hang", "lắp đặt", "lap dat",
    "trả góp", "tra gop", "đổi trả", "doi tra", "chính sách", "chinh sach",
    "vệ sinh", "khui hộp", "khui hop", "hoá đơn", "hóa đơn",
)
ESCALATION_KEYWORDS = (
    "gặp người", "gap nguoi", "tư vấn viên", "tu van vien", "nhân viên",
    "nhan vien", "khiếu nại", "khieu nai",
)
COMPARE_KEYWORDS = (
    "so sánh", "so sanh", "compare", "đối chiếu", "doi chieu", "so kèo",
)
STOCK_KEYWORDS = ("còn hàng", "con hang", "tồn kho", "ton kho", "khả năng giao hàng")

PHONE_RE = re.compile(r"0\d{8,10}")


def phone_in_text(user_text: str) -> str | None:
    """First Vietnamese mobile number found in the text, if any."""
    m = PHONE_RE.search((user_text or "").replace(" ", "").replace(".", ""))
    return m.group(0) if m else None


def has_intent(user_text: str, keywords: tuple[str, ...]) -> bool:
    t = (user_text or "").lower()
    return any(k in t for k in keywords)


async def merge_turn_need(
    user_text: str,
    stored: dict[str, Any],
    *,
    resolve_followup: bool = True,
) -> tuple[dict[str, Any], object | None]:
    """Interpret one turn on top of the stored multi-turn need.

    A freshly named category wins over the stored one; short follow-up
    answers ("9kg", "5 người") fill the slot just asked unless the user
    switched category this turn. Returns (merged_need, detected_category).
    """
    detected = detect_category(user_text)
    ctx_category = (detected.slug if detected else None) or stored.get("category")
    fresh = extract_need_from_text(user_text, ctx_category)
    need = merge_needs(stored, fresh)
    if resolve_followup:
        switching = bool(
            detected and stored.get("category") and detected.slug != stored.get("category")
        )
        if not switching:
            need = resolve_followup_answer(need, stored, user_text)
    return need, detected


async def fill_budget_from_profile(
    need: dict[str, Any], *, channel: str, external_id: str
) -> None:
    """Budget mentioned in an earlier turn lives in the memory profile."""
    if need.get("budget_vnd") is None:
        profile = await load_profile(channel, external_id)
        if profile.get("budget_vnd"):
            need["budget_vnd"] = int(profile["budget_vnd"])


def format_need_more(rec: dict[str, Any]) -> str:
    """Ask the missing-slot question for a recommendation that needs more info."""
    display = (rec.get("category_display") or "sản phẩm").lower()
    asks = rec.get("ask") or []
    return (
        f"Để gợi ý {display} sát nhu cầu, em cần thêm:\n"
        + "\n".join(f"- {a}" for a in asks)
    )


__all__ = [
    "COMPARE_KEYWORDS",
    "ESCALATION_KEYWORDS",
    "FAQ_KEYWORDS",
    "STOCK_KEYWORDS",
    "fill_budget_from_profile",
    "format_need_more",
    "has_intent",
    "merge_turn_need",
    "phone_in_text",
]
