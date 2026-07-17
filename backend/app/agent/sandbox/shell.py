"""Read-only-ish sandbox: whitelist commands under backend/data jail."""

from __future__ import annotations

import asyncio
import shlex
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

    binary = Path(parts[0]).name
    if binary not in ALLOW_BIN:
        return {"ok": False, "error": f"denied binary '{binary}'. allow: {sorted(ALLOW_BIN)}"}

    # Jail file args under data/
    for arg in parts[1:]:
        if arg.startswith("-"):
            continue
        if binary in {"cat", "head", "wc", "ls"} and (".." in arg or arg.startswith("/")):
            p = Path(arg)
            if not str(p.resolve()).startswith(str(DATA_ROOT.resolve())):
                # rewrite relative to data
                candidate = (DATA_ROOT / arg.lstrip("./")).resolve()
                if not str(candidate).startswith(str(DATA_ROOT.resolve())):
                    return {"ok": False, "error": f"path outside data jail: {arg}"}

    # Prefer running inside data dir
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        proc = await asyncio.create_subprocess_exec(
            *parts,
            cwd=str(DATA_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return {"ok": False, "error": "timeout"}
        return {
            "ok": proc.returncode == 0,
            "code": proc.returncode,
            "stdout": stdout.decode("utf-8", errors="replace")[:4000],
            "stderr": stderr.decode("utf-8", errors="replace")[:1000],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
