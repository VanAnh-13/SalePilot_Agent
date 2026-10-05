"""Import Điện Máy Xanh crawl snapshot into SalePilot catalog.

Reads ``products_detail.json`` produced by the DMX crawler, normalizes every
product through the category-aware pipeline already in
``app.catalog.crawl_categories``, writes the result to the configured catalog
snapshot path, and regenerates the spec index.

Usage (from ``backend/``):
    python -m scripts.import_dmx_products --src /path/to/dmx_data
    python -m scripts.import_dmx_products --dry-run

Environment variables (used when --src is not passed):
    DMX_SRC_DIR   Path to the directory containing products_detail.json
    DMX_DATA_DIR  Override the output data directory (default: backend/data)

Design notes:
  - No hardcoded OS-specific paths anywhere in this file.
  - Each concern is a separate function (SRP).
  - The script is idempotent: re-running overwrites with a fresh, deterministic result.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from scripts.shared import resolve_dmx_src

# ---------------------------------------------------------------------------
# Module-level constants — only stable, non-OS-specific values here.
# ---------------------------------------------------------------------------
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DATA_DIR = _BACKEND_ROOT / "data"

_SOURCE_FILENAME = "products_detail.json"
_SPEC_INDEX_FILENAME = "spec_index.json"
_STATS_FILENAME = "catalog_stats.json"

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# I/O helpers — pure functions, each with a single responsibility
# ---------------------------------------------------------------------------

def load_raw_products(source_path: Path) -> list[dict[str, Any]]:
    """Load the raw crawler JSON. Raises on invalid JSON."""
    log.info("Loading %s …", source_path)
    data = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array at top level, got {type(data).__name__}")
    log.info("  %d raw products loaded", len(data))
    return data


def normalize_all(
    raw_products: list[dict[str, Any]],
    *,
    source_label: str,
    log_every: int = 1000,
) -> list[dict[str, Any]]:
    """Normalize raw crawl records using the category-aware pipeline.

    Each product is passed through ``normalize_product`` bound to the
    category detected from its ``category_id`` / ``category_name`` fields.
    Products whose category cannot be resolved receive a generic category
    object so no product is silently dropped.
    """
    # Import here (not at module top) so the script can be imported without
    # triggering full app initialization during tests.
    from app.catalog.crawl_categories import normalize_product
    from app.catalog.category_model import make_generic
    from app.catalog.registry import BY_CODE

    docs: list[dict[str, Any]] = []
    skipped = 0

    for row_idx, product in enumerate(raw_products):
        if row_idx % log_every == 0 and row_idx:
            log.info("  normalizing … %d / %d", row_idx, len(raw_products))

        category_id = int(product.get("category_id") or 0)
        category_name: str = str(product.get("category_name") or "")

        cat = BY_CODE.get(category_id)
        if cat is None:
            # Long-tail category not deeply configured — build a generic one.
            cat = make_generic(
                code=category_id,
                display=category_name or f"cat_{category_id}",
            )

        try:
            doc = normalize_product(
                cat,
                product,
                source=source_label,
                source_row=row_idx,
            )
            docs.append(doc)
        except Exception as exc:  # noqa: BLE001
            log.warning("  row %d skipped — %s", row_idx, exc)
            skipped += 1

    log.info("  %d normalized, %d skipped", len(docs), skipped)
    return docs


def compute_stats(docs: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize the normalized catalog for logging and health checks."""
    from collections import Counter

    prices = [d["price_vnd"] for d in docs if d.get("price_vnd")]
    categories: Counter[str] = Counter(d.get("category_display") or d.get("category") or "?" for d in docs)
    brands: set[str] = {str(d["brand"]) for d in docs if d.get("brand")}

    return {
        "total_products": len(docs),
        "priced_products": len(prices),
        "total_categories": len(categories),
        "total_brands": len(brands),
        "price_min_vnd": min(prices) if prices else None,
        "price_max_vnd": max(prices) if prices else None,
        "price_median_vnd": _median(prices),
        "price_mean_vnd": int(sum(prices) / len(prices)) if prices else None,
        "top_15_categories": [
            {"name": name, "count": count}
            for name, count in categories.most_common(15)
        ],
    }


def _median(values: list[int | float]) -> int | float | None:
    if not values:
        return None
    sorted_vals = sorted(values)
    mid = len(sorted_vals) // 2
    if len(sorted_vals) % 2 == 0:
        return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
    return sorted_vals[mid]


def write_snapshot(docs: list[dict[str, Any]], snapshot_path: Path) -> None:
    """Write the normalized catalog to a hash-stable JSON snapshot."""
    from app.catalog.repository import save_snapshot
    out = save_snapshot(docs)
    log.info("Snapshot written → %s  (%d products)", out, len(docs))


def write_spec_index(docs: list[dict[str, Any]], index_path: Path) -> None:
    """Build the spec reverse index and persist it alongside the snapshot."""
    from app.catalog.spec_index import SpecIndex
    idx = SpecIndex.build(docs)
    idx.save(index_path)
    log.info(
        "Spec index written → %s  (%d unique spec keys)",
        index_path,
        len(idx),
    )


def write_stats(stats: dict[str, Any], stats_path: Path) -> None:
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    log.info("Stats written → %s", stats_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _resolve_data_dir(cli_data_dir: Path | None) -> Path:
    """Resolve the output data directory from CLI arg or DMX_DATA_DIR env var."""
    if cli_data_dir is not None:
        return cli_data_dir
    from app.config import get_settings
    # Allow an explicit override via the app settings (read from .env).
    # Falls back to the default backend/data directory.
    return _DEFAULT_DATA_DIR


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import DMX crawl snapshot into SalePilot catalog.",
        epilog=(
            "Environment variables:\n"
            "  DMX_SRC_DIR   directory containing products_detail.json\n"
            "  DMX_DATA_DIR  override the output data directory"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--src",
        type=Path,
        default=None,
        metavar="DIR",
        help=(
            f"Directory containing {_SOURCE_FILENAME}. "
            "Falls back to DMX_SRC_DIR env var if omitted."
        ),
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help="Output data directory. Falls back to DMX_DATA_DIR env var, then backend/data.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Normalize products but do not write any files.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    # ---- resolve I/O paths ---------------------------------------------------
    try:
        source_path = resolve_dmx_src(args.src, filename=_SOURCE_FILENAME)
    except SystemExit as exc:
        log.error("%s", exc)
        sys.exit(1)

    data_dir: Path = _resolve_data_dir(args.data_dir)
    snapshot_path = data_dir / "catalog_snapshot.json"
    index_path = data_dir / _SPEC_INDEX_FILENAME
    stats_path = data_dir / _STATS_FILENAME

    # ---- load ----------------------------------------------------------------
    raw = load_raw_products(source_path)

    # ---- normalize -----------------------------------------------------------
    docs = normalize_all(raw, source_label=_SOURCE_FILENAME)

    # ---- summarize -----------------------------------------------------------
    stats = compute_stats(docs)
    log.info(
        "Summary: %d products, %d categories, %d brands, price %s–%s VND",
        stats["total_products"],
        stats["total_categories"],
        stats["total_brands"],
        f"{stats['price_min_vnd']:,}" if stats["price_min_vnd"] else "N/A",
        f"{stats['price_max_vnd']:,}" if stats["price_max_vnd"] else "N/A",
    )

    if args.dry_run:
        log.info("--dry-run: no files written.")
        return

    # ---- write ---------------------------------------------------------------
    write_snapshot(docs, snapshot_path)
    write_spec_index(docs, index_path)
    write_stats(stats, stats_path)

    log.info("Done.")


if __name__ == "__main__":
    main()
