"""Import the public refrigerator sheet into an offline-safe JSON snapshot."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import urllib.request
from pathlib import Path
from typing import Any

SHEET_ID = "1EjYJxHmYPZJsUrpxXjkUgThioqBH4KgW"
SHEET_GID = "1924624295"
SHEET_NAME = "Tủ Lạnh"
CATEGORY_CODE = 38
SOURCE_URL = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export"
    f"?format=csv&gid={SHEET_GID}"
)
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data" / "products.json"


def _clean(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def _number(value: str | None) -> float | None:
    text = _clean(value)
    if not text:
        return None
    match = re.search(r"-?\d[\d.,]*", text.replace(" ", ""))
    if not match:
        return None
    number = match.group(0)
    separators = [index for index, char in enumerate(number) if char in ".,"]
    if not separators:
        return float(number)

    last_separator = separators[-1]
    decimal_digits = len(number) - last_separator - 1
    if len(separators) == 1:
        if decimal_digits == 3:
            return float(number.replace(".", "").replace(",", ""))
        return float(number.replace(",", "."))
    if len(separators) > 1 and decimal_digits not in {1, 2}:
        return float(number.replace(".", "").replace(",", ""))

    decimal_separator = number[last_separator]
    thousands_separator = "," if decimal_separator == "." else "."
    normalized = number.replace(thousands_separator, "").replace(decimal_separator, ".")
    return float(normalized)


def _integer(value: str | None) -> int | None:
    number = _number(value)
    return int(round(number)) if number is not None else None


def _yes_no(value: str | None) -> bool | None:
    text = (_clean(value) or "").casefold()
    if text == "có":
        return True
    if text in {"không", "không có"}:
        return False
    return None


def _people_range(label: str | None) -> tuple[int | None, int | None]:
    text = _clean(label)
    if not text:
        return None, None
    values = [int(value) for value in re.findall(r"\d+", text)]
    if "trên" in text.casefold() and values:
        return values[0] + 1, None
    if len(values) >= 2:
        return values[0], values[1]
    if values:
        return values[0], values[0]
    return None, None


def _split_features(value: str | None) -> list[str]:
    text = _clean(value)
    return [item.strip() for item in text.split("|") if item.strip()] if text else []


def _name(row: dict[str, str], capacity_l: int | None) -> str:
    brand = _clean(row.get("brand")) or "Không rõ hãng"
    style = _clean(row.get("Kiểu dáng"))
    model_code = _clean(row.get("model_code")) or "không rõ"
    parts = ["Tủ lạnh", brand]
    if style:
        parts.append(style)
    if capacity_l:
        parts.append(f"{capacity_l} lít")
    parts.append(f"(model {model_code})")
    return " ".join(parts)


def normalize_row(row: dict[str, str], source_row: int) -> dict[str, Any]:
    original_price = _integer(row.get("giá gốc"))
    sale_price = _integer(row.get("giá khuyến mãi"))
    price = sale_price or original_price
    people_min, people_max = _people_range(row.get("Số người sử dụng"))
    usable_capacity = _integer(row.get("Dung tích sử dụng"))
    energy_technology = _clean(row.get("Công nghệ tiết kiệm điện"))
    raw_specs = {
        key: value
        for key, raw_value in row.items()
        if (value := _clean(raw_value)) is not None
    }
    description_parts = [
        _clean(row.get("Công nghệ làm lạnh")),
        _clean(row.get("Công nghệ bảo quản thực phẩm")),
        _clean(row.get("Tiện ích")),
    ]
    description = " | ".join(part for part in description_parts if part)

    return {
        "sku": str(row["sku"]).strip(),
        "model_code": str(row["model_code"]).strip(),
        "product_id_web": str(row["productidweb"]).strip(),
        "category": "tu_lanh",
        "category_code": CATEGORY_CODE,
        "brand_id": _integer(row.get("brand_id")),
        "brand": _clean(row.get("brand")),
        "name": _name(row, usable_capacity),
        "style": _clean(row.get("Kiểu dáng")),
        "cooling_technology": _clean(row.get("Công nghệ làm lạnh")),
        "made_in": _clean(row.get("Sản xuất tại")),
        "release_time": _clean(row.get("Thời gian ra mắt")),
        "tray_material": _clean(row.get("Chất liệu khay ngăn lạnh")),
        "gross_capacity_l": _integer(row.get("Dung tích tổng")),
        "freezer_capacity_l": _integer(row.get("Dung tích ngăn đá")),
        "fridge_capacity_l": _integer(row.get("Dung tích ngăn lạnh")),
        "usable_capacity_l": usable_capacity,
        "energy_consumption": _number(row.get("Điện năng tiêu thụ")),
        "body_material": _clean(row.get("Chất liệu thân vỏ")),
        "household_size_label": _clean(row.get("Số người sử dụng")),
        "household_size_min": people_min,
        "household_size_max": people_max,
        "energy_saving_technology": energy_technology,
        "has_energy_saving": bool(
            energy_technology
            and energy_technology.casefold() not in {"không", "không có"}
        ),
        "food_preservation_technology": _clean(
            row.get("Công nghệ bảo quản thực phẩm")
        ),
        "features": _split_features(row.get("Tiện ích")),
        "motor_material": _clean(row.get("Chất liệu động cơ")),
        "convertible_compartment_l": _integer(row.get("Dung tích ngăn chuyển đổi")),
        "doors": _integer(row.get("Số cửa")),
        "height_cm": _number(row.get("Cao")),
        "width_cm": _number(row.get("Ngang")),
        "depth_cm": _number(row.get("Sâu")),
        "weight_kg": _number(row.get("Khối lượng máy")),
        "external_water_dispenser": _yes_no(row.get("Lấy nước ngoài")),
        "automatic_mode": _yes_no(row.get("Chế độ tự động")),
        "original_price_vnd": original_price,
        "sale_price_vnd": sale_price,
        "price_vnd": price,
        "has_current_price": price is not None,
        "gift_promotion": _clean(row.get("khuyến mãi quà")),
        "description": description,
        "source": f"google_sheet:{SHEET_ID}:gid={SHEET_GID}:row={source_row}",
        "source_url": SOURCE_URL,
        "source_sheet": SHEET_NAME,
        "source_row": source_row,
        "specs": raw_specs,
    }


def load_csv(source: str) -> str:
    if source.startswith(("http://", "https://")):
        request = urllib.request.Request(source, headers={"User-Agent": "SalePilot/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read().decode("utf-8-sig")
    return Path(source).read_text(encoding="utf-8-sig")


def import_products(source: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(load_csv(source)))
    required = {"model_code", "sku", "productidweb", "category_code", "brand"}
    missing = required.difference(reader.fieldnames or [])
    if missing:
        raise ValueError(f"Missing required sheet columns: {sorted(missing)}")

    products = []
    seen_skus: set[str] = set()
    for source_row, row in enumerate(reader, start=2):
        if _integer(row.get("category_code")) != CATEGORY_CODE:
            continue
        product = normalize_row(row, source_row)
        sku = product["sku"]
        if sku in seen_skus:
            raise ValueError(f"Duplicate SKU in source: {sku}")
        seen_skus.add(sku)
        products.append(product)

    if not products:
        raise ValueError("No category_code=38 refrigerator rows found")
    return products


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=SOURCE_URL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    products = import_products(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(products, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    priced = sum(product["has_current_price"] for product in products)
    print(f"Imported {len(products)} refrigerators ({priced} with current price)")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
