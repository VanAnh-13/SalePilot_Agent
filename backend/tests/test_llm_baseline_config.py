"""Unit tests for B2 multi-provider pin resolution (no network)."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "salepilot_run_llm_baseline",
    ROOT / "scripts" / "run_llm_baseline.py",
)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


class LlmBaselineConfigTests(unittest.TestCase):
    def test_resolve_prefers_llm_api_env(self) -> None:
        env = {
            "LLM_API_BASE": "https://api.groq.com/openai/v1",
            "LLM_API_KEY": "secret-key",
            "LLM_MODEL": "llama-3.3-70b",
            "OPENAI_API_KEY": "other",
            "META_API_KEY": "meta",
        }
        with patch.dict(os.environ, env, clear=False):
            for key in ("OPENAI_BASE_URL", "META_API_BASE", "OPENAI_API_BASE", "OPENAI_MODEL", "META_MODEL", "MODEL_NAME"):
                os.environ.pop(key, None)
            pin = mod.resolve_llm_pin()
        self.assertEqual(pin["api_base"], "https://api.groq.com/openai/v1")
        self.assertEqual(pin["model"], "llama-3.3-70b")
        self.assertEqual(pin["api_key_present"], "true")
        self.assertEqual(pin["provider"], "groq")
        public = mod.pin_public_view(pin)
        self.assertNotIn("api_key", public)
        self.assertEqual(len(public["api_key_fingerprint"]), 12)

    def test_cli_overrides_env(self) -> None:
        with patch.dict(os.environ, {"LLM_API_KEY": "env-key", "LLM_MODEL": "env-model"}, clear=False):
            pin = mod.resolve_llm_pin(
                api_base="https://api.openai.com/v1",
                api_key="cli-key",
                model="gpt-4o-mini",
                provider="openai",
            )
        self.assertEqual(pin["model"], "gpt-4o-mini")
        self.assertEqual(pin["api_key"], "cli-key")
        self.assertEqual(pin["provider"], "openai")

    def test_dry_run_config_exits_zero(self) -> None:
        # --dry-run-config must be side-effect-free: no --pin-out is passed on
        # purpose, to prove main() no longer writes to the repo's real
        # experiments/results/b2_pin_<split>.json in this code path.
        with patch.dict(os.environ, {"LLM_API_KEY": "k", "LLM_MODEL": "m"}, clear=False):
            code = mod.main(["--dry-run-config", "--provider", "openai"])
        self.assertEqual(code, 0)
        real_pin_path = ROOT / "experiments" / "results" / "b2_pin_dev.json"
        if real_pin_path.is_file():
            before = real_pin_path.read_text(encoding="utf-8")
            with patch.dict(os.environ, {"LLM_API_KEY": "k", "LLM_MODEL": "m"}, clear=False):
                mod.main(["--dry-run-config", "--provider", "openai"])
            after = real_pin_path.read_text(encoding="utf-8")
            self.assertEqual(before, after, "dry-run-config must not modify the real pin file")

    def test_allow_unavailable_without_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "b2.jsonl"
            pin_out = Path(tmp) / "pin.json"
            env = {k: "" for k in (
                "LLM_API_KEY", "OPENAI_API_KEY", "META_API_KEY", "ANTHROPIC_API_KEY",
            )}
            with patch.dict(os.environ, env, clear=False):
                code = mod.main(
                    [
                        "--split",
                        "dev",
                        "--output",
                        str(out),
                        "--pin-out",
                        str(pin_out),
                        "--allow-unavailable",
                    ]
                )
            self.assertEqual(code, 0)
            report = out.with_suffix(".unavailable.json")
            self.assertTrue(report.is_file())
            data = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "unavailable")
            self.assertEqual(data["condition"], "B2_llm_single_agent")


if __name__ == "__main__":
    unittest.main()
