"""Shared CLI utilities for DMX data import scripts.

Provides a single ``resolve_dmx_src`` function used by every import script
so the resolution logic (Settings → env var → --src flag → error) lives in
exactly one place.

Resolution order (highest priority first):
  1. Explicit ``src`` argument passed by the caller (from ``--src`` CLI flag)
  2. ``dmx_src_dir`` field in ``app.config.Settings`` (reads from .env /
     DMX_SRC_DIR environment variable via pydantic-settings)
  3. ``SystemExit`` with a clear, actionable error message

No OS-specific paths are tried automatically anywhere in this module.
"""

from __future__ import annotations

from pathlib import Path


def resolve_dmx_src(src: Path | None, filename: str = "") -> Path:
    """Return a resolved path for a DMX data file or directory.

    Args:
        src:      Explicit path from the ``--src`` CLI argument (may be None).
        filename: If non-empty, the returned path will be ``src / filename``.
                  If empty, the directory itself is returned (for callers that
                  iterate over multiple files).

    Returns:
        Resolved ``Path`` that exists.

    Raises:
        SystemExit: If the path cannot be resolved or does not exist.
    """
    from app.config import get_settings

    resolved_dir: Path | None = None

    if src is not None:
        resolved_dir = src
    else:
        settings_dir = get_settings().dmx_src_dir
        if settings_dir:
            resolved_dir = Path(settings_dir)

    if resolved_dir is None:
        raise SystemExit(
            "DMX source directory not configured.\n"
            "Choose one of:\n"
            "  --src /path/to/dmx_data\n"
            "  Set DMX_SRC_DIR=/path/to/dmx_data in .env or environment"
        )

    target = resolved_dir / filename if filename else resolved_dir

    if not target.exists():
        raise SystemExit(
            f"Path does not exist: {target}\n"
            "Check DMX_SRC_DIR or --src points to the correct directory."
        )

    return target
