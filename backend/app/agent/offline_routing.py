"""Pure routing policy for the offline multi-agent path.

Single responsibility: turn raw text plus the accumulated multi-turn need
into routing flags. No I/O here — the executor in offline.py loads memory,
calls this policy, then runs the routed handlers. Keeping the policy pure
makes it directly unit-testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.agent.intent import (
    COMPARE_KEYWORDS,
    ESCALATION_KEYWORDS,
    FAQ_KEYWORDS,
    STOCK_KEYWORDS,
    has_intent,
    phone_in_text,
)
from app.catalog.registry import Category, detect_category, detect_unsupported

# The offline router has no LLM, so its FAQ net is intentionally wider than
# the shared FAQ_KEYWORDS: short stems ("lắp", "giao", "đổi") catch phrasings
# the stricter fast-path list would route to the graph instead.
FAQ_EXTRA_KEYWORDS = ("lắp", "giao", "ship", "đổi", "trả", "đổi cũ")
CRM_EXTRA_KEYWORDS = ("gọi lại", "để lại sđt", "liên hệ em")
GENERIC_INTENT_KEYWORDS = (
    "gợi ý", "so sánh", "nên mua", "tư vấn", "top", "rẻ", "tiết kiệm", "triệu", "mua",
)

_SKU_RE = re.compile(r"\b\d{4,7}\b")


def _has_need_signal(need: dict[str, Any]) -> bool:
    """True when the need profile carries any slot beyond the raw text."""
    return any(
        value not in (None, "", [])
        for key, value in need.items()
        if key not in {"raw", "category", "priority"}
    ) or bool(need.get("priority"))


@dataclass(frozen=True)
class TurnSignals:
    """Routing decision for one offline turn."""

    stock_question: bool
    need_faq: bool
    need_escalate: bool
    need_crm: bool
    phone: str | None
    need_product: bool
    compare_intent: bool
    do_compare_now: bool
    compare_skus: list[str] = field(default_factory=list)
    unsupported: tuple[str, str | None] | None = None


def read_turn_signals(
    user_text: str,
    *,
    stored_need: dict[str, Any],
    extracted_need: dict[str, Any],
    merged_need: dict[str, Any],
    detected: Category | None,
) -> TurnSignals:
    """Classify one turn. Pure: same inputs always give the same signals."""
    t = user_text.lower()

    stock_question = has_intent(user_text, STOCK_KEYWORDS)
    need_faq = stock_question or has_intent(user_text, FAQ_KEYWORDS) or any(
        k in t for k in FAQ_EXTRA_KEYWORDS
    )
    need_escalate = has_intent(user_text, ESCALATION_KEYWORDS)
    phone = phone_in_text(user_text)
    need_crm = bool(phone) or any(k in t for k in CRM_EXTRA_KEYWORDS)

    # Honest guardrail: the sheet does not cover every product people ask for.
    unsupported = None
    if detected is None and not merged_need.get("category"):
        unsupported = detect_unsupported(user_text)

    # Compare intent: "so sánh 358683 với 360309" or "so sánh 2 mẫu vừa gợi ý".
    compare_intent = has_intent(user_text, COMPARE_KEYWORDS)
    skus_in_text = _SKU_RE.findall(user_text)

    generic_intent = any(k in t for k in GENERIC_INTENT_KEYWORDS)
    follow_up = bool(stored_need.get("category")) and _has_need_signal(extracted_need)
    need_product = (
        bool(detected)
        or follow_up
        or (_has_need_signal(extracted_need) and generic_intent)
    )
    if stock_question and not _has_need_signal(extracted_need):
        need_product = False
    if unsupported:
        need_product = False

    # Resolve a compare request to concrete SKUs (from the message, else the
    # last top-3 we recommended to this customer). Compare replaces recommend.
    compare_skus = skus_in_text[:5] if compare_intent else []
    if compare_intent and len(compare_skus) < 2:
        # Merge, don't replace: keep any SKU the user explicitly typed and fill
        # the rest from the last recommended top-3 (previously the typed SKU was
        # discarded, so the compare ran on stale SKUs and never answered the ask).
        extra = [s for s in (stored_need.get("last_skus") or []) if s not in compare_skus]
        compare_skus = (compare_skus + extra)[:5]
    do_compare_now = compare_intent and len(compare_skus) >= 2
    if do_compare_now:
        need_product = False

    return TurnSignals(
        stock_question=stock_question,
        need_faq=need_faq,
        need_escalate=need_escalate,
        need_crm=need_crm,
        phone=phone,
        need_product=need_product,
        compare_intent=compare_intent,
        do_compare_now=do_compare_now,
        compare_skus=compare_skus,
        unsupported=unsupported,
    )


__all__ = ["TurnSignals", "read_turn_signals"]
