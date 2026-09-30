"""Import DMX chat history into the SalePilot trajectory store.

Parses ``chat_history_buy_product.json``, anonymizes PII, and writes one
trajectory file per conversation to ``data/trajectories/dmx_chat/``.

Usage (from backend/):
    python -m scripts.import_chat_trajectories --src /path/to/dmx_data

Source resolution: --src flag > DMX_SRC_DIR in .env > error.

Design:
  - Orchestrator only: wires together ChatParser → Anonymizer → TrajectoryWriter.
  - Each collaborator has its own SRP module; this script adds no business logic.
  - Idempotent: re-running overwrites trajectory files with fresh results.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from app.dmx.anonymizer import Anonymizer
from app.dmx.chat_parser import ChatParser
from app.dmx.trajectory_writer import TrajectoryWriter
from scripts.shared import resolve_dmx_src

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_TRAJECTORY_DIR = _BACKEND_ROOT / "data" / "trajectories" / "dmx_chat"
_CHAT_FILENAME = "chat_history_buy_product.json"

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import DMX chat history into the trajectory store.",
        epilog="Source resolution: --src flag > DMX_SRC_DIR in .env > error",
    )
    parser.add_argument(
        "--src",
        type=Path,
        default=None,
        metavar="DIR",
        help=f"Directory containing {_CHAT_FILENAME}. Falls back to DMX_SRC_DIR in .env.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=_DEFAULT_TRAJECTORY_DIR,
        metavar="DIR",
        help="Output directory for trajectory files (default: data/trajectories/dmx_chat/).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    chat_path = resolve_dmx_src(args.src, filename=_CHAT_FILENAME)
    out_dir: Path = args.out_dir

    # Step 1: parse
    log.info("Parsing %s …", chat_path)
    parse_result = ChatParser().parse_file(chat_path)
    log.info(
        "  %d conversations parsed (%d raw objects, %d skipped)",
        len(parse_result.conversations),
        parse_result.total_raw,
        parse_result.skipped,
    )
    for warning in parse_result.warnings:
        log.warning("  Parser warning: %s", warning)

    if not parse_result.conversations:
        raise SystemExit("No conversations parsed — check the source file.")

    # Step 2: anonymize
    log.info("Anonymizing PII …")
    anonymized = Anonymizer().anonymize_all(parse_result.conversations)

    # Step 3: write
    log.info("Writing trajectory files to %s …", out_dir)
    write_result = TrajectoryWriter(out_dir).write_all(anonymized)
    log.info("  Wrote %d trajectory files.", write_result.written)

    # Summary
    purchases = sum(1 for r in anonymized if r.has_purchase)
    total_msgs = sum(len(r.messages) for r in anonymized)
    log.info(
        "Done. %d conversations | %d messages total | %d with purchase",
        write_result.written,
        total_msgs,
        purchases,
    )


if __name__ == "__main__":
    main()
