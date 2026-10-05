"""Declarative per-category rules ("rule sâu cho từng ngành").

Rewritten for the real dienmayxanh.com crawl (``products_detail.json``): a
product carries a free-form ``spec_product`` dict whose Vietnamese keys differ
per category, plus prices, promotion, rating and units-sold. Each
:class:`Category` encodes everything the generic ranking engine needs to advise
on one product family: how to detect it from Vietnamese chat, which
``spec_product`` keys become normalized specs, which need slots to collect (and
how to ask for them), which buyer priorities map to which specs, and which
trade-off axes to surface.

The registry deeply configures the requirement's headline families (điện thoại,
laptop, tivi, loa/tai nghe, máy lạnh, tủ lạnh, máy giặt, máy hút bụi). Every
other category in the crawl is still importable and advisable through a
*generic* :class:`Category` built on the fly from the catalog data (ranked by
budget fit + rating + units sold), so SalePilot degrades gracefully instead of
refusing the ~110 long-tail families.
"""

from __future__ import annotations

import re
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


# --------------------------------------------------------------------------- #
# Normalization: raw crawl product -> normalized product document.
# --------------------------------------------------------------------------- #

_NEGATIVE = {"không", "khong", "không có", "khong co", "n/a", "na", "-", "hãng không công bố"}


def _price(value: Any) -> int | None:
    """Prices arrive as floats/ints/strings; 0 and blanks mean "no price"."""
    if value is None or value == "":
        return None
    try:
        result = int(round(float(value)))
    except (TypeError, ValueError):
        return N.price(value)
    return result or None


def _rating(value: Any) -> float | None:
    text = N.clean(value)
    if not text:
        return None
    num = N.number(text)
    if num is None or num <= 0:
        return None
    return round(float(num), 1)


def _sold(value: Any) -> int | None:
    """``"14,5k"`` -> ``14500`` ; ``"1,2tr"`` -> ``1_200_000`` ; ``"999"`` -> ``999``."""
    text = (N.clean(value) or "").casefold().replace(" ", "")
    if not text:
        return None
    m = re.match(r"([\d.,]+)\s*(k|tr|triệu|trieu)?", text)
    if not m:
        return None
    number = m.group(1).replace(".", "").replace(",", ".")
    try:
        base = float(number)
    except ValueError:
        return None
    suffix = m.group(2)
    if suffix == "k":
        base *= 1_000
    elif suffix in {"tr", "triệu", "trieu"}:
        base *= 1_000_000
    return int(round(base)) or None


def _apply_spec(spec: Spec, raw: Any) -> Any:
    if spec.mode in {"num", "min", "max", "int"}:
        if spec.mode == "min":
            return N.min_number(raw)
        if spec.mode == "max":
            return N.max_number(raw)
        if spec.mode == "int":
            return N.integer(raw)
        return N.number(raw)
    if spec.mode == "gb":
        # Scale by the unit of the FIRST capacity token only, so a note like
        # "512 GB SSD (… tối đa 2 TB)" reads as 512 GB, not 2 TB.
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*(tb|gb)", str(raw or ""), re.IGNORECASE)
        if not m:
            return N.number(raw)
        val = float(m.group(1).replace(",", "."))
        return val * 1024 if m.group(2).lower() == "tb" else val
    if spec.mode == "text":
        text = N.clean(raw)
        return None if (text or "").casefold() in _NEGATIVE else text
    if spec.mode == "yesno":
        return N.yes_no(raw)
    if spec.mode.startswith("dimension:"):
        return N.dimension_cm(raw, spec.mode.split(":", 1)[1])
    if spec.mode == "present":
        text = N.clean(raw)
        return bool(text and text.casefold() not in _NEGATIVE)
    if spec.mode.startswith("flag:"):
        token = spec.mode.split(":", 1)[1].casefold()
        text = (N.clean(raw) or "").casefold()
        return bool(token in text and "không" not in text and "khong" not in text)
    return N.clean(raw)


