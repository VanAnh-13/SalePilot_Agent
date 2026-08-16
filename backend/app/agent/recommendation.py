"""Need extraction, follow-up resolution, and category-aware recommendation."""

from __future__ import annotations

import math
import re
from typing import Any

from app.agent.catalog_queries import (
    _fmt_num,
    _fmt_price,
    _fmt_sold,
    _summary,
    compare,
    product_public,
)
from app.catalog import normalize as N
from app.catalog import repository
from app.catalog.registry import (
    CATEGORIES,
    Category,
    Priority,
    Slot,
    detect_category,
    get_category,
)
from app.nlp.vi_normalizer import ViNormalizer as _ViNormalizer

_normalizer = _ViNormalizer()

__all__ = [
    "recommend_top3",
    "recommendation_need",
    "extract_need_from_text",
    "merge_needs",
    "pending_slots",
    "resolve_followup_answer",
]


# --------------------------------------------------------------------------- #
# Need extraction — universal budget/brand + per-category slots & priorities.
# --------------------------------------------------------------------------- #

def _extract_budget(text: str) -> int | None:
    low = text.casefold()
    if m := re.search(
            r"(?:dưới|duoi|tối đa|toi da|khoảng|khoang|tầm|tam|budget|ngân sách|ngan sach)\s*(\d+(?:[.,]\d+)?)\s*(?:triệu|trieu|tr)\b",
            low):
        return int(float(m.group(1).replace(",", ".")) * 1_000_000)
    if m := re.search(r"(\d+)\s*[-–]\s*(\d+)\s*(?:triệu|trieu|tr)\b", low):
        return int(m.group(2)) * 1_000_000
    if m := re.search(r"(\d+(?:[.,]\d+)?)\s*(?:triệu|trieu|tr)\b", low):
        return int(float(m.group(1).replace(",", ".")) * 1_000_000)
    if m := re.search(r"(\d[\d.,]{6,})\s*(?:đồng|dong|đ|vnđ|vnd)\b", low):
        return N.price(m.group(1))
    # "500k" / "800 nghìn" / "900 ngàn" → thousands.
    if m := re.search(r"(\d+(?:[.,]\d+)?)\s*(?:k|nghìn|nghin|ngàn|ngan)\b", low):
        return int(float(m.group(1).replace(",", ".")) * 1_000)
    return None


def _match_brand(text: str, cat: Category | None) -> str:
    low = text.casefold()
    refs = repository.brands(cat.code) if cat else []
    for brand in refs:
        if brand and brand.casefold() in low:
            return brand
    return ""


def extract_need_from_text(text: str, category: str | int | None = None) -> dict[str, Any]:
    """Parse a Vietnamese request into a normalized need profile (any category).

    The input is pre-processed by ViNormalizer (abbreviation expansion) before
    any pattern matching so that shorthands like "dc", "ko", "bh" are resolved
    to their full forms without altering any downstream logic.
    """
    raw = _normalizer.expand(text or "")
    low = raw.casefold()
    cat = get_category(category) or detect_category(raw)
    need: dict[str, Any] = {"priority": [], "raw": raw[:300]}
    if cat:
        need["category"] = cat.slug

    budget = _extract_budget(raw)
    if budget is not None:
        need["budget_vnd"] = budget

    brand = _match_brand(raw, cat)
    if brand:
        need["brand"] = brand

    if cat:
        for slot in cat.slots:
            for pattern in slot.extract:
                if m := re.search(pattern, low):
                    value = float(m.group(1).replace(",", ".")) * slot.mult
                    need[slot.key] = int(value) if value.is_integer() else value
                    break
        for prio in cat.priorities:
            if any(alias in low for alias in prio.aliases):
                need["priority"].append(prio.key)

    need["priority"] = list(dict.fromkeys(need["priority"]))
    return need


