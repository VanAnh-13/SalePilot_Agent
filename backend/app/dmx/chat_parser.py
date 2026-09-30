"""Parse the DMX chat history file into structured conversation records.

The source file (``chat_history_buy_product.json``) uses a non-standard
JSON layout where each top-level element is a JSON object (conversation)
separated by newlines, without a surrounding array bracket.  Some objects
may also have malformed or escaped content.

Design (ISP / SRP):
  - ``ConversationRecord`` is a plain dataclass — it knows nothing about
    parsing or persistence.
  - ``RawConversation`` is the intermediate representation after JSON
    decoding but before structural validation.
  - ``ChatParser`` owns one responsibility: turn raw bytes into a list of
    ``ConversationRecord``.
  - Callers receive ``ParseResult`` so they can log warnings without the
    parser crashing on individual malformed conversations.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_SOURCE_FILENAME = "chat_history_buy_product.json"


# ---------------------------------------------------------------------------
# Data models — pure data, no parsing logic
# ---------------------------------------------------------------------------

@dataclass
class Message:
    role: str
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCallSummary:
    """Aggregated tool-call statistics for one conversation."""
    total: int
    per_tool: dict[str, int]


@dataclass
class ConversationRecord:
    """Structured, validated representation of one DMX chat conversation."""

    source_index: int
    raw_user_info: dict[str, Any]
    messages: list[Message]
    tool_call_summary: ToolCallSummary
    lasted_update: int | None
    welcome_chat: str
    has_purchase: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParseResult:
    conversations: list[ConversationRecord]
    total_raw: int
    skipped: int
    warnings: list[str]


# ---------------------------------------------------------------------------
# Internal helpers — each does exactly one thing
# ---------------------------------------------------------------------------

def _split_json_objects(text: str) -> list[str]:
    """Split concatenated JSON objects separated by newlines.

    The file may be one big array, NDJSON, or concatenated bare objects.
    We try array first, then NDJSON, then regex-based brace matching.
    """
    stripped = text.strip()

    # Case 1: wrapped in a JSON array
    if stripped.startswith("["):
        try:
            items = json.loads(stripped)
            return [json.dumps(item, ensure_ascii=False) for item in items]
        except json.JSONDecodeError:
            pass

    # Case 2: newline-delimited JSON objects
    lines = [ln.strip() for ln in stripped.splitlines() if ln.strip().startswith("{")]
    if lines:
        valid = []
        for line in lines:
            try:
                json.loads(line)
                valid.append(line)
            except json.JSONDecodeError:
                pass
        if valid:
            return valid

    # Case 3: regex brace matching — handles concatenated objects with no
    # newline separation.  O(n) scan tracking nesting depth.
    return _brace_split(stripped)


def _brace_split(text: str) -> list[str]:
    objects: list[str] = []
    depth = 0
    start = -1
    in_string = False
    escape_next = False

    for i, ch in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start != -1:
                objects.append(text[start : i + 1])
                start = -1
    return objects


def _extract_messages(raw: dict[str, Any]) -> list[Message]:
    """Extract the messages list from a raw conversation dict.

    The raw format stores messages directly as a list under several
    possible keys, or as the top-level value of the object.
    """
    for key in ("messages", "data", "conversation", "chat"):
        candidate = raw.get(key)
        if isinstance(candidate, list):
            return _parse_message_list(candidate)

    # Fallback: look for any list value that contains role-bearing dicts
    for value in raw.values():
        if isinstance(value, list) and value and isinstance(value[0], dict) and "role" in value[0]:
            return _parse_message_list(value)

    return []


def _parse_message_list(items: list[Any]) -> list[Message]:
    messages: list[Message] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "unknown").strip()
        content = str(item.get("content") or "").strip()
        tool_calls = item.get("tool_calls") or []
        if not isinstance(tool_calls, list):
            tool_calls = []
        extra = {k: v for k, v in item.items() if k not in {"role", "content", "tool_calls"}}
        messages.append(Message(role=role, content=content, tool_calls=tool_calls, extra=extra))
    return messages


def _count_tool_calls(messages: list[Message]) -> ToolCallSummary:
    per_tool: dict[str, int] = {}
    for msg in messages:
        for tc in msg.tool_calls:
            fn = (tc.get("function") or {}) if isinstance(tc, dict) else {}
            name = str(fn.get("name") or tc.get("name") or "unknown")
            per_tool[name] = per_tool.get(name, 0) + 1
    return ToolCallSummary(total=sum(per_tool.values()), per_tool=per_tool)


def _has_purchase(messages: list[Message]) -> bool:
    return any(
        "create_order" in name or "order" in name
        for msg in messages
        for tc in msg.tool_calls
        for name in [
            str((tc.get("function") or {}).get("name") or tc.get("name") or "")
        ]
    )


def _build_record(raw: dict[str, Any], index: int) -> ConversationRecord:
    messages = _extract_messages(raw)
    tool_summary = _count_tool_calls(messages)
    return ConversationRecord(
        source_index=index,
        raw_user_info=raw.get("user_info") or {},
        messages=messages,
        tool_call_summary=tool_summary,
        lasted_update=raw.get("lasted_update") or raw.get("last_update"),
        welcome_chat=str(raw.get("wellcome_chat") or raw.get("welcome_chat") or ""),
        has_purchase=_has_purchase(messages),
        metadata={
            "total_messages": len(messages),
            "label": raw.get("label") or "",
            "is_stop": raw.get("is_stop"),
        },
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class ChatParser:
    """Parse a DMX chat history file into structured conversation records.

    Single responsibility: file → list[ConversationRecord].
    Does not write files, does not anonymize — those are separate concerns.
    """

    def parse_file(self, path: Path) -> ParseResult:
        """Parse all conversations from the given file path."""
        text = path.read_text(encoding="utf-8")
        return self.parse_text(text)

    def parse_text(self, text: str) -> ParseResult:
        """Parse all conversations from a text string."""
        raw_objects = _split_json_objects(text)
        conversations: list[ConversationRecord] = []
        warnings: list[str] = []

        for i, obj_text in enumerate(raw_objects):
            try:
                raw = json.loads(obj_text)
                if not isinstance(raw, dict):
                    warnings.append(f"Object {i}: not a dict, skipped")
                    continue
                record = _build_record(raw, index=i)
                conversations.append(record)
            except (json.JSONDecodeError, Exception) as exc:  # noqa: BLE001
                warnings.append(f"Object {i}: {exc}")

        return ParseResult(
            conversations=conversations,
            total_raw=len(raw_objects),
            skipped=len(raw_objects) - len(conversations),
            warnings=warnings,
        )