def normalize_product(
    cat: Category,
    product: dict[str, Any],
    source: str = "products_detail.json",
    source_row: int | None = None,
) -> dict[str, Any]:
    """Build a normalized, MongoDB-ready document from one crawl product."""
    original = _price(product.get("Giá gốc"))
    sale = _price(product.get("Giá khuyến mãi"))
    current = sale or original

    spec_product = product.get("spec_product") or {}
    raw_specs = {
        str(col): value
        for col, raw_value in spec_product.items()
        if (value := N.clean(raw_value)) is not None
    }

    norm: dict[str, Any] = {}
    for spec in cat.specs:
        value = _apply_spec(spec, spec_product.get(spec.col))
        if value is not None and value != "":
            norm[spec.key] = value
    for rng in cat.ranges:
        raw = spec_product.get(rng.col)
        if rng.kind == "people":
            low, high = N.people_range(raw)
        else:
            low, high = N.area_range(raw)
        if low is not None:
            norm[f"{rng.key}_min"] = low
        if high is not None:
            norm[f"{rng.key}_max"] = high

    category_code = int(product.get("category_id") or cat.code)
    doc: dict[str, Any] = {
        "sku": str(product.get("product_id") or "").strip(),
        "model_code": str(product.get("productcode") or "").strip(),
        "product_id_web": str(product.get("product_id") or "").strip(),
        "category_code": category_code,
        "category": cat.slug,
        "category_display": cat.display,
        "brand": N.clean(product.get("brand")),
        "brand_id": None,
        "price_original_vnd": original,
        "price_sale_vnd": sale,
        "price_vnd": current,
        "has_current_price": current is not None,
        "gift_promotion": N.clean(product.get("promotion")),
        "outstanding": N.clean(product.get("outstanding")),
        "rating": _rating(product.get("rating_vote")),
        "sold": _sold(product.get("quantity_sold")),
        "warranty": N.clean(product.get("chính sách bảo hành")),
        "accessories": N.clean(product.get("Phụ kiện đi kèm")),
        "color": N.clean(product.get("màu sắc")),
        "image_url": N.clean(product.get("url_image")),
        "url": N.clean(product.get("url")),
        "online_only": bool(product.get("onlineSaleOnly")),
        "norm": norm,
        "specs": raw_specs,
        "source": source,
        "source_row": source_row,
    }
    doc["name"] = N.clean(product.get("tên sản phẩm")) or _build_name(cat, doc)
    doc["description"] = _build_description(cat, doc)
    doc["search_text"] = _build_search_text(cat, doc)
    return doc


def _fmt_spec_value(cat: Category, key: str, value: Any) -> str:
    unit = cat.spec_unit(key)
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return f"{value} {unit}".strip() if unit else str(value)


def _build_name(cat: Category, doc: dict[str, Any]) -> str:
    parts = [cat.display]
    if doc.get("brand"):
        parts.append(str(doc["brand"]))
    for key in cat.name_specs:
        value = doc["norm"].get(key)
        if value not in (None, ""):
            parts.append(_fmt_spec_value(cat, key, value))
    model = doc.get("model_code")
    if model:
        parts.append(f"(model {model})")
    return " ".join(parts)


def _build_description(cat: Category, doc: dict[str, Any]) -> str:
    bits = []
    for key in cat.desc_specs:
        value = doc["specs"].get(key)
        if value and isinstance(value, str):
            bits.append(f"{key}: {value}")
    return " | ".join(bits)[:600]


def _build_search_text(cat: Category, doc: dict[str, Any]) -> str:
    chunks = [cat.display, cat.slug, str(doc.get("brand") or ""), doc.get("name", "")]
    chunks.extend(str(v) for v in doc["specs"].values())
    for spec in cat.specs:
        if doc["norm"].get(spec.key) is True:
            chunks.append(spec.col)
    return " ".join(chunks).casefold()


# --------------------------------------------------------------------------- #
# The registry — deep rules for the headline families.
# Category codes are the real dienmayxanh category_id values so that
# ``category_code`` on a stored document always equals ``Category.code``.
# --------------------------------------------------------------------------- #

