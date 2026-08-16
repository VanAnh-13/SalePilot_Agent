"""Canonical workbook category registry (Spec_cate_gia / 14 ngành).

Runtime detection, need slots, priorities and trade-offs for the RIVF
experiment path. Crawl-specific normalization lives in ``crawl_categories``.
"""

from __future__ import annotations

from typing import Any

from app.catalog import normalize as N
from app.catalog.category_model import (
    Category,
    CategoryRegistry,
    Priority,
    RangeSpec,
    Slot,
    Spec,
    Tradeoff,
    make_generic,
    slugify,
)


def _apply_spec(spec: Spec, raw: Any) -> Any:
    if spec.mode in {"num", "min", "max", "int"}:
        if spec.mode == "min":
            return N.min_number(raw)
        if spec.mode == "max":
            return N.max_number(raw)
        if spec.mode == "int":
            return N.integer(raw)
        return N.number(raw)
    if spec.mode == "text":
        text = N.clean(raw)
        return None if not text else text
    if spec.mode == "yesno":
        return N.yes_no(raw)
    if spec.mode == "present":
        parsed = N.yes_no(raw)
        if parsed is not None:
            return parsed
        text = (N.clean(raw) or "").casefold()
        if not text:
            return None
        # Descriptive feature cells are present unless they explicitly negate
        # the feature. This keeps "Không" from becoming True due to truthiness.
        if text.startswith(("không", "khong", "no", "chưa", "chua")):
            return False
        return True
    if spec.mode.startswith("flag:"):
        token = spec.mode.split(":", 1)[1].casefold()
        text = (N.clean(raw) or "").casefold()
        return bool(token in text and "không" not in text and "khong" not in text)
    return N.clean(raw)


def normalize_workbook_product(
    cat: Category,
    row: dict[str, Any],
    source_row: int,
    source: str,
) -> dict[str, Any]:
    """Normalize one flat workbook row into the engine document shape."""
    original = N.price(row.get("giá gốc") or row.get("Giá gốc"))
    sale = N.price(row.get("giá khuyến mãi") or row.get("Giá khuyến mãi"))
    current = sale or original
    sku = str(row.get("sku") or row.get("SKU") or "").strip()
    model = str(row.get("model_code") or row.get("model") or "").strip()

    raw_specs = {
        str(k): v
        for k, raw in row.items()
        if not str(k).startswith("__") and (v := N.clean(raw)) is not None
    }
    norm: dict[str, Any] = {}
    for spec in cat.specs:
        value = _apply_spec(spec, row.get(spec.col))
        if value is not None and value != "":
            norm[spec.key] = value
    for rng in cat.ranges:
        raw = row.get(rng.col)
        low, high = N.people_range(raw) if rng.kind == "people" else N.area_range(raw)
        if low is not None:
            norm[f"{rng.key}_min"] = low
        if high is not None:
            norm[f"{rng.key}_max"] = high

    brand = N.clean(row.get("brand") or row.get("Brand") or row.get("hãng"))
    name_bits = [cat.display]
    if brand:
        name_bits.append(brand)
    for key in cat.name_specs:
        if norm.get(key) not in (None, ""):
            unit = cat.spec_unit(key)
            val = norm[key]
            if isinstance(val, float) and val.is_integer():
                val = int(val)
            name_bits.append(f"{val}{(' ' + unit) if unit else ''}".strip())
    if model:
        name_bits.append(f"(model {model})")
    name = " ".join(name_bits)

    doc: dict[str, Any] = {
        "sku": sku,
        "model_code": model,
        "product_id_web": sku,
        "category_code": cat.code,
        "category": cat.slug,
        "category_display": cat.display,
        "brand": brand,
        "brand_id": None,
        "price_original_vnd": original,
        "price_sale_vnd": sale,
        "price_vnd": current,
        "has_current_price": current is not None,
        "gift_promotion": N.clean(row.get("quà tặng") or row.get("gift_promotion")),
        "outstanding": None,
        "rating": None,
        "sold": None,
        "warranty": N.clean(row.get("bảo hành")),
        "accessories": None,
        "color": N.clean(row.get("màu sắc") or row.get("color")),
        "image_url": None,
        "url": None,
        "online_only": False,
        "name": name,
        "description": " | ".join(f"{k}: {v}" for k, v in list(raw_specs.items())[:8])[:600],
        "norm": norm,
        "specs": raw_specs,
        "source": source,
        "source_row": int(source_row),
    }
    search_bits = [cat.display, cat.slug, brand or "", name, model, *[str(v) for v in raw_specs.values()]]
    doc["search_text"] = " ".join(search_bits).casefold()
    return doc


