from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

SPEC = importlib.util.spec_from_file_location("salepilot_run_pilot", ROOT / "scripts" / "run_pilot.py")
assert SPEC and SPEC.loader
run_pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run_pilot)


class CatalogPinTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.snapshot = self.root / "canonical.json"
        self.fixture = self.root / "engineering.json"
        self.manifest = self.root / "manifest.json"
        self.snapshot.write_text("canonical", encoding="utf-8")
        self.fixture.write_text("engineering", encoding="utf-8")
        self.snapshot_hash = hashlib.sha256(self.snapshot.read_bytes()).hexdigest()
        self.fixture_hash = hashlib.sha256(self.fixture.read_bytes()).hexdigest()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def resolve(self, *, status: str, explicit_hash: str | None = None) -> tuple[str, Path, str]:
        self.manifest.write_text(
            json.dumps(
                {
                    "status": status,
                    "catalog": {"normalized_catalog_hash": self.snapshot_hash},
                }
            ),
            encoding="utf-8",
        )
        config = {
            "catalog": {
                "path": self.fixture.name,
                "sha256": self.snapshot_hash,
            }
        }
        settings = SimpleNamespace(catalog_snapshot=str(self.snapshot))
        with (
            patch.object(run_pilot, "ROOT", self.root),
            patch.object(run_pilot, "get_settings", return_value=settings),
        ):
            return run_pilot._load_catalog_pin(
                config=config,
                manifest_path=self.manifest,
                explicit_hash=explicit_hash,
            )

    def test_ready_manifest_ignores_engineering_fixture_path(self) -> None:
        expected, path, source = self.resolve(status="ready")

        self.assertEqual(expected, self.snapshot_hash)
        self.assertEqual(path, self.snapshot)
        self.assertEqual(source, "manifest")

    def test_cli_hash_ignores_engineering_fixture_path(self) -> None:
        expected, path, source = self.resolve(
            status="ready",
            explicit_hash=self.snapshot_hash,
        )

        self.assertEqual(expected, self.snapshot_hash)
        self.assertEqual(path, self.snapshot)
        self.assertEqual(source, "cli")

    def test_conditions_pin_still_checks_engineering_fixture_path(self) -> None:
        with self.assertRaisesRegex(SystemExit, "pinned catalog file hash mismatch"):
            self.resolve(status="blocked")

    def test_pilot_rejects_llm_baseline_condition(self) -> None:
        cfg_path = self.root / "conditions.json"
        cfg_path.write_text(
            json.dumps(
                {
                    "conditions": [
                        "B0_price_popularity",
                        "B2_llm_single_agent",
                    ],
                    "catalog": {
                        "path": self.fixture.name,
                        "sha256": self.fixture_hash,
                    },
                }
            ),
            encoding="utf-8",
        )
        self.manifest.write_text(
            json.dumps({"status": "blocked", "catalog": {}}),
            encoding="utf-8",
        )
        argv = [
            "run_pilot.py",
            "--config",
            str(cfg_path),
            "--manifest",
            str(self.manifest),
            "--benchmark",
            str(self.root / "empty.jsonl"),
            "--out",
            str(self.root / "out.jsonl"),
        ]
        (self.root / "empty.jsonl").write_text("", encoding="utf-8")
        with (
            patch.object(run_pilot, "ROOT", self.root),
            patch.object(sys, "argv", argv),
        ):
            with self.assertRaisesRegex(SystemExit, "deterministic conditions"):
                run_pilot.main()


if __name__ == "__main__":
    unittest.main()
