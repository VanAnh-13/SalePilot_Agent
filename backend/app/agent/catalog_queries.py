"""Catalog read models, filtering, and product comparison."""

from __future__ import annotations

import re
from typing import Any

from app.catalog import normalize as N
from app.catalog import repository
from app.catalog.registry import Category, get_category


def fmt_price(value: int | float | None) -> str:
    if value is None:
        return "Chưa có giá"
    return f"{int(value):,}".replace(",", ".") + "đ"


def fmt_num(value: Any, unit: str = "") -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return f"{value} {unit}".strip() if unit else str(value)


def fmt_sold(value: Any) -> str:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return ""
    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}".rstrip("0").rstrip(".") + "tr"
    if number >= 1_000:
        return f"{number / 1_000:.1f}".rstrip("0").rstrip(".") + "k"
    return str(number)


def _norm(product: dict[str, Any]) -> dict[str, Any]:
    norm = dict(product.get("norm") or {})
    dimensions = (product.get("specs") or {}).get("Kích thước - Khối lượng")
    if dimensions:
        norm.setdefault("width_cm", N.dimension_cm(dimensions, "width"))
        norm.setdefault("height_cm", N.dimension_cm(dimensions, "height"))
        norm.setdefault("depth_cm", N.dimension_cm(dimensions, "depth"))
    return {key: value for key, value in norm.items() if value is not None}


def product_public(product: dict[str, Any]) -> dict[str, Any]:
    """Flatten a stored document into the stable agent/API product shape."""
    public: dict[str, Any] = {
        "sku": str(product.get("sku") or ""),
        "model_code": str(product.get("model_code") or ""),
        "product_id_web": str(product.get("product_id_web") or ""),
        "category": product.get("category"),
        "category_code": product.get("category_code"),
        "category_display": product.get("category_display"),
        "brand": product.get("brand"),
        "name": product.get("name") or "",
        "description": product.get("description") or "",
        "price_vnd": product.get("price_vnd"),
        "price_display": fmt_price(product.get("price_vnd")),
        "price_original_vnd": product.get("price_original_vnd"),
        "price_sale_vnd": product.get("price_sale_vnd"),
        "has_current_price": bool(product.get("has_current_price")),
        "gift_promotion": product.get("gift_promotion"),
        "rating": product.get("rating"),
        "sold": product.get("sold"),
        "sold_display": fmt_sold(product.get("sold")) if product.get("sold") else "",
        "warranty": product.get("warranty"),
        "accessories": product.get("accessories"),
        "color": product.get("color"),
        "image_url": product.get("image_url"),
        "url": product.get("url"),
        "source": product.get("source"),
        "source_row": product.get("source_row"),
        "specs": product.get("specs") or {},
    }
    public.update(_norm(product))
    return public


def summarize_product(product: dict[str, Any]) -> dict[str, Any]:
    public = product_public(product)
    public.pop("specs", None)
    return public


def get_by_sku(sku: str) -> dict[str, Any] | None:
    product = repository.get(sku)
    return product_public(product) if product else None


def load_products() -> tuple[dict[str, Any], ...]:
    return tuple(repository.all_products())


def reload_products() -> None:
    repository.reload()


def _fits_household(product: dict[str, Any], household_size: int) -> bool:
    norm = _norm(product)
    minimum = norm.get("household_min")
    if minimum is None:
        return False
    maximum = norm.get("household_max")
    return household_size >= int(minimum) and (
        maximum is None or household_size <= int(maximum)
    )