CATEGORIES: tuple[Category, ...] = (
    # ---- Điện thoại -------------------------------------------------------- #
    Category(
        code=42, slug="dien_thoai", display="Điện thoại", sheet="Điện thoại",
        aliases=("điện thoại", "dien thoai", "smartphone", "iphone", "galaxy",
                 "điện thoai", "smart phone", "đt di động"),
        specs=(
            Spec("ram_gb", "RAM", "num", "GB"),
            Spec("storage_gb", "Dung lượng lưu trữ", "gb", "GB"),
            Spec("screen_inch", "Màn hình rộng", "num", '"'),
            Spec("battery_mah", "Dung lượng pin", "num", "mAh"),
            Spec("charge_w", "Hỗ trợ sạc tối đa", "num", "W"),
            Spec("screen_tech", "Công nghệ màn hình", "text"),
            Spec("chip", "Chip xử lý (CPU)", "text"),
            Spec("has_5g", "Mạng di động", "flag:5g"),
        ),
        desc_specs=("Chip xử lý (CPU)", "RAM", "Dung lượng lưu trữ", "Dung lượng pin", "Công nghệ màn hình"),
        slots=(
            Slot("storage_gb", "bộ nhớ (GB)",
                 question="Anh/chị cần bộ nhớ khoảng bao nhiêu GB ạ (128/256/512)?",
                 kind="min_constraint", spec_key="storage_gb", unit="GB",
                 extract=(r"(\d+)\s*gb",)),
        ),
        priorities=(
            Priority("pin_trau", ("pin trâu", "pin khỏe", "pin lâu", "pin tốt", "trâu bò"), "max_spec", "battery_mah", weight=4.0),
            Priority("choi_game", ("chơi game", "gaming", "chiến game", "game nặng", "cấu hình cao", "mạnh"), "max_spec", "ram_gb", weight=4.0),
            Priority("bo_nho_lon", ("bộ nhớ lớn", "nhiều bộ nhớ", "lưu nhiều", "dung lượng lớn"), "max_spec", "storage_gb", weight=3.0),
            Priority("sac_nhanh", ("sạc nhanh", "sac nhanh", "sạc siêu nhanh"), "max_spec", "charge_w", weight=2.0),
            Priority("5g", ("5g", "mạng 5g"), "bool", "has_5g", weight=2.0),
            Priority("gia_re", ("giá rẻ", "gia re", "rẻ", "tiết kiệm", "bình dân"), "cheap", weight=4.0),
        ),
        tradeoffs=(
            Tradeoff("Pin lớn nhất", "battery_mah", "max", "mAh"),
            Tradeoff("RAM cao nhất", "ram_gb", "max", "GB"),
            Tradeoff("Bộ nhớ lớn nhất", "storage_gb", "max", "GB"),
            Tradeoff("Sạc nhanh nhất", "charge_w", "max", "W"),
            Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price"),
        ),
    ),
    # ---- Laptop ------------------------------------------------------------ #
    Category(
        code=44, slug="laptop", display="Laptop", sheet="Laptop",
        aliases=("laptop", "lap top", "máy tính xách tay", "may tinh xach tay",
                 "macbook", "notebook", "lap"),
        specs=(
            Spec("ram_gb", "RAM", "num", "GB"),
            Spec("storage_gb", "Ổ cứng", "gb", "GB"),
            Spec("screen_inch", "Kích thước màn hình", "num", '"'),
            Spec("cpu", "Công nghệ CPU", "text"),
            Spec("gpu", "Card màn hình", "text"),
            Spec("has_dgpu", "Card màn hình", "flag:rời"),
            Spec("refresh_hz", "Tần số quét", "num", "Hz"),
            Spec("battery_wh", "Thông tin Pin", "max", "Wh"),
            Spec("os", "Hệ điều hành", "text"),
        ),
        desc_specs=("Công nghệ CPU", "RAM", "Ổ cứng", "Card màn hình", "Kích thước màn hình", "Hệ điều hành"),
        slots=(
            Slot("ram_gb", "RAM (GB)",
                 question="Anh/chị cần RAM khoảng bao nhiêu ạ (8/16/32GB)?",
                 kind="min_constraint", spec_key="ram_gb", unit="GB",
                 extract=(r"ram\s*(\d+)",)),
        ),
        priorities=(
            Priority("do_hoa_game", ("gaming", "chơi game", "game", "đồ họa", "do hoa", "render", "dựng phim", "chỉnh sửa video"), "bool", "has_dgpu", weight=5.0),
            Priority("ram_cao", ("đa nhiệm", "da nhiem", "ram cao", "nhiều ram", "nặng"), "max_spec", "ram_gb", weight=3.0),
            Priority("luu_tru_lon", ("ổ cứng lớn", "nhiều dung lượng", "ssd lớn", "lưu nhiều"), "max_spec", "storage_gb", weight=2.0),
            Priority("pin_trau", ("pin trâu", "pin lâu", "pin khỏe", "dùng lâu"), "max_spec", "battery_wh", weight=3.0),
            Priority("van_phong", ("văn phòng", "van phong", "học tập", "sinh viên", "word", "excel", "cơ bản"), "cheap", weight=3.0),
            Priority("gia_re", ("giá rẻ", "gia re", "rẻ", "tiết kiệm", "bình dân"), "cheap", weight=4.0),
        ),
        tradeoffs=(
            Tradeoff("RAM cao nhất", "ram_gb", "max", "GB"),
            Tradeoff("Ổ cứng lớn nhất", "storage_gb", "max", "GB"),
            Tradeoff("Màn hình lớn nhất", "screen_inch", "max", '"'),
            Tradeoff("Pin lớn nhất", "battery_wh", "max", "Wh"),
            Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price"),
        ),
    ),
    # ---- Tivi -------------------------------------------------------------- #
    Category(
        code=1942, slug="tivi", display="Tivi", sheet="Tivi",
        aliases=("tivi", "ti vi", "smart tivi", "android tivi", "google tivi", "màn hình tivi", "tv"),
        specs=(
            Spec("screen_inch", "Kích cỡ màn hình", "num", "inch"),
            Spec("resolution", "Độ phân giải", "text"),
            Spec("panel", "Loại màn hình", "text"),
            Spec("tv_type", "Loại Tivi", "text"),
            Spec("refresh_hz", "Tần số quét thực", "max", "Hz"),
            Spec("speaker_w", "Tổng công suất loa", "num", "W"),
            Spec("os", "Hệ điều hành", "text"),
            Spec("is_4k", "Độ phân giải", "flag:4k"),
            Spec("is_oled", "Loại màn hình", "flag:oled"),
            Spec("is_qled", "Loại màn hình", "flag:qled"),
        ),
        desc_specs=("Loại Tivi", "Kích cỡ màn hình", "Độ phân giải", "Loại màn hình", "Hệ điều hành"),
        slots=(
            Slot("screen_inch", "kích thước màn hình (inch)",
                 question="Anh/chị muốn tivi khoảng bao nhiêu inch ạ (43/55/65...) hoặc phòng rộng bao nhiêu?",
                 kind="proximity", spec_key="screen_inch", unit="inch", weight=5.0,
                 extract=(r"(\d+)\s*inch", r"(\d+)\s*['\"]", r"tivi\s*(\d{2})\b"), primary=True),
        ),
        priorities=(
            Priority("4k", ("4k", "ultra hd", "nét", "sắc nét"), "bool", "is_4k", weight=3.0),
            Priority("oled", ("oled",), "bool", "is_oled", weight=3.0),
            Priority("qled", ("qled",), "bool", "is_qled", weight=3.0),
            Priority("man_lon", ("màn lớn", "man lon", "màn to", "rạp phim", "xem phim"), "max_spec", "screen_inch", weight=3.0),
            Priority("muot", ("mượt", "muot", "120hz", "thể thao", "chơi game"), "max_spec", "refresh_hz", weight=2.0),
            Priority("gia_re", ("giá rẻ", "gia re", "rẻ", "tiết kiệm", "bình dân"), "cheap", weight=4.0),
        ),
        tradeoffs=(
            Tradeoff("Màn hình lớn nhất", "screen_inch", "max", "inch"),
            Tradeoff("Tần số quét cao nhất", "refresh_hz", "max", "Hz"),
            Tradeoff("Loa to nhất", "speaker_w", "max", "W"),
            Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price"),
        ),
    ),
    # ---- Loa, Tai nghe ----------------------------------------------------- #
    Category(
        code=13698, slug="tai_nghe", display="Loa, Tai nghe", sheet="Loa, Tai nghe",
        aliases=("tai nghe", "headphone", "earbuds", "earphone", "airpods",
                 "loa bluetooth", "loa kéo", "loa", "speaker", "tai nghe bluetooth"),
        specs=(
            Spec("product_type", "Loại sản phẩm", "text"),
            Spec("battery_h", "Thời lượng pin tai nghe", "num", "giờ"),
            Spec("power_w", "Tổng công suất", "num", "W"),
            Spec("connection", "Công nghệ kết nối", "text"),
            Spec("is_wireless", "Công nghệ kết nối", "flag:bluetooth"),
        ),
        desc_specs=("Loại sản phẩm", "Công nghệ kết nối", "Tổng công suất", "Thời lượng pin tai nghe"),
        priorities=(
            Priority("khong_day", ("không dây", "khong day", "bluetooth", "wireless"), "bool", "is_wireless", weight=3.0),
            Priority("loa_to", ("công suất lớn", "loa to", "âm thanh lớn", "mạnh", "bass"), "max_spec", "power_w", weight=3.0),
            Priority("pin_trau", ("pin trâu", "pin lâu", "pin khỏe", "dùng lâu"), "max_spec", "battery_h", weight=2.0),
            Priority("gia_re", ("giá rẻ", "gia re", "rẻ", "tiết kiệm", "bình dân"), "cheap", weight=4.0),
        ),
        tradeoffs=(
            Tradeoff("Công suất lớn nhất", "power_w", "max", "W"),
            Tradeoff("Pin lâu nhất", "battery_h", "max", "giờ"),
            Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price"),
        ),
    ),
    # ---- Máy lạnh ---------------------------------------------------------- #
    Category(
        code=2002, slug="may_lanh", display="Máy lạnh", sheet="Máy lạnh",
        aliases=("máy lạnh", "may lanh", "điều hòa", "dieu hoa", "máy điều hòa", "điều hoà"),
        specs=(
            Spec("hp", "Công suất làm lạnh", "num", "HP"),
            Spec("btu", "Công suất làm lạnh", "max", "BTU"),
            Spec("has_inverter", "Inverter", "flag:inverter"),
            Spec("noise_db", "Độ ồn trung bình (được đo trong phòng thí nghiệm)", "min", "dB"),
            Spec("power_kwh", "Tiêu thụ điện", "num", "kWh"),
            Spec("gas", "Loại Gas", "text"),
            Spec("mode_type", "Loại máy", "text"),
        ),
        ranges=(RangeSpec("area", "Phạm vi làm lạnh hiệu quả", "area"),),
        desc_specs=("Loại máy", "Công suất làm lạnh", "Inverter", "Phạm vi làm lạnh hiệu quả"),
        slots=(
            Slot("area_m2", "diện tích phòng (m²)",
                 question="Phòng mình rộng khoảng bao nhiêu m² ạ (hoặc phòng ngủ / phòng khách)?",
                 kind="range_fit", range_key="area", unit="m²", weight=6.0,
                 extract=(r"(\d+(?:[.,]\d+)?)\s*m2", r"(\d+(?:[.,]\d+)?)\s*m²", r"phòng\s*(\d+)\s*m"), primary=True,
                 hardness="hard", missing_policy="exclude"),
        ),
        priorities=(
            Priority("tiet_kiem_dien", ("tiết kiệm điện", "tiet kiem dien", "inverter", "ít điện", "tiết kiệm"), "bool", "has_inverter", weight=4.0),
            Priority("chay_em", ("chạy êm", "êm", "ít ồn", "yên tĩnh", "phòng ngủ", "im lặng"), "min_spec", "noise_db", weight=3.0),
            Priority("hai_chieu", ("2 chiều", "hai chiều", "sưởi", "làm ấm", "mùa đông"), "text", "mode_type", value="2 chiều", weight=3.0),
            Priority("lam_lanh_nhanh", ("làm lạnh nhanh", "lạnh sâu", "lạnh nhanh", "mát nhanh"), "max_spec", "btu", weight=2.0),
            Priority("gia_re", ("giá rẻ", "gia re", "rẻ", "tiết kiệm chi phí", "bình dân"), "cheap", weight=3.0),
        ),
        tradeoffs=(
            Tradeoff("Công suất lớn nhất", "btu", "max", "BTU"),
            Tradeoff("Chạy êm nhất", "noise_db", "min", "dB"),
            Tradeoff("Ít tốn điện nhất", "power_kwh", "min", "kWh"),
            Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price"),
        ),
    ),
    # ---- Tủ lạnh ----------------------------------------------------------- #
    Category(
        code=1943, slug="tu_lanh", display="Tủ lạnh", sheet="Tủ lạnh",
        aliases=("tủ lạnh", "tu lanh", "side by side", "multi door", "ngăn đá",
                 "ngan da", "tủ 2 cánh", "tủ 4 cánh", "french door"),
        specs=(
            Spec("usable_capacity_l", "Dung tích sử dụng", "num", "lít"),
            Spec("freezer_l", "Dung tích ngăn đá", "num", "lít"),
            Spec("fridge_l", "Dung tích ngăn lạnh", "num", "lít"),
            Spec("type", "Kiểu tủ", "text"),
            Spec("has_inverter", "Công nghệ tiết kiệm điện", "flag:inverter"),
            Spec("power_kwh_year", "Công suất tiêu thụ công bố theo TCVN", "num", "kWh/năm"),
            Spec("water_dispenser", "Lấy nước ngoài", "yesno"),
            Spec("auto_ice", "Làm đá tự động", "yesno"),
            Spec("width_cm", "Kích thước - Khối lượng", "dimension:width", "cm"),
            Spec("height_cm", "Kích thước - Khối lượng", "dimension:height", "cm"),
            Spec("depth_cm", "Kích thước - Khối lượng", "dimension:depth", "cm"),
        ),
        ranges=(RangeSpec("household", "Dung tích sử dụng", "people"),),
        desc_specs=("Kiểu tủ", "Dung tích sử dụng", "Công nghệ tiết kiệm điện"),
        slots=(
            Slot("household_size", "số người dùng",
                 question="Nhà mình khoảng mấy người dùng ạ?",
                 kind="range_fit", range_key="household", weight=5.0,
                 extract=(r"(\d+)\s*người", r"gia đình\s*(\d+)", r"nhà\s*(\d+)\s*người"), primary=True),
            Slot("capacity_l", "dung tích (lít)",
                 question="Anh/chị muốn dung tích khoảng bao nhiêu lít ạ?",
                 kind="proximity", spec_key="usable_capacity_l", unit="lít", weight=3.0,
                 extract=(r"(\d+)\s*l[íi]t", r"(\d+)\s*l\b")),
            Slot("max_width_cm", "chiều ngang tối đa (cm)",
                 question="Khoảng đặt tủ rộng tối đa bao nhiêu cm ạ?",
                 kind="max_constraint", spec_key="width_cm", unit="cm", weight=4.0,
                 extract=(r"(?:ngang|rộng|rong)\s*(?:tối đa|toi da|max)?\s*(\d+(?:[.,]\d+)?)",),
                 hardness="hard", missing_policy="exclude"),
        ),
        priorities=(
            Priority("tiet_kiem_dien", ("tiết kiệm điện", "tiet kiem dien", "inverter", "ít điện", "tiết kiệm"), "bool", "has_inverter", weight=4.0),
            Priority("side_by_side", ("side by side", "sbs", "tủ to", "4 cánh", "multi door", "nhiều cánh"), "text", "type", value="side by side", weight=3.0),
            Priority("lay_nuoc", ("lấy nước ngoài", "lay nuoc", "lấy nước", "nước ngoài"), "bool", "water_dispenser", weight=2.0),
            Priority("dung_tich_lon", ("dung tích lớn", "trữ nhiều", "to", "rộng"), "max_spec", "usable_capacity_l", weight=3.0),
            Priority("gia_re", ("giá rẻ", "gia re", "rẻ", "tiết kiệm chi phí", "bình dân"), "cheap", weight=3.0),
        ),
        tradeoffs=(
            Tradeoff("Dung tích lớn nhất", "usable_capacity_l", "max", "lít"),
            Tradeoff("Ngăn đá lớn nhất", "freezer_l", "max", "lít"),
            Tradeoff("Ít tốn điện nhất", "power_kwh_year", "min", "kWh/năm"),
            Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price"),
        ),
    ),
    # ---- Máy giặt ---------------------------------------------------------- #
    Category(
        code=1944, slug="may_giat", display="Máy giặt", sheet="Máy giặt",
        aliases=("máy giặt", "may giat", "giặt sấy", "giat say", "máy giặt sấy"),
        specs=(
            Spec("wash_kg", "Khối lượng giặt", "num", "kg"),
            Spec("type", "Loại máy giặt", "text"),
            Spec("has_inverter", "Loại Inverter", "flag:inverter"),
            Spec("spin_rpm", "Tốc độ quay vắt tối đa", "num", "vòng/phút"),
            Spec("motor_type", "Kiểu động cơ", "text"),
        ),
        ranges=(RangeSpec("household", "Số người sử dụng", "people"),),
        desc_specs=("Loại máy giặt", "Khối lượng giặt", "Số người sử dụng"),
        slots=(
            Slot("wash_kg", "khối lượng giặt (kg)",
                 question="Nhà mình mấy người, hoặc cần giặt khoảng bao nhiêu kg mỗi lần ạ?",
                 kind="proximity", spec_key="wash_kg", unit="kg", weight=5.0,
                 extract=(r"(\d+(?:[.,]\d+)?)\s*kg",), primary=True),
            Slot("household_size", "số người dùng",
                 question="Nhà mình khoảng mấy người ạ?",
                 kind="range_fit", range_key="household", weight=3.0,
                 extract=(r"(\d+)\s*người", r"gia đình\s*(\d+)")),
        ),
        priorities=(
            Priority("cua_truoc", ("cửa trước", "cua truoc", "lồng ngang", "cửa ngang"), "text", "type", value="trước", weight=3.0),
            Priority("cua_tren", ("cửa trên", "cua tren", "lồng đứng", "cửa đứng"), "text", "type", value="trên", weight=3.0),
            Priority("tiet_kiem_dien", ("tiết kiệm điện", "tiet kiem dien", "inverter", "ít điện", "tiết kiệm"), "bool", "has_inverter", weight=3.0),
            Priority("giat_nhieu", ("giặt nhiều", "tải lớn", "nhiều đồ", "gia đình đông"), "max_spec", "wash_kg", weight=3.0),
            Priority("gia_re", ("giá rẻ", "gia re", "rẻ", "tiết kiệm chi phí", "bình dân"), "cheap", weight=3.0),
        ),
        tradeoffs=(
            Tradeoff("Giặt được nhiều nhất", "wash_kg", "max", "kg"),
            Tradeoff("Vắt nhanh nhất", "spin_rpm", "max", "vòng/phút"),
            Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price"),
        ),
    ),
    # ---- Máy hút bụi ------------------------------------------------------- #
    Category(
        code=12298, slug="may_hut_bui", display="Máy hút bụi gia đình", sheet="Máy hút bụi gia đình",
        aliases=("máy hút bụi", "may hut bui", "robot hút bụi", "robot lau nhà",
                 "hút bụi cầm tay", "máy hút bụi không dây", "robot"),
        specs=(
            # Handhelds report "Công suất hút"; robots report "Lực hút tối đa".
            # Both map onto suction_pa (the later spec wins when present).
            Spec("suction_pa", "Công suất hút", "num", "Pa"),
            Spec("suction_pa", "Lực hút tối đa", "num", "Pa"),
            Spec("power_w", "Công suất hoạt động", "num", "W"),
            Spec("filter", "Bộ lọc", "text"),
            Spec("type", "Loại máy", "text"),
            Spec("area_m2", "Diện tích sử dụng", "num", "m²"),
            Spec("noise_db", "Độ ồn cao nhất", "num", "dB"),
            Spec("noise_db", "Độ ồn", "num", "dB"),
        ),
        desc_specs=("Loại máy", "Công suất hút", "Bộ lọc"),
        priorities=(
            Priority("robot", ("robot", "tự động", "tu dong", "lau nhà", "tự hành"), "text", "type", value="robot", weight=4.0),
            Priority("khong_day", ("không dây", "khong day", "cầm tay", "cordless"), "text", "type", value="không dây", weight=3.0),
            Priority("hut_manh", ("hút mạnh", "lực hút", "mạnh", "sạch sâu"), "max_spec", "suction_pa", weight=3.0),
            Priority("gia_re", ("giá rẻ", "gia re", "rẻ", "tiết kiệm", "bình dân"), "cheap", weight=3.0),
        ),
        tradeoffs=(
            Tradeoff("Lực hút mạnh nhất", "suction_pa", "max", "Pa"),
            Tradeoff("Chạy êm nhất", "noise_db", "min", "dB"),
            Tradeoff("Giá tốt nhất", "price_vnd", "min", fmt="price"),
        ),
    ),
)

