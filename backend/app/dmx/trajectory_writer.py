"""Persist anonymized conversation records to the trajectory store.

Design (SRP):
  - TrajectoryWriter has one responsibility: serialize and write
    AnonymizedRecord objects to disk in the project's standard trajectory
    format.
  - It does NOT parse, does NOT anonymize — those are separate concerns.
  - The output format is a plain dict so it can be deserialized without
    importing this module (no circular dependencies).

Output format (one file per conversation):
  {
    "source": "dmx_chat_history",
    "conversation_id": "dmx_<index:04d>",
    "user_info": { ... safe user info ... },
    "messages": [
      {
        "role": "user|assistant|tool",
        "content": "...",
        "tool_calls": [...],
      },
      ...
    ],
    "tool_calls_summary": { "total": N, "per_tool": { "search": M, ... } },
    "metadata": {
      "total_messages": N,
      "has_purchase": true,
      "lasted_update": ...,
      "label": "...",
    }
  }
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.dmx.anonymizer import AnonymizedRecord


_CONVERSATION_ID_PREFIX = "dmx"


@dataclass
class WriteResult:
    written: int
    output_dir: Path
    file_paths: list[Path]


# ---------------------------------------------------------------------------
# Serialization helpers — pure functions, no side effects
# ---------------------------------------------------------------------------

def _message_to_dict(msg: Any) -> dict[str, Any]:
    return {
        "role": msg.role,
        "content": msg.content,
        "tool_calls": msg.tool_calls,
    }


def _record_to_dict(record: AnonymizedRecord, conversation_id: str) -> dict[str, Any]:
    summary = record.tool_call_summary
    return {
        "source": "dmx_chat_history",
        "conversation_id": conversation_id,
        "user_info": record.safe_user_info,
        "messages": [_message_to_dict(m) for m in record.messages],
        "tool_calls_summary": {
            "total": summary.total,
            "per_tool": summary.per_tool,
        },
        "metadata": {
            **record.metadata,
            "has_purchase": record.has_purchase,
            "lasted_update": record.lasted_update,
        },
    }


def _conversation_id(source_index: int) -> str:
    return f"{_CONVERSATION_ID_PREFIX}_{source_index:04d}"


def _output_filename(conversation_id: str) -> str:
    return f"{conversation_id}.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class TrajectoryWriter:
    """Write AnonymizedRecord objects to disk as trajectory JSON files.

    Single responsibility: serialize + write.
    Each conversation produces one file; the output directory is created
    if it does not exist.
    """

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def write_all(self, records: list[AnonymizedRecord]) -> WriteResult:
        """Write every record to the output directory.

        Existing files are overwritten (idempotent).
        Returns a WriteResult describing what was written.
        """
        self._output_dir.mkdir(parents=True, exist_ok=True)
        written_paths: list[Path] = []

        for record in records:
            cid = _conversation_id(record.source_index)
            payload = _record_to_dict(record, cid)
            out_path = self._output_dir / _output_filename(cid)
            out_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            written_paths.append(out_path)

        return WriteResult(
            written=len(written_paths),
            output_dir=self._output_dir,
            file_paths=written_paths,
        )