def search(
    query: str = "",
    *,
    category: str | int | None = None,
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
    cat = get_category(category)
    products = repository.by_category(cat.code) if cat else repository.all_products()

    query_text = (query or "").casefold().strip()
    brand_query = brand.casefold().strip()
    style_query = style.casefold().strip()
    scored: list[tuple[float, int, dict[str, Any]]] = []

    for index, product in enumerate(products):
        price = product.get("price_vnd")
        norm = _norm(product)
        if priced_only and price is None:
            continue
        if budget_vnd is not None and (price is None or int(price) > budget_vnd):
            continue
        if household_size is not None and not _fits_household(product, household_size):
            continue
        if min_capacity_l is not None:
            capacity = norm.get("usable_capacity_l") or norm.get("gross_capacity_l")
            if capacity is None or int(capacity) < min_capacity_l:
                continue
        if max_width_cm is not None and (
            norm.get("width_cm") is None or float(norm["width_cm"]) > max_width_cm
        ):
            continue
        if max_height_cm is not None and (
            norm.get("height_cm") is None or float(norm["height_cm"]) > max_height_cm
        ):
            continue
        if max_depth_cm is not None and (
            norm.get("depth_cm") is None or float(norm["depth_cm"]) > max_depth_cm
        ):
            continue
        energy_flag = norm.get("has_energy_saving", norm.get("has_inverter"))
        if energy_saving is not None and bool(energy_flag) != energy_saving:
            continue
        if brand_query and brand_query not in str(product.get("brand") or "").casefold():
            continue
        if style_query and style_query not in str(norm.get("style") or "").casefold():
            continue

        score = 1.0
        if query_text:
            text = product.get("search_text") or ""
            score = 0.0
            for token in re.split(r"\s+", query_text):
                if len(token) > 1 and token in text:
                    score += 1.0
            if query_text in text:
                score += 3.0
            if score <= 0:
                continue
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
    return [summarize_product(product) for _, _, product in selected]


def compare(skus: list[str]) -> dict[str, Any]:
    items = [
        product_public(product)
        for sku in skus[:5]
        if (product := repository.get(sku))
    ]
    if len(items) < 2:
        return {
            "ok": False,
            "error": "Cần ít nhất 2 SKU hợp lệ",
            "items": items,
            "source": f"catalog:{repository.source()}",
        }

    cat = get_category(items[0].get("category_code"))
    tradeoffs = _tradeoff_lines(cat, items) if cat and not cat.generic else []
    discounted = [
        item
        for item in items
        if item.get("price_original_vnd")
        and item.get("price_sale_vnd")
        and int(item["price_original_vnd"]) > int(item["price_sale_vnd"])
    ]
    if discounted:
        best = max(
            discounted,
            key=lambda item: int(item["price_original_vnd"])
            - int(item["price_sale_vnd"]),
        )
        gap = int(best["price_original_vnd"]) - int(best["price_sale_vnd"])
        tradeoffs.append(f"Giảm giá nhiều nhất: {best['name']} ({fmt_price(gap)}).")

    rated = [item for item in items if item.get("rating")]
    if rated:
        best = max(rated, key=lambda item: float(item["rating"]))
        tradeoffs.append(f"Đánh giá cao nhất: {best['name']} ({best['rating']}★).")

    best_sellers = [item for item in items if item.get("sold")]
    if best_sellers:
        best = max(best_sellers, key=lambda item: int(item["sold"]))
        tradeoffs.append(
            f"Bán chạy nhất: {best['name']} (đã bán {fmt_sold(best['sold'])})."
        )

    return {
        "ok": True,
        "items": items,
        "tradeoffs": tradeoffs,
        "plain_summary": " | ".join(tradeoffs),
        "source": (
            f"catalog:{repository.source()}:"
            f"category_code={items[0].get('category_code')}"
        ),
    }


def _tradeoff_lines(
    cat: Category,
    items: list[dict[str, Any]],
) -> list[str]:
    lines: list[str] = []
    for tradeoff in cat.tradeoffs:
        pool = [
            item for item in items if item.get(tradeoff.spec_key) is not None
        ]
        if not pool:
            continue
        pick = (min if tradeoff.mode == "min" else max)(
            pool,
            key=lambda item: float(item[tradeoff.spec_key]),
        )
        value = (
            fmt_price(pick[tradeoff.spec_key])
            if tradeoff.fmt == "price"
            else fmt_num(pick[tradeoff.spec_key], tradeoff.unit)
        )
        lines.append(f"{tradeoff.label}: {pick['name']} ({value}).")
    return lines