def merge_needs(stored: dict[str, Any], fresh: dict[str, Any]) -> dict[str, Any]:
    """Merge a freshly extracted need onto the accumulated multi-turn need.

    Fresh values win per key. Switching to a different category resets the
    old category's slots (they don't transfer) but keeps the budget, since
    "còn máy lạnh thì sao?" usually implies the same wallet.
    """
    stored = dict(stored or {})
    fresh = dict(fresh or {})
    stored_cat = stored.get("category")
    fresh_cat = fresh.get("category")

    if fresh_cat and stored_cat and fresh_cat != stored_cat:
        merged = fresh
        if merged.get("budget_vnd") is None and stored.get("budget_vnd") is not None:
            merged["budget_vnd"] = stored["budget_vnd"]
        return merged

    merged = stored
    for key, value in fresh.items():
        if key == "priority":
            merged["priority"] = list(
                dict.fromkeys([*(stored.get("priority") or []), *(value or [])])
            )
        elif value not in (None, "", []):
            merged[key] = value
    if not merged.get("category") and (fresh_cat or stored_cat):
        merged["category"] = fresh_cat or stored_cat
    return merged


def recommendation_need(
        *,
        category: str | int | None = None,
        household_size: int | None = None,
        capacity_l: int | None = None,
        budget_vnd: int | None = None,
        priorities: list[str] | None = None,
        preferred_styles: list[str] | None = None,
        max_width_cm: float | None = None,
        max_height_cm: float | None = None,
        max_depth_cm: float | None = None,
        force: bool = False,
        free_text: str = "",
) -> dict[str, Any]:
    """Build a need dict from explicit tool arguments (+ optional free text)."""
    need = extract_need_from_text(free_text, category) if free_text else {}
    if category is not None and "category" not in need:
        cat = get_category(category)
        if cat:
            need["category"] = cat.slug
    overrides = {
        "household_size": household_size,
        "capacity_l": capacity_l,
        "budget_vnd": budget_vnd,
        "max_width_cm": max_width_cm,
        "max_height_cm": max_height_cm,
        "max_depth_cm": max_depth_cm,
    }
    for key, value in overrides.items():
        if value is not None:
            need[key] = value
    if priorities:
        need.setdefault("priority", [])
        need["priority"] = list(dict.fromkeys([*need["priority"], *priorities]))
    if preferred_styles:
        need["preferred_styles"] = preferred_styles
    if force:
        need["force"] = True
        need["budget_flexible"] = True
    return need


# --------------------------------------------------------------------------- #
# Recommendation — per-category scoring with normalized spec stats.
# --------------------------------------------------------------------------- #

def _priorities(need: dict[str, Any]) -> list[str]:
    values = need.get("priority") or need.get("priorities") or []
    return [values] if isinstance(values, str) else list(values)


def _spec_stats(products: list[dict[str, Any]], key: str) -> tuple[float, float]:
    values = [float(p[key]) for p in (product_public(x) for x in products) if p.get(key) is not None]
    return (min(values), max(values)) if values else (0.0, 0.0)


def _active_slots(cat: Category, need: dict[str, Any]) -> list[tuple[Slot, float]]:
    out = []
    for slot in cat.slots:
        if slot.key in need and need[slot.key] is not None:
            out.append((slot, float(need[slot.key])))
    return out


