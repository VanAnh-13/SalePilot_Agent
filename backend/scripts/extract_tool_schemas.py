"""Extract tool-call schemas and intent test cases from DMX chat history.

Reads the raw chat history file, collects every tool-call invocation, and
produces two research artifacts:

  data/research/dmx_tool_schemas.json
      Per-tool statistics: call count, unique parameter combinations, and
      representative example calls.

  data/research/intent_test_cases.json
      One test case per user message that was immediately followed by a
      tool call, labelled with the tool name (proxy intent label).

Usage (from backend/):
    python -m scripts.extract_tool_schemas --src /path/to/dmx_data

Source resolution: --src flag > DMX_SRC_DIR in .env > error.

Design:
  - Each concern is a separate function (SRP).
  - No hardcoded paths — uses scripts.shared.resolve_dmx_src.
  - Tool schemas and test cases are separate outputs (SRP on data too).
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.dmx.chat_parser import ChatParser
from scripts.shared import resolve_dmx_src

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_RESEARCH_DIR = _BACKEND_ROOT / "data" / "research"
_CHAT_FILENAME = "chat_history_buy_product.json"

_MAX_EXAMPLES_PER_TOOL = 5

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schema extraction — pure functions
# ---------------------------------------------------------------------------

def _iter_tool_calls(
    conversations: list[Any],
) -> list[tuple[str, dict[str, Any], str]]:
    """Yield (tool_name, arguments, conversation_id) for every tool call.

    Arguments may arrive as a JSON string (OpenAI format) or already a dict.
    """
    results: list[tuple[str, dict[str, Any], str]] = []
    for record in conversations:
        cid = f"dmx_{record.source_index:04d}"
        for msg in record.messages:
            for tc in msg.tool_calls:
                if not isinstance(tc, dict):
                    continue
                fn = tc.get("function") or {}
                name = str(fn.get("name") or tc.get("name") or "").strip()
                if not name:
                    continue
                raw_args = fn.get("arguments") or tc.get("arguments") or {}
                if isinstance(raw_args, str):
                    try:
                        raw_args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        raw_args = {"_raw": raw_args}
                results.append((name, raw_args, cid))
    return results


def build_tool_schemas(
    tool_calls: list[tuple[str, dict[str, Any], str]],
) -> dict[str, Any]:
    """Aggregate tool calls into a schema summary per tool."""
    per_tool: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"call_count": 0, "parameter_keys": set(), "examples": []}
    )

    for name, args, cid in tool_calls:
        entry = per_tool[name]
        entry["call_count"] += 1
        entry["parameter_keys"].update(args.keys())
        if len(entry["examples"]) < _MAX_EXAMPLES_PER_TOOL:
            entry["examples"].append({"conversation_id": cid, "arguments": args})

    # Serialize: convert sets to sorted lists
    return {
        name: {
            "call_count": data["call_count"],
            "parameter_keys": sorted(data["parameter_keys"]),
            "examples": data["examples"],
        }
        for name, data in sorted(per_tool.items(), key=lambda kv: -kv[1]["call_count"])
    }


def build_intent_test_cases(conversations: list[Any]) -> list[dict[str, Any]]:
    """Build labelled intent test cases from user→tool-call message pairs.

    For each user message immediately followed by an assistant message that
    contains a tool call, emit a test case:
      { "input": "<user text>", "expected_tool": "<tool_name>", "source": "<cid>" }
    """
    cases: list[dict[str, Any]] = []
    for record in conversations:
        cid = f"dmx_{record.source_index:04d}"
        msgs = record.messages
        for i, msg in enumerate(msgs[:-1]):
            if msg.role != "user" or not msg.content.strip():
                continue
            next_msg = msgs[i + 1]
            if next_msg.role != "assistant" or not next_msg.tool_calls:
                continue
            # Use the first tool call as the intent label
            tc = next_msg.tool_calls[0]
            fn = tc.get("function") or {}
            tool_name = str(fn.get("name") or tc.get("name") or "").strip()
            if not tool_name:
                continue
            cases.append({
                "input": msg.content.strip(),
                "expected_tool": tool_name,
                "source": cid,
            })
    return cases


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def write_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    log.info("Written → %s", path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract tool-call schemas and intent test cases from DMX chat history.",
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
        "--research-dir",
        type=Path,
        default=_DEFAULT_RESEARCH_DIR,
        metavar="DIR",
        help="Output directory for research artifacts (default: data/research/).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    chat_path = resolve_dmx_src(args.src, filename=_CHAT_FILENAME)
    research_dir: Path = args.research_dir

    log.info("Parsing %s …", chat_path)
    parser = ChatParser()
    result = parser.parse_file(chat_path)

    log.info(
        "Parsed %d conversations (%d raw, %d skipped)",
        len(result.conversations),
        result.total_raw,
        result.skipped,
    )
    for warning in result.warnings:
        log.warning("  %s", warning)

    # ---- tool schemas -------------------------------------------------------
    tool_calls = _iter_tool_calls(result.conversations)
    log.info("Found %d total tool calls", len(tool_calls))

    schemas = build_tool_schemas(tool_calls)
    write_json(schemas, research_dir / "dmx_tool_schemas.json")
    log.info("Tool schemas: %d unique tools", len(schemas))

    # ---- intent test cases --------------------------------------------------
    test_cases = build_intent_test_cases(result.conversations)
    write_json(test_cases, research_dir / "intent_test_cases.json")
    log.info("Intent test cases: %d", len(test_cases))

    log.info("Done.")


if __name__ == "__main__":
    main()
