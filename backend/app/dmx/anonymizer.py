"""Redact PII from DMX conversation records before persistence.

Design (SRP):
  - Anonymizer has one responsibility: replace PII in a ConversationRecord
    with safe placeholder values.
  - It does NOT parse, does NOT write files — those are separate concerns.
  - The replacement patterns are declared as data (OCP): adding a new PII
    type requires only adding a pattern, not changing control flow.
  - ``AnonymizedRecord`` is a plain dataclass — no side effects.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.dmx.chat_parser import ConversationRecord, Message


# ---------------------------------------------------------------------------
# Replacement patterns — declared as data, not scattered across if-branches
# ---------------------------------------------------------------------------

# Each entry: (compiled regex, replacement string)
_TEXT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Vietnamese mobile phone: 03x, 07x, 08x, 09x — 10 digits
    (re.compile(r"\b(0[3-9]\d)\s*[-.]?\s*(\d{3})\s*[-.]?\s*(\d{4})\b"), "[PHONE]"),
    # Generic 9-11 digit number that looks like a phone
    (re.compile(r"\b\d{9,11}\b"), "[PHONE]"),
    # Email
    (re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"), "[EMAIL]"),
]

# user_info keys containing PII to replace with placeholders
_USER_INFO_PII_KEYS: frozenset[str] = frozenset({
    "phone",
    "phoneNumber",
    "phone_number",
    "email",
    "customerName",
    "customer_name",
    "name",
})

# user_info keys to keep (geo identifiers useful for delivery-time research)
_USER_INFO_KEEP_KEYS: frozenset[str] = frozenset({
    "districtid",
    "district_id",
    "provinceId",
    "province_id",
    "wardId",
    "ward_id",
    "address",   # kept but street number stripped
})

_STREET_NUMBER_RE = re.compile(r"^\d+[A-Za-z]?\s*/?\s*\d*\s*")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class AnonymizedRecord:
    source_index: int
    safe_user_info: dict[str, Any]
    messages: list[Message]
    tool_call_summary: Any          # ToolCallSummary — re-used as-is
    lasted_update: int | None
    welcome_chat: str
    has_purchase: bool
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _redact_text(text: str) -> str:
    for pattern, replacement in _TEXT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _sanitize_address(address: str) -> str:
    """Keep province/district/ward, strip street number."""
    return _STREET_NUMBER_RE.sub("", address).strip()


def _safe_user_info(raw: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in raw.items():
        if key in _USER_INFO_PII_KEYS:
            safe[key] = "[REDACTED]"
        elif key == "address" and isinstance(value, str):
            safe[key] = _sanitize_address(value)
        elif key in _USER_INFO_KEEP_KEYS:
            safe[key] = value
        else:
            # Unknown keys: redact the string value defensively
            safe[key] = "[REDACTED]" if isinstance(value, str) and value else value
    return safe


def _redact_message(msg: Message) -> Message:
    return Message(
        role=msg.role,
        content=_redact_text(msg.content),
        tool_calls=msg.tool_calls,   # tool call args kept — they reference SKUs, not PII
        extra={k: v for k, v in msg.extra.items() if k not in {"web_url", "img_url"}},
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class Anonymizer:
    """Redact PII from a ConversationRecord.

    Single responsibility: PII removal.
    Returns an AnonymizedRecord; does not mutate the input.
    """

    def anonymize(self, record: ConversationRecord) -> AnonymizedRecord:
        return AnonymizedRecord(
            source_index=record.source_index,
            safe_user_info=_safe_user_info(record.raw_user_info),
            messages=[_redact_message(m) for m in record.messages],
            tool_call_summary=record.tool_call_summary,
            lasted_update=record.lasted_update,
            welcome_chat=record.welcome_chat,
            has_purchase=record.has_purchase,
            metadata=record.metadata,
        )

    def anonymize_all(
        self, records: list[ConversationRecord]
    ) -> list[AnonymizedRecord]:
        return [self.anonymize(r) for r in records]
