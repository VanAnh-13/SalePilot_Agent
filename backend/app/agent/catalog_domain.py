"""Refrigerator catalog domain backed by the category_code=38 sheet snapshot."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "products.json"


@lru_cache(maxsize=1)
def load_products() -> tuple[dict[str, Any], ...]:
    if not DATA.exists():
        return tuple()
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    return tuple(payload if isinstance(payload, list) else [])


def reload_products() -> None:
    load_products.cache_clear()


def _fmt_price(value: int | None) -> str:
    if value is None:
        return "Chưa có giá"
    return f"{int(value):,}".replace(",", ".") + "đ"


def _summary(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "sku": str(p.get("sku") or ""),
        "model_code": str(p.get("model_code") or ""),
        "product_id_web": str(p.get("product_id_web") or ""),
        "name": p.get("name") or "",
        "brand": p.get("brand"),
        "category": p.get("category"),
        "category_code": p.get("category_code"),
        "style": p.get("style"),
        "price_vnd": p.get("price_vnd"),
        "price_display": _fmt_price(p.get("price_vnd")),
        "original_price_vnd": p.get("original_price_vnd"),
        "sale_price_vnd": p.get("sale_price_vnd"),
        "has_current_price": bool(p.get("has_current_price")),
        "usable_capacity_l": p.get("usable_capacity_l"),
        "gross_capacity_l": p.get("gross_capacity_l"),
        "freezer_capacity_l": p.get("freezer_capacity_l"),
        "fridge_capacity_l": p.get("fridge_capacity_l"),
        "household_size_label": p.get("household_size_label"),
        "household_size_min": p.get("household_size_min"),
        "household_size_max": p.get("household_size_max"),
        "energy_saving_technology": p.get("energy_saving_technology"),
        "has_energy_saving": bool(p.get("has_energy_saving")),
        "food_preservation_technology": p.get("food_preservation_technology"),
        "doors": p.get("doors"),
        "height_cm": p.get("height_cm"),
        "width_cm": p.get("width_cm"),
        "depth_cm": p.get("depth_cm"),
        "external_water_dispenser": p.get("external_water_dispenser"),
        "automatic_mode": p.get("automatic_mode"),
        "description": (p.get("description") or "")[:500],
        "source": p.get("source"),
    }


def product_public(p: dict[str, Any]) -> dict[str, Any]:
    result = _summary(p)
    result.update(
        {
            "cooling_technology": p.get("cooling_technology"),
            "made_in": p.get("made_in"),
            "release_time": p.get("release_time"),
            "tray_material": p.get("tray_material"),
            "energy_consumption": p.get("energy_consumption"),
            "body_material": p.get("body_material"),
            "features": p.get("features") or [],
            "motor_material": p.get("motor_material"),
            "convertible_compartment_l": p.get("convertible_compartment_l"),
            "weight_kg": p.get("weight_kg"),
            "gift_promotion": p.get("gift_promotion"),
            "source_url": p.get("source_url"),
            "source_sheet": p.get("source_sheet"),
            "source_row": p.get("source_row"),
            "specs": p.get("specs") or {},
        }
    )
    return result


def get_by_sku(sku: str) -> dict[str, Any] | None:
    normalized = str(sku).strip()
    for product in load_products():
        if str(product.get("sku") or "").strip() == normalized:
            return product_public(product)
    return None


def _contains(text: str | None, query: str) -> bool:
    return query.casefold() in (text or "").casefold()


def _fits_household(product: dict[str, Any], household_size: int) -> bool:
    minimum = product.get("household_size_min")
    maximum = product.get("household_size_max")
    if minimum is None:
        return False
    return household_size >= int(minimum) and (
        maximum is None or household_size <= int(maximum)
    )


def _within_dimension(product: dict[str, Any], key: str, maximum: float | None) -> bool:
    if maximum is None:
        return True
    value = product.get(key)
    return value is not None and float(value) <= maximum


def search(
    query: str = "",
    *,
    budget_vnd: int | None = None,
    household_size: int | None = None,
    min_capacity_l: int | None = None,
    max_width_cm: float | None = None,
    max_height_cm: float | None = None,
    max_depth_cm: float | None = None,
    energy_saving: bool | None = None,
    brand: str = "",
    style: str = "",
    priced_only: bool = False,
    limit: int | None = 8,
) -> list[dict[str, Any]]:
    q = (query or "").casefold().strip()
    brand_q = brand.casefold().strip()
    style_q = style.casefold().strip()
    scored: list[tuple[float, int, dict[str, Any]]] = []

    for index, product in enumerate(load_products()):
        if int(product.get("category_code") or 0) != 38:
            continue
        price = product.get("price_vnd")
        if priced_only and price is None:
            continue
        if budget_vnd is not None and (price is None or int(price) > budget_vnd):
            continue
        if household_size is not None and not _fits_household(product, household_size):
            continue
        capacity = product.get("usable_capacity_l")
        if min_capacity_l is not None and (
            capacity is None or int(capacity) < min_capacity_l
        ):
            continue
        if not _within_dimension(product, "width_cm", max_width_cm):
            continue
        if not _within_dimension(product, "height_cm", max_height_cm):
            continue
        if not _within_dimension(product, "depth_cm", max_depth_cm):
            continue
        if energy_saving is not None and bool(product.get("has_energy_saving")) != energy_saving:
            continue
        if brand_q and brand_q not in str(product.get("brand") or "").casefold():
            continue
        if style_q and style_q not in str(product.get("style") or "").casefold():
            continue

        text = " ".join(
            str(value)
            for value in (
                product.get("sku"),
                product.get("model_code"),
                product.get("product_id_web"),
                product.get("name"),
                product.get("brand"),
                product.get("style"),
                product.get("cooling_technology"),
                product.get("energy_saving_technology"),
                product.get("food_preservation_technology"),
                product.get("features"),
                product.get("description"),
                "lấy nước bên ngoài external water dispenser"
                if product.get("external_water_dispenser")
                else "",
                "làm đá tự động automatic mode" if product.get("automatic_mode") else "",
                " ".join(str(value) for value in (product.get("specs") or {}).values()),
            )
            if value
        ).casefold()
        score = 1.0
        if q:
            score = 0.0
            for token in re.split(r"\s+", q):
                if len(token) > 1 and token in text:
                    score += 1.0
            if q in text:
                score += 3.0
            if score <= 0:
                continue
        if household_size is not None:
            score += 4.0
        if min_capacity_l is not None:
            score += 2.0
        if price is not None:
            score += 0.5

        scored.append((score, index, product))

    scored.sort(
        key=lambda item: (
            -item[0],
            item[2].get("price_vnd") is None,
            int(item[2].get("price_vnd") or 10**15),
            item[1],
        )
    )
    selected = scored if limit is None else scored[: max(1, min(limit, 100))]
    return [_summary(product) for _, _, product in selected]


def compare(skus: list[str]) -> dict[str, Any]:
    items = [product for sku in skus[:5] if (product := get_by_sku(sku))]
    if len(items) < 2:
        return {
            "ok": False,
            "error": "Cần ít nhất 2 SKU hợp lệ",
            "items": items,
            "source": "catalog:google_sheet",
        }

    tradeoffs: list[str] = []
    priced = [item for item in items if item.get("price_vnd") is not None]
    if priced:
        cheapest = min(priced, key=lambda item: int(item["price_vnd"]))
        tradeoffs.append(
            f"Giá hiện tại thấp nhất: {cheapest['name']} ({cheapest['price_display']})."
        )
    capacities = [item for item in items if item.get("usable_capacity_l") is not None]
    if capacities:
        largest = max(capacities, key=lambda item: int(item["usable_capacity_l"]))
        tradeoffs.append(
            f"Dung tích sử dụng lớn nhất: {largest['name']} ({largest['usable_capacity_l']} lít)."
        )
    widths = [item for item in items if item.get("width_cm") is not None]
    if widths:
        narrowest = min(widths, key=lambda item: float(item["width_cm"]))
        tradeoffs.append(
            f"Ngang gọn nhất: {narrowest['name']} ({narrowest['width_cm']:g} cm)."
        )
    discounted = [
        item
        for item in items
        if item.get("original_price_vnd") and item.get("sale_price_vnd")
        and int(item["original_price_vnd"]) > int(item["sale_price_vnd"])
    ]
    if discounted:
        best_discount = max(
            discounted,
            key=lambda item: int(item["original_price_vnd"])
            - int(item["sale_price_vnd"]),
        )
        discount = int(best_discount["original_price_vnd"]) - int(
            best_discount["sale_price_vnd"]
        )
        tradeoffs.append(
            f"Giảm giá nhiều nhất: {best_discount['name']} ({_fmt_price(discount)})."
        )

    return {
        "ok": True,
        "items": items,
        "tradeoffs": tradeoffs,
        "plain_summary": " | ".join(tradeoffs),
        "source": "catalog:google_sheet:category_code=38",
    }


def _score_need(product: dict[str, Any], need: dict[str, Any]) -> float:
    score = 0.0
    household_size = need.get("household_size")
    budget = need.get("budget_vnd")
    target_capacity = need.get("capacity_l")
    priorities = need.get("priority") or need.get("priorities") or []
    if isinstance(priorities, str):
        priorities = [priorities]

    if household_size is not None:
        if _fits_household(product, int(household_size)):
            score += 6.0
        else:
            score -= 8.0

    capacity = product.get("usable_capacity_l")
    if target_capacity is not None:
        if capacity is None:
            score -= 5.0
        else:
            difference = abs(int(capacity) - int(target_capacity))
            score += max(-4.0, 5.0 - difference / max(int(target_capacity), 1) * 10)

    price = product.get("price_vnd")
    if price is None:
        return -100.0
    if budget is not None:
        budget_int = int(budget)
        if int(price) <= budget_int:
            score += 4.0
            score += max(0.0, 2.0 - (budget_int - int(price)) / max(budget_int, 1) * 2)
        elif need.get("budget_flexible"):
            score -= min(5.0, (int(price) - budget_int) / max(budget_int, 1) * 10)
        else:
            return -100.0

    for field, need_key in (
        ("width_cm", "max_width_cm"),
        ("height_cm", "max_height_cm"),
        ("depth_cm", "max_depth_cm"),
    ):
        maximum = need.get(need_key)
        if maximum is not None and not _within_dimension(product, field, float(maximum)):
            return -100.0
        if maximum is not None:
            score += 1.0

    preferred_styles = need.get("preferred_styles") or []
    if isinstance(preferred_styles, str):
        preferred_styles = [preferred_styles]
    if preferred_styles and any(
        _contains(product.get("style"), preferred) for preferred in preferred_styles
    ):
        score += 4.0

    preservation = str(product.get("food_preservation_technology") or "").casefold()
    for priority in priorities:
        value = str(priority).casefold()
        if value in {"tiet_kiem_dien", "tiết kiệm điện", "inverter"}:
            score += 3.0 if product.get("has_energy_saving") else -2.0
        elif value in {"lay_nuoc_ngoai", "lấy nước ngoài"}:
            score += 3.0 if product.get("external_water_dispenser") else -1.0
        elif value in {"tu_dong", "tự động"}:
            score += 3.0 if product.get("automatic_mode") else -1.0
        elif value in {"dong_mem", "đông mềm"}:
            score += 3.0 if "đông mềm" in preservation else -1.0
        elif value in {"bao_quan", "giữ tươi", "bao quản"}:
            score += 2.0 if preservation else -1.0
        elif value in {"gia_re", "giá rẻ", "rẻ"}:
            score += max(0.0, 4.0 - int(price) / 10_000_000)
        elif value in {"dung_tich_lon", "dung tích lớn"} and capacity:
            score += min(4.0, int(capacity) / 200)

    if (
        product.get("sale_price_vnd")
        and product.get("original_price_vnd")
        and int(product["original_price_vnd"]) > int(product["sale_price_vnd"])
    ):
        score += 0.5
    return score


def recommend_top3(need: dict[str, Any]) -> dict[str, Any]:
    """Rank currently-priced refrigerators for a normalized need profile."""
    missing = []
    if need.get("household_size") is None and need.get("capacity_l") is None:
        missing.append("household_size")
    if need.get("budget_vnd") is None and need.get("budget_flexible") is not True:
        missing.append("budget_vnd")
    if missing and not need.get("force"):
        return {
            "ok": False,
            "need_more": True,
            "missing_slots": missing,
            "ask": _clarify_questions(missing),
            "source": "recommend_rules:refrigerator",
        }

    scored = []
    for product in load_products():
        if int(product.get("category_code") or 0) != 38:
            continue
        score = _score_need(product, need)
        if score > -50:
            scored.append((score, product))
    scored.sort(
        key=lambda item: (
            -item[0],
            int(item[1].get("price_vnd") or 10**15),
        )
    )

    top: list[dict[str, Any]] = []
    brands: set[str] = set()
    for score, product in scored:
        brand = str(product.get("brand") or "")
        if brand in brands and len(top) < 2:
            continue
        public = _summary(product)
        public["match_score"] = round(score, 2)
        public["why"] = _why(product, need)
        top.append(public)
        brands.add(brand)
        if len(top) >= 3:
            break
    if len(top) < 3:
        selected_skus = {item["sku"] for item in top}
        for score, product in scored:
            if str(product.get("sku")) in selected_skus:
                continue
            public = _summary(product)
            public["match_score"] = round(score, 2)
            public["why"] = _why(product, need)
            top.append(public)
            if len(top) >= 3:
                break

    tradeoffs = compare([item["sku"] for item in top]).get("tradeoffs", []) if len(top) >= 2 else []
    return {
        "ok": bool(top),
        "need_more": False,
        "message": (
            "Không tìm thấy mẫu có giá đáp ứng đầy đủ ngân sách và giới hạn đã chọn."
            if not top
            else ""
        ),
        "need": need,
        "top3": top,
        "tradeoffs": tradeoffs,
        "source": "google_sheet:category_code=38:recommend_top3",
        "disclaimer": (
            "Giá theo snapshot Google Sheet; bảng không có dữ liệu tồn kho. "
            "Cần kiểm tra lại giá và khả năng giao hàng trước khi chốt."
        ),
    }


def recommendation_need(
    *,
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
    need = extract_need_from_text(free_text) if free_text else {}
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
        need["priority"] = priorities
    if preferred_styles:
        need["preferred_styles"] = preferred_styles
    if force:
        need["force"] = True
        need["budget_flexible"] = True
    return need


def _clarify_questions(missing: list[str]) -> list[str]:
    questions = {
        "household_size": "Nhà mình có bao nhiêu người dùng tủ lạnh ạ?",
        "budget_vnd": "Ngân sách dự kiến khoảng bao nhiêu ạ?",
    }
    return [questions[item] for item in missing if item in questions]


def _why(product: dict[str, Any], need: dict[str, Any]) -> str:
    bits = []
    if product.get("usable_capacity_l"):
        bits.append(f"dung tích {product['usable_capacity_l']} lít")
    if product.get("household_size_label"):
        bits.append(f"gợi ý cho {product['household_size_label']}")
    if product.get("style"):
        bits.append(str(product["style"]))
    if product.get("has_energy_saving") and product.get("energy_saving_technology"):
        bits.append(str(product["energy_saving_technology"]))
    budget = need.get("budget_vnd")
    if budget and int(product.get("price_vnd") or 0) <= int(budget):
        bits.append("trong ngân sách")
    dimensions = [product.get("width_cm"), product.get("height_cm"), product.get("depth_cm")]
    if all(value is not None for value in dimensions):
        bits.append(f"ngang×cao×sâu {dimensions[0]:g}×{dimensions[1]:g}×{dimensions[2]:g} cm")
    if product.get("sale_price_vnd") and product.get("original_price_vnd"):
        discount = int(product["original_price_vnd"]) - int(product["sale_price_vnd"])
        if discount > 0:
            bits.append(f"giảm {_fmt_price(discount)}")
    return "; ".join(bits)


def extract_need_from_text(text: str) -> dict[str, Any]:
    """Extract common refrigerator needs from Vietnamese text without an LLM."""
    raw = text or ""
    normalized = raw.casefold()
    need: dict[str, Any] = {"priority": [], "preferred_styles": []}

    if match := re.search(r"(?:trên|tren|hơn|hon)\s*(\d+)\s*(?:người|nguoi)", normalized):
        need["household_size"] = int(match.group(1)) + 1

    household_patterns = (
        r"(?:gia đình|gia dinh|nhà|nha|cho)\s*(\d+)\s*(?:người|nguoi)",
        r"(\d+)\s*(?:người|nguoi)",
    )
    for pattern in household_patterns:
        if "household_size" in need:
            break
        if match := re.search(pattern, normalized):
            need["household_size"] = int(match.group(1))
            break

    if match := re.search(r"(\d+)\s*(?:lít|lit)\b", normalized):
        need["capacity_l"] = int(match.group(1))

    if match := re.search(r"(?:dưới|duoi)\s*(\d+)\s*(?:triệu|trieu|tr)\b", normalized):
        need["budget_vnd"] = int(match.group(1)) * 1_000_000
    elif match := re.search(r"(\d+)\s*[-–]\s*(\d+)\s*(?:triệu|trieu|tr)\b", normalized):
        need["budget_vnd"] = int(match.group(2)) * 1_000_000
    elif match := re.search(r"(\d+)\s*(?:triệu|trieu|tr)\b", normalized):
        need["budget_vnd"] = int(match.group(1)) * 1_000_000
    if any(term in normalized for term in ("giá rẻ", "càng rẻ", "ngân sách thấp")):
        need["priority"].append("gia_re")

    for label, key in (
        ("ngang", "max_width_cm"),
        ("cao", "max_height_cm"),
        ("sâu", "max_depth_cm"),
        ("sau", "max_depth_cm"),
    ):
        if match := re.search(
            rf"{label}\s*(?:tối đa|toi da|dưới|duoi)?\s*(\d+(?:[.,]\d+)?)",
            normalized,
        ):
            need[key] = float(match.group(1).replace(",", "."))

    style_terms = {
        "side by side": "Tủ lớn - Side by Side",
        "multi door": "Multi Door",
        "4 cánh": "Multi Door",
        "ngăn đá dưới": "Ngăn đá dưới",
        "ngan da duoi": "Ngăn đá dưới",
        "ngăn đá trên": "Ngăn đá trên",
        "ngan da tren": "Ngăn đá trên",
        "mini": "Mini",
    }
    for term, style in style_terms.items():
        if term in normalized and style not in need["preferred_styles"]:
            need["preferred_styles"].append(style)

    priority_terms = {
        "tiết kiệm điện": "tiet_kiem_dien",
        "tiet kiem dien": "tiet_kiem_dien",
        "inverter": "tiet_kiem_dien",
        "lấy nước ngoài": "lay_nuoc_ngoai",
        "lay nuoc ngoai": "lay_nuoc_ngoai",
        "làm đá tự động": "tu_dong",
        "lam da tu dong": "tu_dong",
        "đông mềm": "dong_mem",
        "dong mem": "dong_mem",
        "giữ tươi": "bao_quan",
        "giu tuoi": "bao_quan",
        "bảo quản": "bao_quan",
        "bao quan": "bao_quan",
        "dung tích lớn": "dung_tich_lon",
        "dung tich lon": "dung_tich_lon",
    }
    for term, priority in priority_terms.items():
        if term in normalized:
            need["priority"].append(priority)

    need["priority"] = list(dict.fromkeys(need["priority"]))
    need["preferred_styles"] = list(dict.fromkeys(need["preferred_styles"]))
    need["raw"] = raw[:300]
    return need
