#!/usr/bin/env python3
"""Build a deterministic 14-category engineering fixture catalog.

This is NOT the authorized Spec_cate_gia workbook. It unblocks offline
experiment code paths until the real workbook is provided.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.catalog.categories import CATEGORIES  # noqa: E402


def _products() -> list[dict]:
    out: list[dict] = []
    for cat in CATEGORIES:
        for i in range(1, 6):
            sku = f"{cat.code}-{i:04d}"
            # Keep every ordinary dev budget represented while retaining a
            # deliberate no-match case for the 500k stress episode.
            price = 1_000_000 * i + cat.code * 1000
            norm: dict = {}
            if cat.slug == "tu_lanh":
                norm = {
                    "usable_capacity_l": 250 + i * 20,
                    "width_cm": 55 + i * 3,
                    "height_cm": 160,
                    "depth_cm": 60,
                    "household_min": 2 + (i // 2),
                    "household_max": 4 + i // 2,
                    "has_energy_saving": i % 2 == 1,
                    "external_water": i == 5,
                    "style": "Ngăn đá dưới",
                }
            elif cat.slug == "may_lanh":
                norm = {
                    "area_min": 10 + i * 2,
                    "area_max": 16 + i * 3,
                    "btu": 9000 + i * 1000,
                    "has_inverter": True,
                    "noise_db": 40 - i,
                }
            elif cat.slug == "may_giat":
                norm = {
                    "wash_kg": 7 + i * 0.5,
                    "type": "cửa trước" if i % 2 else "cửa trên",
                    "has_dryer": i >= 4,
                    "household_min": 2,
                    "household_max": 5,
                }
            elif cat.slug == "may_say":
                norm = {"dry_kg": 6 + i}
            elif cat.slug == "may_rua_chen":
                norm = {"place_settings": 8 + i}
            elif cat.slug == "tu_dong":
                norm = {"usable_capacity_l": 100 + i * 30}
            elif cat.slug == "may_nuoc_nong":
                norm = {"type": "trực tiếp", "capacity_l": 15 + i}
            elif cat.slug == "dong_ho":
                norm = {"has_call": True, "has_health": True, "has_sim": i >= 3}
            elif cat.slug == "may_tinh_de_ban":
                norm = {"ram_gb": 8 * i, "storage_gb": 256 * i}
            elif cat.slug == "man_hinh":
                norm = {"screen_inch": 24 + i}
            elif cat.slug == "may_in":
                norm = {"type": "laser" if i % 2 else "phun"}
            elif cat.slug == "may_tinh_bang":
                norm = {"has_sim": i >= 2, "storage_gb": 64 * i, "battery": True}
            name = f"{cat.display} Fixture {i} {norm.get('usable_capacity_l') or norm.get('wash_kg') or norm.get('ram_gb') or ''}".strip()
            doc = {
                "sku": sku,
                "model_code": f"FX-{cat.slug}-{i}",
                "product_id_web": sku,
                "category_code": cat.code,
                "category": cat.slug,
                "category_display": cat.display,
                "brand": ["ABrand", "BBrand", "CBrand", "DBrand", "EBrand"][i - 1],
                "price_original_vnd": price + 500_000,
                "price_sale_vnd": price,
                "price_vnd": price,
                "has_current_price": True,
                "gift_promotion": None,
                "outstanding": None,
                "rating": 4.0 + (i * 0.1),
                "sold": 100 * i,
                "warranty": "12 tháng",
                "accessories": None,
                "color": "Đen",
                "image_url": None,
                "url": None,
                "online_only": False,
                "name": name,
                "description": f"fixture {cat.slug}",
                "norm": norm,
                "specs": {k: str(v) for k, v in norm.items()},
                "source": "experiments/fixtures/catalog_dev_fixture.json",
                "source_row": i,
                "search_text": f"{cat.display} {cat.slug} {name} {' '.join(str(v) for v in norm.values())}".casefold(),
            }
            out.append(doc)
    out.sort(key=lambda d: (int(d["category_code"]), d["sku"]))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "experiments" / "fixtures" / "catalog_dev_fixture.json",
    )
    parser.add_argument(
        "--install-snapshot",
        action="store_true",
        help="Also write backend/data/catalog_snapshot.json for local offline runs",
    )
    args = parser.parse_args()
    products = _products()
    payload = json.dumps(products, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(payload, encoding="utf-8")
    print(f"wrote {args.out} products={len(products)} sha256={digest}")
    if args.install_snapshot:
        snap = ROOT / "backend" / "data" / "catalog_snapshot.json"
        snap.parent.mkdir(parents=True, exist_ok=True)
        snap.write_text(payload, encoding="utf-8")
        print(f"installed snapshot {snap}")
    meta = {
        "role": "engineering_fixture_not_publication_source",
        "products": len(products),
        "categories": len(CATEGORIES),
        "sha256": digest,
    }
    meta_path = args.out.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
