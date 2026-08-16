"""Import the real dienmayxanh.com crawl (``products_detail.json``) into MongoDB.

Each raw product is routed to a deeply-configured :class:`Category` when one
exists (điện thoại, laptop, tivi, loa/tai nghe, máy lạnh, tủ lạnh, máy giặt,
máy hút bụi) or to a generic category built from its ``category_name``
otherwise, normalized into the standard product document, de-duplicated by
``product_id`` (duplicates are skipped, per requirement), upserted into the
Mongo ``products`` collection, and written to a JSON snapshot used as the
offline fallback. SKUs no longer present in the source are pruned, so this
fully replaces the previous placeholder catalog.

Usage (from backend/):
    python -m scripts.import_products_detail --src /path/to/dmx_data
    python -m scripts.import_products_detail --src /path/to/dmx_data --snapshot-only
    python -m scripts.import_products_detail --src /path/to/dmx_data --skip-existing

Source resolution (highest priority first):
    1. --src CLI argument
    2. DMX_SRC_DIR in .env or environment
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from app.catalog import repository
from app.catalog.crawl_categories import BY_CODE, Category, make_generic, normalize_product
from app.config import get_settings
from scripts.shared import resolve_dmx_src

_SOURCE_FILENAME = "products_detail.json"
SOURCE = _SOURCE_FILENAME


def _resolve_category(product: dict[str, Any]) -> Category:
    code = int(product.get("category_id") or 0)
    cat = BY_CODE.get(code)
    if cat is not None:
        return cat
    return make_generic(code, product.get("category_name") or "Sản phẩm")


def build_catalog(json_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit("Expected a JSON array of products.")

    products: list[dict[str, Any]] = []
    seen_skus: set[str] = set()
    skipped_dupes = 0
    skipped_empty = 0
    per_cat: Counter[str] = Counter()
    deep_slugs: set[str] = set()

    for source_row, item in enumerate(raw, start=1):
        sku = str(item.get("product_id") or "").strip()
        name = str(item.get("tên sản phẩm") or "").strip()
        if not sku or not name:
            skipped_empty += 1
            continue
        if sku in seen_skus:
            skipped_dupes += 1
            continue
        cat = _resolve_category(item)
        doc = normalize_product(cat, item, SOURCE, source_row=source_row)
        seen_skus.add(sku)
        products.append(doc)
        per_cat[cat.display] += 1
        if not cat.generic:
            deep_slugs.add(cat.slug)

    priced = sum(1 for d in products if d.get("has_current_price"))
    stats = {
        "total": len(products),
        "priced": priced,
        "skipped_dupes": skipped_dupes,
        "skipped_empty": skipped_empty,
        "deep_categories": sorted(deep_slugs),
        "distinct_categories": len(per_cat),
        "per_category": per_cat,
    }
    return products, stats


def write_mongo(products: list[dict[str, Any]], *, skip_existing: bool = False) -> int:
    from pymongo import ASCENDING, UpdateOne

    settings = get_settings()
    client = repository.mongo_client(timeout_ms=5000)
    coll = client[settings.mongodb_db][settings.mongodb_products_collection]
    coll.create_index([("sku", ASCENDING)], unique=True)
    coll.create_index([("category_code", ASCENDING)])
    coll.create_index([("brand", ASCENDING)])
    coll.create_index([("price_vnd", ASCENDING)])
    coll.create_index([("rating", ASCENDING)])
    coll.create_index([("category_code", ASCENDING), ("has_current_price", ASCENDING)])

    if skip_existing:
        existing = {d["sku"] for d in coll.find({}, {"sku": 1})}
        fresh = [d for d in products if d["sku"] not in existing]
        ops = [UpdateOne({"sku": d["sku"]}, {"$setOnInsert": d}, upsert=True) for d in fresh]
    else:
        ops = [UpdateOne({"sku": d["sku"]}, {"$set": d}, upsert=True) for d in products]

    for start in range(0, len(ops), 1000):
        coll.bulk_write(ops[start : start + 1000], ordered=False)

    if not skip_existing:
        # Replace the previous catalog: drop SKUs no longer present in the source.
        current = [d["sku"] for d in products]
        coll.delete_many({"sku": {"$nin": current}})

    count = coll.count_documents({})
    client.close()
    return count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import DMX products_detail.json into MongoDB + JSON snapshot.",
        epilog="Source resolution: --src flag > DMX_SRC_DIR in .env > error",
    )
    parser.add_argument(
        "--src",
        type=Path,
        default=None,
        metavar="DIR",
        help="Directory containing products_detail.json. Falls back to DMX_SRC_DIR in .env.",
    )
    parser.add_argument("--snapshot-only", action="store_true", help="Skip MongoDB write")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Insert only SKUs not already in MongoDB (do not overwrite/prune)",
    )
    args = parser.parse_args()

    json_path = resolve_dmx_src(args.src, filename=_SOURCE_FILENAME)

    products, stats = build_catalog(json_path)
    if not products:
        raise SystemExit("No products parsed — check the JSON structure.")

    snapshot = repository.save_snapshot(products)
    print(f"Snapshot: {snapshot} ({len(products)} products)")
    print(
        f"Parsed {stats['total']} products "
        f"({stats['priced']} priced) across {stats['distinct_categories']} categories; "
        f"skipped {stats['skipped_dupes']} duplicate + {stats['skipped_empty']} empty."
    )

    if not args.snapshot_only:
        try:
            count = write_mongo(products, skip_existing=args.skip_existing)
            mode = "inserted new only" if args.skip_existing else "replaced"
            print(f"MongoDB ({mode}): '{get_settings().mongodb_products_collection}' now has {count} docs")
        except Exception as exc:  # pragma: no cover - operational path
            print(f"MongoDB write skipped ({exc}). Snapshot is still available for offline use.")

    print(f"\nDeep-rule categories: {', '.join(stats['deep_categories'])}")
    print("\nTop categories by product count:")
    for display, n in stats["per_category"].most_common(20):
        tag = "" if display in {BY_CODE[c].display for c in BY_CODE} else "  (generic)"
        print(f"  {n:5d}  {display}{tag}")


if __name__ == "__main__":
    main()