# Backward-compatible name used by crawl importer via crawl_categories.
def normalize_product(cat: Category, product: dict[str, Any], source: str = "products_detail.json") -> dict[str, Any]:
    from app.catalog.crawl_categories import normalize_product as crawl_normalize

    return crawl_normalize(cat, product, source)


CATEGORIES: tuple[Category, ...] = (
    Category(
        code=38, slug="tu_lanh", display="Tủ lạnh", sheet="Tủ Lạnh",
        aliases=("tủ lạnh", "tu lanh", "side by side", "multi door", "ngăn đá", "ngan da"),
        specs=(
            Spec("usable_capacity_l", "Dung tích sử dụng", "int", "lít"),
            Spec("width_cm", "Ngang", "num", "cm"),
            Spec("height_cm", "Cao", "num", "cm"),
            Spec("depth_cm", "Sâu", "num", "cm"),
            Spec("style", "Kiểu dáng", "text"),
            Spec("has_energy_saving", "Công nghệ tiết kiệm điện", "flag:inverter"),
            Spec("external_water", "Lấy nước ngoài", "yesno"),
        ),
        ranges=(RangeSpec("household", "Số người sử dụng", "people"),),
        name_specs=("usable_capacity_l",),
        slots=(
            Slot("household_size", "số người dùng",
                 question="Nhà mình khoảng mấy người dùng ạ?",
                 kind="range_fit", range_key="household", weight=5.0,
                 extract=(r"(\d+)\s*người", r"gia đình\s*(\d+)"), primary=True, hardness="soft"),
            Slot("capacity_l", "dung tích (lít)",
                 kind="proximity", spec_key="usable_capacity_l", unit="lít", weight=3.0,
                 extract=(r"(\d+)\s*l[íi]t",)),
            Slot("max_width_cm", "chiều ngang tối đa (cm)",
                 kind="max_constraint", spec_key="width_cm", unit="cm", weight=4.0,
                 extract=(r"ngang\s*(?:tối đa|toi da|max)?\s*(\d+(?:[.,]\d+)?)", r"(\d+(?:[.,]\d+)?)\s*cm"),
                 hardness="hard", missing_policy="exclude"),
        ),
        priorities=(
            Priority("tiet_kiem_dien", ("tiết kiệm điện", "tiet kiem dien", "inverter"), "bool", "has_energy_saving", weight=4.0),
            Priority("lay_nuoc_ngoai", ("lấy nước ngoài", "lay nuoc ngoai", "lấy nước"), "bool", "external_water", weight=2.0),
        ),
        tradeoffs=(
            Tradeoff("Dung tích lớn nhất", "usable_capacity_l", "max", "lít"),
            Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price"),
        ),
    ),
    Category(
        code=36, slug="may_lanh", display="Máy lạnh", sheet="Máy Lạnh",
        aliases=("máy lạnh", "may lanh", "điều hòa", "dieu hoa", "điều hoà"),
        specs=(
            Spec("btu", "Công suất", "max", "BTU"),
            Spec("has_inverter", "Inverter", "flag:inverter"),
            Spec("noise_db", "Độ ồn", "min", "dB"),
        ),
        ranges=(RangeSpec("area", "Phạm vi làm lạnh hiệu quả", "area"),),
        slots=(
            Slot("area_m2", "diện tích phòng (m²)",
                 question="Phòng mình rộng khoảng bao nhiêu m² ạ?",
                 kind="range_fit", range_key="area", unit="m²", weight=6.0,
                 extract=(r"(\d+(?:[.,]\d+)?)\s*m2", r"(\d+(?:[.,]\d+)?)\s*m²"), primary=True,
                 hardness="hard", missing_policy="clarify"),
        ),
        priorities=(
            Priority("tiet_kiem_dien", ("tiết kiệm điện", "inverter"), "bool", "has_inverter", weight=4.0),
            Priority("chay_em", ("chạy êm", "êm", "ít ồn", "yên tĩnh"), "min_spec", "noise_db", weight=3.0),
        ),
        tradeoffs=(
            Tradeoff("Công suất lớn nhất", "btu", "max", "BTU"),
            Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price"),
        ),
    ),
    Category(
        code=39, slug="may_giat", display="Máy giặt", sheet="Máy Giặt",
        aliases=("máy giặt", "may giat", "giặt sấy", "giat say"),
        specs=(
            Spec("wash_kg", "Khối lượng giặt", "num", "kg"),
            Spec("type", "Loại máy giặt", "text"),
            Spec("has_dryer", "Sấy", "present"),
        ),
        ranges=(RangeSpec("household", "Số người sử dụng", "people"),),
        slots=(
            Slot("wash_kg", "khối lượng giặt (kg)",
                 question="Cần giặt khoảng bao nhiêu kg mỗi lần ạ?",
                 kind="proximity", spec_key="wash_kg", unit="kg", weight=5.0,
                 extract=(r"(\d+(?:[.,]\d+)?)\s*kg",), primary=True),
            Slot("household_size", "số người dùng",
                 kind="range_fit", range_key="household", weight=3.0,
                 extract=(r"(\d+)\s*người",)),
        ),
        priorities=(
            Priority("cua_truoc", ("cửa trước", "cua truoc"), "text", "type", value="trước", weight=3.0),
            Priority("co_say", ("có sấy", "co say", "sấy"), "bool", "has_dryer", weight=3.0),
        ),
        tradeoffs=(Tradeoff("Giặt được nhiều nhất", "wash_kg", "max", "kg"), Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price")),
    ),
    Category(
        code=40, slug="may_say", display="Máy sấy", sheet="Máy Sấy",
        aliases=("máy sấy", "may say", "sấy quần áo"),
        specs=(Spec("dry_kg", "Khối lượng sấy", "num", "kg"),),
        slots=(Slot("dry_kg", "khối lượng sấy (kg)", question="Mình cần sấy khoảng bao nhiêu kg mỗi lần ạ?", kind="proximity", spec_key="dry_kg", unit="kg",
                    extract=(r"(\d+(?:[.,]\d+)?)\s*kg",), primary=True),),
        tradeoffs=(Tradeoff("Sấy nhiều nhất", "dry_kg", "max", "kg"), Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price")),
    ),
    Category(
        code=41, slug="may_rua_chen", display="Máy rửa chén", sheet="Máy Rửa Chén",
        aliases=("máy rửa chén", "may rua chen", "máy rửa bát"),
        specs=(Spec("place_settings", "Bộ chén", "int"),),
        slots=(Slot("place_settings", "số bộ chén", question="Gia đình mình cần máy rửa khoảng bao nhiêu bộ chén ạ?", kind="proximity", spec_key="place_settings",
                    extract=(r"(\d+)\s*bộ",), primary=True),),
        tradeoffs=(Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price"),),
    ),
    Category(
        code=30, slug="tu_dong", display="Tủ đông", sheet="Tủ Đông",
        aliases=("tủ đông", "tu dong", "tủ mát đông"),
        specs=(Spec("usable_capacity_l", "Dung tích", "int", "lít"),),
        slots=(Slot("capacity_l", "dung tích (lít)", question="Mình cần tủ đông khoảng bao nhiêu lít ạ?", kind="proximity", spec_key="usable_capacity_l", unit="lít",
                    extract=(r"(\d+)\s*l[íi]t",), primary=True),),
        tradeoffs=(Tradeoff("Dung tích lớn nhất", "usable_capacity_l", "max", "lít"), Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price")),
    ),
    Category(
        code=49, slug="may_nuoc_nong", display="Máy nước nóng", sheet="Máy Nước Nóng",
        aliases=("máy nước nóng", "may nuoc nong", "bình nóng lạnh"),
        specs=(Spec("type", "Loại", "text"), Spec("capacity_l", "Dung tích", "num", "lít")),
        slots=(),
        tradeoffs=(Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price"),),
    ),
    Category(
        code=72, slug="dong_ho", display="Đồng hồ thông minh", sheet="Đồng Hồ",
        aliases=("đồng hồ", "dong ho", "smartwatch", "đồng hồ thông minh"),
        specs=(
            Spec("has_call", "Nghe gọi", "yesno"),
            Spec("has_health", "Theo dõi sức khỏe", "present"),
            Spec("has_sim", "SIM", "yesno"),
        ),
        slots=(),
        priorities=(
            Priority("nghe_goi", ("nghe gọi", "nghe goi", "gọi điện"), "bool", "has_call", weight=4.0),
            Priority("suc_khoe", ("sức khỏe", "theo dõi sức khỏe", "nhịp tim"), "bool", "has_health", weight=3.0),
        ),
        tradeoffs=(Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price"),),
    ),
    Category(
        code=73, slug="may_tinh_de_ban", display="Máy tính để bàn", sheet="Máy Tính Để Bàn",
        aliases=("máy tính để bàn", "may tinh de ban", "pc", "desktop"),
        specs=(Spec("ram_gb", "RAM", "num", "GB"), Spec("storage_gb", "Ổ cứng", "num", "GB")),
        slots=(Slot("ram_gb", "RAM (GB)", question="Mình cần tối thiểu bao nhiêu GB RAM ạ?", kind="min_constraint", spec_key="ram_gb", unit="GB",
                    extract=(r"ram\s*(\d+)", r"(\d+)\s*gb\s*ram"), primary=True),),
        tradeoffs=(Tradeoff("RAM cao nhất", "ram_gb", "max", "GB"), Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price")),
    ),
    Category(
        code=75, slug="man_hinh", display="Màn hình", sheet="Màn Hình",
        aliases=("màn hình", "man hinh", "monitor"),
        specs=(Spec("screen_inch", "Kích thước", "num", "inch"),),
        slots=(Slot("screen_inch", "inch", question="Mình muốn màn hình khoảng bao nhiêu inch ạ?", kind="proximity", spec_key="screen_inch", unit="inch",
                    extract=(r"(\d+(?:[.,]\d+)?)\s*inch",), primary=True),),
        tradeoffs=(Tradeoff("Màn lớn nhất", "screen_inch", "max", "inch"), Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price")),
    ),
    Category(
        code=115, slug="may_in", display="Máy in", sheet="Máy In",
        aliases=("máy in", "may in", "printer"),
        specs=(Spec("type", "Loại máy in", "text"),),
        slots=(),
        tradeoffs=(Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price"),),
    ),
    Category(
        code=116, slug="may_tinh_bang", display="Máy tính bảng", sheet="Máy Tính Bảng",
        aliases=("máy tính bảng", "may tinh bang", "tablet", "ipad"),
        specs=(
            Spec("has_sim", "SIM", "yesno"),
            Spec("storage_gb", "Bộ nhớ", "num", "GB"),
            Spec("battery", "Pin", "present"),
        ),
        slots=(),
        priorities=(
            Priority("co_sim", ("có sim", "co sim", "lắp sim", "5g", "4g"), "bool", "has_sim", weight=4.0),
            Priority("pin_trau", ("pin trâu", "pin khỏe", "pin lâu"), "bool", "battery", weight=3.0),
        ),
        tradeoffs=(Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price"),),
    ),
    Category(
        code=137, slug="micro_karaoke", display="Micro karaoke", sheet="Micro Karaoke",
        aliases=("micro karaoke", "mic karaoke", "microphone karaoke"),
        specs=(),
        slots=(),
        tradeoffs=(Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price"),),
    ),
    Category(
        code=139, slug="micro_thu_am", display="Micro thu âm", sheet="Micro Thu Âm",
        aliases=("micro thu âm", "micro thu am", "mic thu âm"),
        specs=(),
        slots=(),
        tradeoffs=(Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price"),),
    ),
)

UNSUPPORTED_TERMS: tuple[tuple[str, str, str], ...] = (
    (r"\blaptop\b|\blap top\b|\bmacbook\b", "laptop", "Anh/chị có thể xem máy tính để bàn hoặc máy tính bảng trong catalog hiện có ạ."),
    (r"\bđiện thoại\b|\bdien thoai\b|\bsmartphone\b|\biphone\b", "điện thoại", ""),
    (r"\btivi\b|\bti vi\b|\bsmart tivi\b", "tivi", ""),
    (r"\bô ?tô\b|\boto\b|xe hơi", "ô tô", ""),
    (r"xe máy|xe gắn máy|xe điện", "xe máy / xe điện", ""),
    (r"thực phẩm|đồ ăn|rau củ", "thực phẩm", ""),
    (r"vé máy bay|khách sạn|tour du lịch", "dịch vụ du lịch", ""),
    (r"bất động sản|nhà đất|căn hộ", "bất động sản", ""),
)


REGISTRY = CategoryRegistry(
    CATEGORIES,
    unsupported_terms=UNSUPPORTED_TERMS,
    ignore_unsupported_when_category_detected=True,
)
BY_SLUG = REGISTRY.by_slug
BY_CODE = REGISTRY.by_code
BY_SHEET = REGISTRY.by_sheet
EXPECTED_SHEETS: tuple[str, ...] = tuple(category.sheet for category in CATEGORIES)

get_category = REGISTRY.get_category
detect_category = REGISTRY.detect_category
detect_negated_categories = REGISTRY.detect_negated_categories
detect_unsupported = REGISTRY.detect_unsupported
