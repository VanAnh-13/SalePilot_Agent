"""Regression coverage for sandbox executable-path allowlist bypasses."""

from __future__ import annotations

import shlex
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.agent.sandbox import shell


class SandboxShellTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = SimpleNamespace(sandbox_enabled=True)
        settings_patch = patch.object(shell, "get_settings", return_value=self.settings)
        settings_patch.start()
        self.addCleanup(settings_patch.stop)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.data_root = Path(directory.name).resolve()
        root_patch = patch.object(shell, "DATA_ROOT", self.data_root)
        root_patch.start()
        self.addCleanup(root_patch.stop)

    async def test_rejects_path_qualified_command_names_before_lookup(self):
        templates = (
            "/tmp/{binary}",
            "tmp/{binary}",
            "./{binary}",
            "../{binary}",
            "{binary}/",
            "tmp/../{binary}",
            "C:/tmp/{binary}",
            "C:{binary}",
            "C:\\tmp\\{binary}",
            ".\\{binary}",
            "..\\{binary}",
            "\\\\server\\share\\{binary}",
            "\\{binary}",
        )
        with (
            patch.object(shell.shutil, "which") as lookup,
            patch.object(shell.asyncio, "create_subprocess_exec", new_callable=AsyncMock) as spawn,
        ):
            for binary in sorted(shell.ALLOW_BIN):
                for template in templates:
                    command = template.format(binary=binary)
                    with self.subTest(command=command):
                        result = await shell.run_sandbox_command(shlex.quote(command))
                        self.assertFalse(result["ok"])
                        self.assertIn("denied binary", result["error"])
                        lookup.assert_not_called()
                        spawn.assert_not_awaited()

    async def test_allowlisted_basenames_execute_only_the_path_resolved_binary(self):
        for binary in sorted(shell.ALLOW_BIN):
            resolved = str(self.data_root / "path-bin" / binary)
            process = SimpleNamespace(returncode=0, communicate=AsyncMock(return_value=(b"ok\n", b"")))
            with (
                self.subTest(binary=binary),
                patch.object(shell.shutil, "which", return_value=resolved) as lookup,
                patch.object(shell.asyncio, "create_subprocess_exec", return_value=process) as spawn,
            ):
                result = await shell.run_sandbox_command(binary)
                self.assertTrue(result["ok"])
                self.assertEqual(result["stdout"], "ok\n")
                lookup.assert_called_once_with(binary)
                spawn.assert_awaited_once_with(
                    resolved,
                    cwd=str(self.data_root),
                    stdout=shell.asyncio.subprocess.PIPE,
                    stderr=shell.asyncio.subprocess.PIPE,
                )

    async def test_resolved_binary_preserves_file_arguments(self):
        resolved = str(self.data_root / "path-bin" / "cat")
        process = SimpleNamespace(returncode=0, communicate=AsyncMock(return_value=(b"contents", b"")))
        with (
            patch.object(shell.shutil, "which", return_value=resolved) as lookup,
            patch.object(shell.asyncio, "create_subprocess_exec", return_value=process) as spawn,
        ):
            result = await shell.run_sandbox_command("cat -n 'folder/file with spaces.txt'")
            self.assertTrue(result["ok"])
            lookup.assert_called_once_with("cat")
            spawn.assert_awaited_once_with(
                resolved,
                "-n",
                "folder/file with spaces.txt",
                cwd=str(self.data_root),
                stdout=shell.asyncio.subprocess.PIPE,
                stderr=shell.asyncio.subprocess.PIPE,
            )

    async def test_missing_allowlisted_binary_does_not_spawn(self):
        with (
            patch.object(shell.shutil, "which", return_value=None) as lookup,
            patch.object(shell.asyncio, "create_subprocess_exec", new_callable=AsyncMock) as spawn,
        ):
            result = await shell.run_sandbox_command("cat")
            self.assertEqual(result, {"ok": False, "error": "binary not found on PATH: cat"})
            lookup.assert_called_once_with("cat")
            spawn.assert_not_awaited()

    async def test_non_allowlisted_binary_does_not_reach_lookup(self):
        with (
            patch.object(shell.shutil, "which") as lookup,
            patch.object(shell.asyncio, "create_subprocess_exec", new_callable=AsyncMock) as spawn,
        ):
            result = await shell.run_sandbox_command("python")
            self.assertFalse(result["ok"])
            self.assertIn("denied binary", result["error"])
            lookup.assert_not_called()
            spawn.assert_not_awaited()

    async def test_disabled_sandbox_does_not_reach_lookup(self):
        self.settings.sandbox_enabled = False
        with (
            patch.object(shell.shutil, "which") as lookup,
            patch.object(shell.asyncio, "create_subprocess_exec", new_callable=AsyncMock) as spawn,
        ):
            result = await shell.run_sandbox_command("cat")
            self.assertEqual(result, {"ok": False, "error": "sandbox disabled"})
            lookup.assert_not_called()
            spawn.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