# --------------------------------------------------------------------------- #
# Generic categories — built on the fly for the long-tail families so every
# product in the crawl stays searchable/advisable (ranked by budget + rating +
# units sold) even without a hand-written config.
# --------------------------------------------------------------------------- #


def _generic_registry() -> dict[str, Category]:
    """Distinct catalog categories not already deeply configured."""
    from app.catalog import repository

    out: dict[str, Category] = {}
    for entry in repository.distinct_categories():
        code = int(entry.get("code") or 0)
        if code in REGISTRY.by_code:
            continue
        cat = make_generic(code, entry.get("display") or entry.get("slug") or "")
        out[cat.slug] = cat
    return out


# Truly out-of-scope things the catalog does not carry at all. SalePilot must
# say so honestly instead of forcing an unrelated category.
UNSUPPORTED_TERMS: tuple[tuple[str, str, str], ...] = (
    (r"\bô ?tô\b|\boto\b|xe hơi|xe ô tô", "ô tô", ""),
    (r"xe máy|xe gắn máy|xe điện", "xe máy / xe điện", ""),
    (r"thực phẩm|đồ ăn|rau củ|thịt cá", "thực phẩm", ""),
    (r"vé máy bay|đặt phòng|khách sạn|tour du lịch", "dịch vụ du lịch", ""),
    (r"bất động sản|nhà đất|căn hộ", "bất động sản", ""),
)


REGISTRY = CategoryRegistry(
    CATEGORIES,
    unsupported_terms=UNSUPPORTED_TERMS,
    generic_categories=_generic_registry,
)
BY_SLUG = REGISTRY.by_slug
BY_CODE = REGISTRY.by_code
BY_SHEET = REGISTRY.by_sheet

get_category = REGISTRY.get_category
detect_category = REGISTRY.detect_category
detect_negated_categories = REGISTRY.detect_negated_categories
detect_unsupported = REGISTRY.detect_unsupported