def _missing_slots(cat: Category, need: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if need.get("budget_vnd") is None and need.get("budget_flexible") is not True:
        missing.append("budget_vnd")
    primary = [s for s in cat.slots if s.primary]
    # The primary sizing question is answered when the primary slot *or* any
    # sibling slot it offers as an alternative is provided — e.g. máy giặt asks
    # "mấy người HOẶC bao nhiêu kg", tủ lạnh accepts số người hoặc số lít. Only
    # gating on the primary slot re-asks forever when the user answers with the
    # alternative.
    if primary and not any(need.get(s.key) is not None for s in cat.slots):
        missing.append(primary[0].key)
    return missing


def _clarify_questions(cat: Category, missing: list[str]) -> list[str]:
    questions: list[str] = []
    for key in missing:
        if key == "budget_vnd":
            questions.append("Ngân sách dự kiến của mình khoảng bao nhiêu ạ?")
            continue
        slot = next((s for s in cat.slots if s.key == key), None)
        if slot:
            questions.append(slot.question or f"Anh/chị cho biết {slot.label} giúp em ạ?")
    return questions


# --------------------------------------------------------------------------- #
# Follow-up answers — map a short reply onto the slot we just asked about, so a
# terse "50" / "phòng ngủ" / "9" doesn't get dropped and re-asked forever.
# --------------------------------------------------------------------------- #

# Máy lạnh: the discovery question invites a room type instead of an exact m².
_ROOM_AREA_M2: dict[str, int] = {
    "phòng ngủ": 15, "phong ngu": 15,
    "phòng khách": 24, "phong khach": 24,
    "phòng bếp": 18, "phong bep": 18,
    "phòng trọ": 14, "phong tro": 14,
    "văn phòng": 30, "van phong": 30,
    "phòng lớn": 30, "phong lon": 30,
    "phòng nhỏ": 12, "phong nho": 12,
}


def pending_slots(need: dict[str, Any]) -> list[str]:
    """Slots still required before we can recommend (i.e. what we'd ask next)."""
    cat = get_category(need.get("category")) or detect_category(need.get("raw", ""))
    if cat is None:
        return []
    n = dict(need)
    if n.get("household_size") is not None and "household_size" not in {s.key for s in cat.slots}:
        n.pop("household_size", None)
    return _missing_slots(cat, n)


def resolve_followup_answer(
        need: dict[str, Any], prev_need: dict[str, Any], text: str
) -> dict[str, Any]:
    """Fill the pending slot from a short reply the normal parser can't catch.

    After the agent asks a discovery question, users answer tersely — "50",
    "phòng ngủ", "9" — without units or the product name. We look at which
    slot(s) were still missing on the previous turn and map the reply onto the
    first unfilled one: a bare number becomes that slot's value; a room type
    becomes an approximate area for cooling. No-ops when the reply already
    parsed or nothing was pending.
    """
    cat = get_category(need.get("category"))
    if cat is None:
        return need
    asked = pending_slots(prev_need)
    if not asked:
        return need

    low = (text or "").casefold().strip()
    match = re.fullmatch(r"(\d+(?:[.,]\d+)?)", low.replace(" ", ""))
    num = float(match.group(1).replace(",", ".")) if match else None
    product_slots = [k for k in asked if k != "budget_vnd"]

    if num is not None:
        target = next((k for k in product_slots if need.get(k) is None), None)
        if target is not None:
            slot = next((s for s in cat.slots if s.key == target), None)
            mult = (slot.mult if slot else 1.0) or 1.0
            value = num * mult
            need[target] = int(value) if float(value).is_integer() else value
            return need
        if "budget_vnd" in asked and need.get("budget_vnd") is None and 0 < num <= 500:
            need["budget_vnd"] = int(num * 1_000_000)  # "12" → 12 triệu
            return need

    for key in product_slots:
        if need.get(key) is not None:
            continue
        slot = next((s for s in cat.slots if s.key == key), None)
        if slot and (slot.range_key == "area" or slot.key == "area_m2"):
            for keyword, m2 in _ROOM_AREA_M2.items():
                if keyword in low:
                    need[key] = m2
                    return need
    return need


def _score(product: dict[str, Any], need: dict[str, Any], cat: Category, ctx: dict[str, Any]) -> float:
    public = product_public(product)
    price = public.get("price_vnd")
    if price is None:
        return -1e9
    score = 0.0

    budget = need.get("budget_vnd")
    if budget is not None:
        budget = int(budget)
        if int(price) <= budget:
            score += 4.0 + max(0.0, 2.0 - (budget - int(price)) / max(budget, 1) * 2)
        elif need.get("budget_flexible"):
            score -= min(6.0, (int(price) - budget) / max(budget, 1) * 10)
        else:
            return -1e9

    if need.get("brand") and need["brand"].casefold() == str(public.get("brand") or "").casefold():
        score += 3.0

    # Explicit preferred styles (MCP / tool argument back-compat).
    preferred = need.get("preferred_styles") or []
    if isinstance(preferred, str):
        preferred = [preferred]
    if preferred:
        style = str(public.get("style") or public.get("type") or "").casefold()
        if any(p.casefold() in style for p in preferred if p):
            score += 4.0

    for slot, value in ctx["slots"]:
        spec = public.get(slot.spec_key) if slot.spec_key else None
        if slot.kind == "range_fit":
            low = public.get(f"{slot.range_key}_min")
            high = public.get(f"{slot.range_key}_max")
            hard = slot.hardness == "hard"
            if low is None and high is None:
                if hard and slot.missing_policy != "allow_unknown":
                    return -1e9
                score -= slot.weight * 0.5
            elif (low is None or value >= float(low)) and (
                    high is None or value <= float(high)
            ):
                score += slot.weight
            else:
                if hard:
                    return -1e9
                score -= slot.weight + 2.0
        elif slot.kind == "max_constraint":
            if spec is None:
                if slot.hardness == "hard" and slot.missing_policy == "exclude":
                    return -1e9
                score -= slot.weight * 0.5
            elif float(spec) > value:
                return -1e9
            else:
                score += 1.0
        elif slot.kind == "min_constraint":
            if spec is None:
                if slot.hardness == "hard" and slot.missing_policy == "exclude":
                    return -1e9
                score -= slot.weight * 0.5
            elif float(spec) < value:
                return -1e9
            else:
                score += 1.0
        else:  # proximity
            if spec is None:
                score -= slot.weight * 0.4
            else:
                diff = abs(float(spec) - value)
                score += max(-slot.weight * 0.6, slot.weight - diff / max(value, 1) * slot.weight)

    for prio in ctx["prio_objs"]:
        score += _apply_priority(prio, public, ctx, need)

    # Real-world signals from the crawl: rating, popularity, live promotion.
    # Kept small so they tie-break rather than override need/budget fit.
    rating = public.get("rating")
    if rating:
        score += (float(rating) - 4.0) * 0.6  # 4.0★ neutral, 5.0★ ≈ +0.6
    sold = public.get("sold")
    if sold:
        score += min(1.0, math.log10(int(sold) + 1) / 5.0)  # popularity, capped at +1
    if public.get("price_sale_vnd") and public.get("price_original_vnd") and int(public["price_original_vnd"]) > int(
            public["price_sale_vnd"]):
        score += 0.5
    if public.get("gift_promotion"):
        score += 0.3
    return score


def _apply_priority(prio: Priority, public: dict[str, Any], ctx: dict[str, Any], need: dict[str, Any]) -> float:
    if prio.mode == "cheap":
        lo, hi = ctx["price_range"]
        price = public.get("price_vnd")
        if price is None or hi <= lo:
            return 0.0
        return prio.weight * (1 - (int(price) - lo) / (hi - lo))
    value = public.get(prio.spec_key)
    if prio.mode in {"bool", "present"}:
        return prio.weight if bool(value) else -prio.weight * 0.5
    if prio.mode == "text":
        return prio.weight if value and prio.value.casefold() in str(value).casefold() else -1.0
    if prio.mode in {"max_spec", "min_spec"}:
        lo, hi = ctx["spec_ranges"].get(prio.spec_key, (0.0, 0.0))
        if value is None or hi <= lo:
            return 0.0
        ratio = (float(value) - lo) / (hi - lo)
        return prio.weight * (ratio if prio.mode == "max_spec" else 1 - ratio)
    return 0.0


def _why(public: dict[str, Any], need: dict[str, Any], cat: Category, ctx: dict[str, Any]) -> str:
    bits: list[str] = []
    for slot, value in ctx["slots"]:
        if slot.kind == "range_fit":
            label = public.get("household_label") if slot.range_key == "household" else public.get(
                slot.range_key + "_min")
            if public.get(f"{slot.range_key}_min") is not None:
                bits.append(f"phù hợp {slot.label}")
        elif slot.spec_key and public.get(slot.spec_key) is not None:
            bits.append(_fmt_num(public[slot.spec_key], slot.unit))
    for prio in ctx["prio_objs"]:
        contribution = _apply_priority(prio, public, ctx, need)
        if contribution > 0 and prio.mode in {"bool", "present", "text"}:
            bits.append(prio.key.replace("_", " "))
    budget = need.get("budget_vnd")
    if budget and public.get("price_vnd") and int(public["price_vnd"]) <= int(budget):
        bits.append("trong ngân sách")
    if public.get("price_sale_vnd") and public.get("price_original_vnd"):
        gap = int(public["price_original_vnd"]) - int(public["price_sale_vnd"])
        if gap > 0:
            bits.append(f"giảm {_fmt_price(gap)}")
    if public.get("rating"):
        bits.append(f"{public['rating']}★")
    if public.get("sold"):
        bits.append(f"đã bán {_fmt_sold(public['sold'])}")
    return "; ".join(dict.fromkeys(bits))


def recommend_top3(need: dict[str, Any]) -> dict[str, Any]:
    """Rank the currently-priced products of the target category for this need."""
    cat = get_category(need.get("category")) or detect_category(need.get("raw", ""))
    if cat is None:
        # Never default to a category the user did not ask for.
        supported = ", ".join(c.display for c in CATEGORIES)
        return {
            "ok": False,
            "need_more": True,
            "missing_slots": ["category"],
            "ask": [
                "Anh/chị muốn tư vấn nhóm hàng nào ạ? "
                f"Các nhóm đang được cấu hình để tư vấn sâu gồm: {supported}."
            ],
            "source": "recommend:multi_category",
        }

    # Fridge back-compat: capacity_l is a proximity slot, household is range_fit.
    need = dict(need)
    if need.get("household_size") is not None and "household_size" not in {s.key for s in cat.slots}:
        need.pop("household_size", None)

    missing = _missing_slots(cat, need)
    if missing and not need.get("force"):
        return {
            "ok": False,
            "need_more": True,
            "missing_slots": missing,
            "ask": _clarify_questions(cat, missing),
            "category": cat.slug,
            "category_display": cat.display,
            "source": f"recommend:{cat.slug}",
        }

    products = [p for p in repository.by_category(cat.code) if p.get("price_vnd") is not None]
    ctx = {
        "slots": _active_slots(cat, need),
        "prio_objs": [p for p in cat.priorities if p.key in _priorities(need)],
        "price_range": _spec_stats(products, "price_vnd"),
        "spec_ranges": {},
    }
    for prio in ctx["prio_objs"]:
        if prio.mode in {"max_spec", "min_spec"} and prio.spec_key not in ctx["spec_ranges"]:
            ctx["spec_ranges"][prio.spec_key] = _spec_stats(products, prio.spec_key)

    scored = [(sc, p) for p in products if (sc := _score(p, need, cat, ctx)) > -1e8]
    scored.sort(key=lambda item: (-item[0], int(item[1].get("price_vnd") or 10 ** 15)))

    def _add(product: dict[str, Any], score: float) -> None:
        public = _summary(product)
        public["match_score"] = round(score, 2)
        public["why"] = _why(product_public(product), need, cat, ctx)
        top.append(public)

    def _model(product: dict[str, Any]) -> str:
        return str(product.get("model_code") or product.get("sku") or "")

    top: list[dict[str, Any]] = []
    brands: set[str] = set()
    seen_models: set[str] = set()
    # First pass: prefer brand diversity, skip near-duplicate models (colour variants).
    for sc, product in scored:
        if _model(product) in seen_models:
            continue
        brand = str(product.get("brand") or "")
        if brand in brands and len(top) < 2:
            continue
        _add(product, sc)
        brands.add(brand)
        seen_models.add(_model(product))
        if len(top) >= 3:
            break
    # Fallback: fill remaining slots (still de-duplicating by model).
    if len(top) < 3:
        for sc, product in scored:
            if _model(product) in seen_models:
                continue
            _add(product, sc)
            seen_models.add(_model(product))
            if len(top) >= 3:
                break

    tradeoffs = compare([it["sku"] for it in top]).get("tradeoffs", []) if len(top) >= 2 else []
    return {
        "ok": bool(top),
        "need_more": False,
        "message": "" if top else "Không tìm thấy mẫu có giá đáp ứng đầy đủ ngân sách và giới hạn đã chọn.",
        "category": cat.slug,
        "category_display": cat.display,
        "need": need,
        # Evidence counts: priced candidates evaluated vs excluded fail-closed
        # (hard constraint/budget violation or hard-slot data missing).
        "candidate_count": len(products),
        "rejection_count": len(products) - len(scored),
        "top3": top,
        "tradeoffs": tradeoffs,
        "source": f"catalog:{repository.source()}:category_code={cat.code}:recommend_top3",
        "disclaimer": (
            "Giá / khuyến mãi / đánh giá theo dữ liệu catalog tại thời điểm thu thập; "
            "nguồn không có tồn kho thời gian thực — cần kiểm tra lại giá và khả năng giao hàng trước khi chốt."
        ),
    }
