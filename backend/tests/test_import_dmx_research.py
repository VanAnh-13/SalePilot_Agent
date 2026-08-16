"""Synthetic DMX research import contract tests (no full catalog required)."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from openpyxl import Workbook

from scripts import import_dmx_research as importer
from scripts.import_dmx_research import (
    build_catalog,
    main,
    save_canonical_snapshot,
    update_manifest,
    validate_import_rights,
)


def _write_mini_dmx(path: Path) -> None:
    wb = Workbook()
    products = wb.active
    products.title = "products"
    products.append(
        [
            "product_id",
            "tên sản phẩm",
            "category_name",
            "category_id",
            "brand",
            "Giá gốc",
            "Giá khuyến mãi",
            "rating_vote",
            "quantity_sold",
            "màu sắc",
            "productcode",
            "producttype",
            "onlineSaleOnly",
            "Phụ kiện đi kèm",
            "chính sách bảo hành",
            "promotion",
            "outstanding",
            "url",
            "url_image",
            "time_crawler",
        ]
    )
    products.append(
        [
            "1001",
            "Tủ lạnh test 300L",
            "Tủ lạnh",
            38,
            "TestBrand",
            15_000_000,
            12_000_000,
            4.5,
            10,
            "Bạc",
            "TB300",
            "tu-lanh",
            False,
            "",
            "24 tháng",
            "",
            "Inverter",
            "https://example.test/p/1001",
            "",
            "2026-07-01",
        ]
    )
    products.append(
        [
            "1002",
            "Máy lạnh test 1HP",
            "Máy lạnh",
            57,
            "CoolCo",
            9_000_000,
            None,
            4.0,
            3,
            "Trắng",
            "AC1HP",
            "may-lanh",
            False,
            "",
            "12 tháng",
            "",
            "",
            "https://example.test/p/1002",
            "",
            "2026-07-01",
        ]
    )
    specs = wb.create_sheet("specs")
    specs.append(["product_id", "tên sản phẩm", "spec_key", "spec_value"])
    specs.append(["1001", "Tủ lạnh test 300L", "Dung tích sử dụng", "300 lít"])
    specs.append(["1001", "Tủ lạnh test 300L", "Ngang", "60 cm"])
    specs.append(["1002", "Máy lạnh test 1HP", "Phạm vi làm lạnh hiệu quả", "Từ 9 - 12m²"])
    wb.save(path)


def _base_manifest(source_rel: str, snapshot_rel: str) -> dict:
    return {
        "schema_version": "salepilot-research-manifest-v1",
        "project": "salepilot-r",
        "status": "blocked",
        "blockers": ["canonical_source_missing"],
        "protocol_path": "docs/RIVF_TRACK2_PROTOCOL.md",
        "dataset_card_path": "docs/DATASET_CARD.md",
        "split_seed": 20260723,
        "human_study_gate": "disabled",
        "catalog": {
            "family": "dmx_crawl_products_detail",
            "source_path": source_rel,
            "source_required": True,
            "raw_source_hash": None,
            "normalized_catalog_hash": None,
            "snapshot_path": snapshot_rel,
            "schema_version": "salepilot-catalog-v1",
            "experiment_backend": "snapshot",
            "rights_status": "owner_confirmed_publication_pending_file",
        },
        "assets": [
            {
                "id": "catalog_workbook",
                "path": source_rel,
                "role": "canonical_catalog_source",
                "rights_status": "owner_confirmed_publication_pending_file",
                "required_for_experiments": True,
                "hash": None,
            },
            {
                "id": "catalog_snapshot",
                "path": snapshot_rel,
                "role": "canonical_experiment_snapshot",
                "rights_status": "pending",
                "required_for_experiments": True,
                "hash": None,
            },
        ],
        "privacy": {
            "benchmark_ids": "synthetic_or_pseudonymous",
            "allow_raw_trajectories_in_release": False,
            "allow_real_phone_email": False,
            "redaction_required": True,
        },
    }


class ImportDmxResearchTests(unittest.TestCase):
    def test_build_catalog_joins_specs_and_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            xlsx = Path(tmp) / "mini.xlsx"
            _write_mini_dmx(xlsx)
            products_a, stats_a = build_catalog(xlsx)
            products_b, stats_b = build_catalog(xlsx)
            self.assertEqual(len(products_a), 2)
            self.assertEqual(stats_a["total"], 2)
            self.assertEqual(products_a, products_b)
            self.assertEqual(stats_a, stats_b)
            by_sku = {p["sku"]: p for p in products_a}
            self.assertIn("Dung tích sử dụng", by_sku["1001"]["specs"])
            self.assertTrue(by_sku["1001"]["has_current_price"])
            ordered = sorted(
                products_a,
                key=lambda p: (int(p.get("category_code") or 0), str(p.get("sku") or "")),
            )
            self.assertEqual(products_a, ordered)

    def test_snapshot_hash_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            xlsx = root / "mini.xlsx"
            _write_mini_dmx(xlsx)
            products, _stats = build_catalog(xlsx)
            path_a = root / "a.json"
            path_b = root / "b.json"
            _, hash_a = save_canonical_snapshot(products, path=path_a)
            _, hash_b = save_canonical_snapshot(products, path=path_b)
            self.assertEqual(hash_a, hash_b)
            self.assertEqual(
                hashlib.sha256(path_a.read_bytes()).hexdigest(),
                hash_a,
            )

    def test_rights_fail_closed_without_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            xlsx = root / "products_detail.xlsx"
            snap = root / "snap.json"
            _write_mini_dmx(xlsx)
            man = root / "experiments"
            man.mkdir()
            manifest = man / "manifest.json"
            source_rel = "products_detail.xlsx"
            snapshot_rel = "snap.json"
            manifest.write_text(
                json.dumps(_base_manifest(source_rel, snapshot_rel), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            with unittest.mock.patch.object(importer, "ROOT", root), unittest.mock.patch.object(
                importer, "MANIFEST_PATH", manifest
            ):
                with self.assertRaises(ValueError):
                    validate_import_rights(xlsx, snap, confirm_publication_rights=False)

    def test_manifest_ready_with_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            xlsx = root / "products_detail.xlsx"
            snap = root / "backend" / "data" / "research" / "catalog_dmx_snapshot.json"
            snap.parent.mkdir(parents=True)
            _write_mini_dmx(xlsx)
            man = root / "experiments"
            man.mkdir()
            manifest = man / "manifest.json"
            source_rel = "products_detail.xlsx"
            snapshot_rel = "backend/data/research/catalog_dmx_snapshot.json"
            manifest.write_text(
                json.dumps(_base_manifest(source_rel, snapshot_rel), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            products, stats = build_catalog(xlsx)
            _, norm = save_canonical_snapshot(products, path=snap)
            raw = hashlib.sha256(xlsx.read_bytes()).hexdigest()
            with unittest.mock.patch.object(importer, "ROOT", root), unittest.mock.patch.object(
                importer, "MANIFEST_PATH", manifest
            ):
                validate_import_rights(xlsx, snap, confirm_publication_rights=True)
                update_manifest(
                    raw_hash=raw,
                    normalized_hash=norm,
                    total=stats["total"],
                    stats=stats,
                    source_path=source_rel,
                    snapshot_path=snapshot_rel,
                    confirm_publication_rights=True,
                )
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "ready")
            self.assertEqual(data["blockers"], [])
            self.assertEqual(data["catalog"]["raw_source_hash"], raw)
            self.assertEqual(data["catalog"]["normalized_catalog_hash"], norm)
            self.assertEqual(data["human_study_gate"], "disabled")

    def test_cli_snapshot_only_without_manifest_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            xlsx = root / "products_detail.xlsx"
            snap = root / "out" / "snap.json"
            snap.parent.mkdir(parents=True)
            _write_mini_dmx(xlsx)
            with unittest.mock.patch.object(importer, "ROOT", root), unittest.mock.patch.object(
                importer, "MANIFEST_PATH", root / "missing-manifest.json"
            ), unittest.mock.patch.object(importer, "RESEARCH_SNAPSHOT", snap), unittest.mock.patch.object(
                importer, "DEFAULT_EXCEL", xlsx
            ):
                code = main(
                    [
                        "--excel",
                        str(xlsx),
                        "--snapshot-out",
                        str(snap),
                        "--snapshot-only",
                        "--no-manifest-update",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertTrue(snap.is_file())
            products = json.loads(snap.read_text(encoding="utf-8"))
            self.assertEqual(len(products), 2)

    def test_cli_missing_excel_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nope.xlsx"
            with self.assertRaises(SystemExit) as ctx:
                main(["--excel", str(missing), "--snapshot-only", "--no-manifest-update"])
            self.assertIn("Excel not found", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
