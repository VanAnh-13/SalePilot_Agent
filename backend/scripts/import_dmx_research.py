"""Deterministic DMX research catalog import for RIVF Track 2.

Reads the owner-authorized ``products_detail.xlsx`` (products + specs sheets),
normalizes via the crawl registry, writes an isolated research snapshot, and
updates ``experiments/manifest.json`` hashes when requested.

Usage (from backend/):
    python -m scripts.import_dmx_research --snapshot-only --confirm-publication-rights
    python -m scripts.import_dmx_research --excel ../products_detail.xlsx --snapshot-only --no-manifest-update
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import openpyxl

from app.catalog.crawl_categories import BY_CODE, Category, make_generic, normalize_product

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXCEL = ROOT / "products_detail.xlsx"
MANIFEST_PATH = ROOT / "experiments" / "manifest.json"
RESEARCH_SNAPSHOT = ROOT / "backend" / "data" / "research" / "catalog_dmx_snapshot.json"
SOURCE_LABEL = "products_detail.xlsx"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json_bytes(products: list[dict[str, Any]]) -> bytes:
    return (
        json.dumps(
            products,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _resolve_category(product: dict[str, Any]) -> Category:
    code = int(product.get("category_id") or 0)
    cat = BY_CODE.get(code)
    if cat is not None:
        return cat
    return make_generic(code, product.get("category_name") or "Sản phẩm")


def _sheet_rows(ws) -> tuple[list[str], list[tuple[int, tuple[Any, ...]]]]:
    rows_iter = ws.iter_rows(values_only=True)
    header_row = next(rows_iter, None)
    if not header_row:
        raise ValueError(f"Sheet {ws.title!r} has no header row")
    headers = [str(c).strip() if c is not None else "" for c in header_row]
    if any(not h for h in headers):
        raise ValueError(f"Sheet {ws.title!r} has blank header cells")
    if len(headers) != len(set(headers)):
        raise ValueError(f"Sheet {ws.title!r} has duplicate headers")
    body: list[tuple[int, tuple[Any, ...]]] = []
    for offset, values in enumerate(rows_iter, start=2):
        if values is None or all(v in (None, "") for v in values):
            continue
        body.append((offset, values))
    return headers, body


def load_xlsx_products(excel: Path) -> list[dict[str, Any]]:
    """Load products sheet and join specs into ``spec_product`` maps."""
    wb = openpyxl.load_workbook(excel, read_only=True, data_only=True)
    try:
        if "products" not in wb.sheetnames:
            raise ValueError("Excel missing required sheet 'products'")
        if "specs" not in wb.sheetnames:
            raise ValueError("Excel missing required sheet 'specs'")

        product_headers, product_rows = _sheet_rows(wb["products"])
        required = {"product_id", "tên sản phẩm", "category_id", "category_name"}
        missing = required - set(product_headers)
        if missing:
            raise ValueError(f"products sheet missing columns: {sorted(missing)}")

        specs_headers, specs_rows = _sheet_rows(wb["specs"])
        for col in ("product_id", "spec_key", "spec_value"):
            if col not in specs_headers:
                raise ValueError(f"specs sheet missing column {col!r}")

        idx = {name: i for i, name in enumerate(product_headers)}
        specs_by_id: dict[str, dict[str, Any]] = defaultdict(dict)
        s_idx = {name: i for i, name in enumerate(specs_headers)}
        for _row_no, values in specs_rows:
            pid = str(values[s_idx["product_id"]] or "").strip()
            key = str(values[s_idx["spec_key"]] or "").strip()
            if not pid or not key:
                continue
            specs_by_id[pid][key] = values[s_idx["spec_value"]]

        products: list[dict[str, Any]] = []
        for row_no, values in product_rows:
            item = {
                product_headers[i]: values[i] if i < len(values) else None
                for i in range(len(product_headers))
            }
            pid = str(item.get("product_id") or "").strip()
            if not pid:
                continue
            item["spec_product"] = dict(specs_by_id.get(pid, {}))
            item["__row__"] = row_no
            products.append(item)
        return products
    finally:
        wb.close()


def build_catalog(excel: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_products = load_xlsx_products(excel)
    products: list[dict[str, Any]] = []
    seen: set[str] = set()
    skipped_dupes = 0
    skipped_empty = 0
    per_cat: Counter[str] = Counter()
    deep_slugs: set[str] = set()

    for item in raw_products:
        sku = str(item.get("product_id") or "").strip()
        name = str(item.get("tên sản phẩm") or "").strip()
        if not sku or not name:
            skipped_empty += 1
            continue
        if sku in seen:
            skipped_dupes += 1
            continue
        cat = _resolve_category(item)
        doc = normalize_product(
            cat,
            item,
            SOURCE_LABEL,
            source_row=int(item.get("__row__") or 0) or None,
        )
        seen.add(sku)
        products.append(doc)
        per_cat[cat.slug] += 1
        if not cat.generic:
            deep_slugs.add(cat.slug)

    products.sort(key=lambda d: (int(d.get("category_code") or 0), str(d.get("sku") or "")))
    priced = sum(1 for d in products if d.get("has_current_price"))
    stats = {
        "total": len(products),
        "priced": priced,
        "skipped_dupes": skipped_dupes,
        "skipped_empty": skipped_empty,
        "deep_categories": sorted(deep_slugs),
        "distinct_categories": len(per_cat),
        "per_category": {
            slug: {"total": count, "code": next(
                (int(p["category_code"]) for p in products if p.get("category") == slug),
                0,
            )}
            for slug, count in sorted(per_cat.items())
        },
    }
    return products, stats


def save_canonical_snapshot(products: list[dict[str, Any]], path: Path | None = None) -> tuple[Path, str]:
    payload = _canonical_json_bytes(products)
    digest = _sha256_bytes(payload)
    target = path or RESEARCH_SNAPSHOT
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", delete=False, dir=str(target.parent)) as tmp:
        tmp.write(payload)
        tmp_path = Path(tmp.name)
    tmp_path.replace(target)
    return target, digest


def validate_import_rights(
    excel: Path,
    snapshot_path: Path,
    *,
    confirm_publication_rights: bool = False,
) -> None:
    if not MANIFEST_PATH.is_file():
        raise ValueError("research manifest is required before a full DMX research import")
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    catalog = data.get("catalog") or {}
    denied = {"denied", "revoked", "not_allowed"}
    if catalog.get("rights_status") in denied:
        raise ValueError("manifest catalog rights are denied")
    if not confirm_publication_rights and catalog.get("rights_status") != "owner_confirmed_publication":
        raise ValueError(
            "manifest catalog rights are not publication-approved; "
            "pass --confirm-publication-rights after owner approval"
        )

    declared = catalog.get("source_path")
    declared_path = (ROOT / declared).resolve() if isinstance(declared, str) else None
    if declared_path is None or declared_path != excel.resolve():
        raise ValueError(
            "import source does not match manifest catalog.source_path: "
            f"{excel} != {declared}"
        )
    declared_snapshot = catalog.get("snapshot_path")
    manifest_snapshot = (
        (ROOT / declared_snapshot).resolve() if isinstance(declared_snapshot, str) else None
    )
    if manifest_snapshot is None or manifest_snapshot != snapshot_path.resolve():
        raise ValueError("import snapshot target does not match manifest catalog.snapshot_path")
    for asset in data.get("assets") or []:
        if asset.get("rights_status") in denied:
            raise ValueError(f"asset rights are denied: {asset.get('id')}")
        if asset.get("id") == "catalog_workbook":
            if (
                not confirm_publication_rights
                and asset.get("rights_status") != "owner_confirmed_publication"
            ):
                raise ValueError("catalog_workbook asset rights are not publication-approved")
            asset_path = asset.get("path")
            resolved_asset = (ROOT / asset_path).resolve() if isinstance(asset_path, str) else None
            if resolved_asset != excel.resolve():
                raise ValueError("catalog_workbook asset path does not match import source")


def update_manifest(
    *,
    raw_hash: str,
    normalized_hash: str,
    total: int,
    stats: dict[str, Any],
    source_path: str,
    snapshot_path: str,
    confirm_publication_rights: bool = False,
) -> None:
    if not MANIFEST_PATH.is_file():
        return
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    catalog = data.setdefault("catalog", {})

    if catalog.get("rights_status") in {"denied", "revoked", "not_allowed"}:
        raise ValueError("manifest catalog rights are denied; import cannot mark it ready")
    if confirm_publication_rights:
        catalog["rights_status"] = "owner_confirmed_publication"
        for asset in data.get("assets") or []:
            if asset.get("id") == "catalog_workbook":
                if asset.get("rights_status") in {"denied", "revoked", "not_allowed"}:
                    raise ValueError("manifest workbook rights are denied")
                asset["rights_status"] = "owner_confirmed_publication"
    elif catalog.get("rights_status") != "owner_confirmed_publication":
        raise ValueError(
            "manifest catalog rights are not publication-approved; "
            "pass --confirm-publication-rights after owner approval"
        )

    catalog["family"] = "dmx_crawl_products_detail"
    catalog["source_path"] = source_path
    catalog["source_present"] = True
    catalog["source_required"] = True
    catalog["raw_source_hash"] = raw_hash
    catalog["normalized_catalog_hash"] = normalized_hash
    catalog["snapshot_path"] = snapshot_path
    catalog["experiment_backend"] = "snapshot"
    catalog["expected_total_products"] = total
    per_category = stats.get("per_category") or {}
    catalog["per_category"] = per_category
    categories = sorted(per_category.keys())
    catalog["categories"] = categories
    catalog["expected_categories"] = len(categories)
    catalog["rights_status"] = "owner_confirmed_publication"
    catalog["derivative_release"] = "aggregates_and_labels_only_when_sealed"

    data["status"] = "ready"
    data["blockers"] = []
    data["updated_at"] = "2026-07-25"
    data["human_study_gate"] = "disabled"
    data.setdefault("default_optional_tasks", {})
    data["default_optional_tasks"]["task_10_ui"] = "disabled"
    data["default_optional_tasks"]["task_11_human_study"] = "disabled"

    for asset in data.get("assets") or []:
        if asset.get("id") == "catalog_workbook":
            asset["path"] = source_path
            asset["hash"] = raw_hash
            asset["rights_status"] = "owner_confirmed_publication"
            asset["role"] = "canonical_catalog_source"
            asset["required_for_experiments"] = True
            asset["notes"] = "DMX products_detail.xlsx staged at repo root; gitignored"
        if asset.get("id") == "catalog_snapshot":
            asset["path"] = snapshot_path
            asset["hash"] = normalized_hash
            asset["rights_status"] = "derived_ready"
            asset["role"] = "canonical_experiment_snapshot"
            asset["required_for_experiments"] = True
            asset["notes"] = "Normalized DMX research snapshot"

    MANIFEST_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _resolve_existing_file(path: Path) -> Path | None:
    """Resolve an existing file via absolute, cwd-relative, then repo-relative paths."""
    candidates: list[Path] = []
    if path.is_absolute():
        candidates.append(path.resolve())
    else:
        candidates.append((Path.cwd() / path).resolve())
        candidates.append((ROOT / path).resolve())
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--excel", type=Path, default=None)
    parser.add_argument("--snapshot-only", action="store_true", help="Skip Mongo writes (always true for research isolation)")
    parser.add_argument("--no-manifest-update", action="store_true")
    parser.add_argument("--snapshot-out", type=Path, default=None)
    parser.add_argument(
        "--confirm-publication-rights",
        action="store_true",
        help="Explicitly promote a pending owner-rights declaration before marking the manifest ready",
    )
    args = parser.parse_args(argv)

    excel_arg = args.excel if args.excel is not None else DEFAULT_EXCEL
    excel = _resolve_existing_file(excel_arg)
    if excel is None and args.excel is None:
        excel = DEFAULT_EXCEL if DEFAULT_EXCEL.is_file() else None
    if excel is None or not excel.is_file():
        raise SystemExit(f"Excel not found: {excel_arg}")

    if args.snapshot_out is None:
        snapshot_target = RESEARCH_SNAPSHOT
    else:
        raw_out = args.snapshot_out
        if raw_out.is_absolute():
            snapshot_target = raw_out.resolve()
        else:
            cwd_out = (Path.cwd() / raw_out).resolve()
            root_out = (ROOT / raw_out).resolve()
            # Prefer an existing parent under repo root when invoked from backend/.
            if root_out.parent.is_dir():
                snapshot_target = root_out
            else:
                snapshot_target = cwd_out

    if not args.no_manifest_update:
        validate_import_rights(
            excel,
            snapshot_target,
            confirm_publication_rights=args.confirm_publication_rights,
        )

    raw_hash = _sha256_file(excel)
    products, stats = build_catalog(excel)
    if not products:
        raise SystemExit("No products parsed from DMX workbook")

    snapshot, norm_hash = save_canonical_snapshot(products, path=snapshot_target)
    print(f"Snapshot: {snapshot} products={len(products)} sha256={norm_hash}")
    print(f"Raw source sha256={raw_hash}")
    print(
        f"Parsed {stats['total']} products ({stats['priced']} priced) "
        f"across {stats['distinct_categories']} categories; "
        f"skipped {stats['skipped_dupes']} duplicate + {stats['skipped_empty']} empty."
    )
    print(f"Deep-rule categories: {', '.join(stats['deep_categories'])}")

    if not args.no_manifest_update:
        try:
            source_rel = excel.resolve().relative_to(ROOT.resolve()).as_posix()
        except ValueError as exc:
            raise SystemExit(
                f"Excel must live inside the repo for manifest paths (got {excel})"
            ) from exc
        try:
            snapshot_rel = snapshot.resolve().relative_to(ROOT.resolve()).as_posix()
        except ValueError as exc:
            raise SystemExit(
                f"Snapshot must live inside the repo for manifest paths (got {snapshot})"
            ) from exc
        update_manifest(
            raw_hash=raw_hash,
            normalized_hash=norm_hash,
            total=int(stats["total"]),
            stats=stats,
            source_path=source_rel,
            snapshot_path=snapshot_rel,
            confirm_publication_rights=args.confirm_publication_rights,
        )
        print(f"Updated research manifest: {MANIFEST_PATH}")

    # Research importer never writes production Mongo collections.
    if not args.snapshot_only:
        print("Note: DMX research import is snapshot-isolated; Mongo write skipped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
