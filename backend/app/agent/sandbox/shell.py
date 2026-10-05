"""Read-only-ish sandbox: whitelist commands under backend/data jail."""

from __future__ import annotations

import asyncio
import shlex
import shutil
from pathlib import Path

from app.config import get_settings

ALLOW_BIN = {"date", "pwd", "ls", "wc", "head", "cat", "echo"}
DATA_ROOT = Path(__file__).resolve().parents[3] / "data"


async def run_sandbox_command(cmd: str, timeout: float = 5.0) -> dict:
    if not get_settings().sandbox_enabled:
        return {"ok": False, "error": "sandbox disabled"}

    cmd = (cmd or "").strip()
    if not cmd:
        return {"ok": False, "error": "empty command"}

    try:
        parts = shlex.split(cmd)
    except ValueError as e:
        return {"ok": False, "error": f"parse error: {e}"}

    if not parts:
        return {"ok": False, "error": "empty"}

    # Check the entire command token: basename-only validation would allow
    # caller-selected executable paths to bypass the PATH lookup below.
    binary = parts[0]
    if binary not in ALLOW_BIN:
        return {"ok": False, "error": f"denied binary '{binary}'. allow: {sorted(ALLOW_BIN)}"}

    # Resolve through PATH so the OS cannot shadow an allowlisted name with a
    # planted executable inside the jail (Windows CreateProcess searches the
    # cwd before PATH; passing an absolute path removes cwd from the hunt).
    resolved_bin = shutil.which(binary)
    if resolved_bin is None:
        return {"ok": False, "error": f"binary not found on PATH: {binary}"}

    # Jail file args under data/: resolve the ACTUAL arg against DATA_ROOT (the
    # cwd we run in) and require it to stay inside. Reject absolute paths on any
    # platform. The previous check validated a rewritten candidate while the
    # original arg was executed, and missed Windows absolute paths — both holes.
    data_root = DATA_ROOT.resolve()
    for arg in parts[1:]:
        if arg.startswith("-"):
            continue
        if binary in {"cat", "head", "wc", "ls"}:
            p = Path(arg)
            if p.is_absolute():
                return {"ok": False, "error": f"absolute paths not allowed: {arg}"}
            resolved = (data_root / arg).resolve()
            try:
                resolved.relative_to(data_root)
            except ValueError:
                return {"ok": False, "error": f"path outside data jail: {arg}"}

    # Prefer running inside data dir
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        proc = await asyncio.create_subprocess_exec(
            resolved_bin,
            *parts[1:],
            cwd=str(DATA_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            try:
                await proc.wait()  # reap the killed child, no zombie handle
            except ProcessLookupError:
                pass
            return {"ok": False, "error": "timeout"}
        return {
            "ok": proc.returncode == 0,
            "code": proc.returncode,
            "stdout": stdout.decode("utf-8", errors="replace")[:4000],
            "stderr": stderr.decode("utf-8", errors="replace")[:1000],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
