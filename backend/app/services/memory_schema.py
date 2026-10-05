"""Backfill + unique index for ``customer_memories`` on upgraded databases.

``Base.metadata.create_all`` only creates missing tables, so a deployment that
predates ``CustomerMemory``'s UniqueConstraint never gains it. Without the
constraint, concurrent first writes both INSERT, and ``_write_profile``'s
IntegrityError retry never fires. This module is the explicit upgrade step: it
merges any legacy duplicates, then creates the unique index.

It takes a plain SQLAlchemy ``Connection`` so the async startup path (via
``run_sync``) and the sync ``create_all`` path share one implementation.
"""

from __future__ import annotations

import json
import logging
from typing import Any, NamedTuple

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

logger = logging.getLogger(__name__)

TABLE = "customer_memories"
COLUMNS = frozenset({"channel", "external_id"})
# Same name as the model's UniqueConstraint, so PostgreSQL treats both as one index.
INDEX_NAME = "uq_customer_memory_channel_external"
# Mirrors app.agent.memory.store.PROFILE_SUMMARY_CAP. Not imported: that module
# imports app.db.session, which imports this one (a test pins the two together).
PROFILE_SUMMARY_CAP = 500


class MigrationResult(NamedTuple):
    duplicate_groups: int
    deleted_rows: int
    index_created: bool


_NOOP = MigrationResult(0, 0, False)


def _has_unique_cover(conn: Connection) -> bool:
    """True when a unique constraint or unique index already covers (channel, external_id)."""
    inspector = inspect(conn)
    for constraint in inspector.get_unique_constraints(TABLE):
        if set(constraint["column_names"]) == COLUMNS:
            return True
    for index in inspector.get_indexes(TABLE):
        if index.get("unique") and set(index["column_names"]) == COLUMNS:
            return True
    return False


def _lock_table(conn: Connection) -> None:
    """Block concurrent writers so no duplicate can appear between backfill and index.

    PostgreSQL only; SQLite already serializes writers. SHARE ROW EXCLUSIVE
    still allows reads and conflicts with itself, so racing workers queue up.
    """
    if conn.dialect.name == "postgresql":
        conn.execute(text(f"LOCK TABLE {TABLE} IN SHARE ROW EXCLUSIVE MODE"))


def _profile_dict(raw: Any) -> dict[str, Any] | None:
    try:
        data = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _is_unset(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _item_key(item: Any) -> str:
    return json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)


def _merge_value(older: Any, newer: Any) -> Any:
    """Newer wins, except that an empty newer value never erases a real older one.

    Stored profiles always carry every default key (``load_profile`` starts from
    the defaults), so a plain overwrite would let the newer row's empty
    ``name``/``interests``/... wipe the older row's data. Lists are unioned.
    Booleans such as ``marketing_consent`` are not "empty": the newest value
    wins, so a consent that may have been revoked is never resurrected.
    """
    if _is_unset(newer):
        return older if not _is_unset(older) else newer
    if isinstance(older, list) and isinstance(newer, list):
        merged = list(older)
        seen = {_item_key(item) for item in merged}
        for item in newer:
            key = _item_key(item)
            if key not in seen:
                merged.append(item)
                seen.add(key)
        return merged
    return newer


def _merge_duplicates(conn: Connection) -> tuple[int, int]:
    """Collapse duplicate (channel, external_id) rows into the newest row.

    Profiles are merged oldest to newest (see ``_merge_value``). Unreadable or
    non-object profiles are skipped. Rows with a NULL key are left alone: NULLs
    are distinct in a unique index, so they never conflict.
    """
    groups = conn.execute(
        text(
            f"SELECT channel, external_id FROM {TABLE}"
            " WHERE channel IS NOT NULL AND external_id IS NOT NULL"
            " GROUP BY channel, external_id HAVING COUNT(*) > 1"
        )
    ).all()
    deleted = 0
    for channel, external_id in groups:
        rows = conn.execute(
            text(
                f"SELECT id, profile_json FROM {TABLE}"
                " WHERE channel = :channel AND external_id = :external_id"
                " ORDER BY updated_at, id"
            ),
            {"channel": channel, "external_id": external_id},
        ).all()
        keeper, stale = rows[-1], rows[:-1]
        merged: dict[str, Any] = {}
        readable = False
        for row in rows:
            data = _profile_dict(row.profile_json)
            if data is not None:
                for key, value in data.items():
                    merged[key] = _merge_value(merged[key], value) if key in merged else value
                readable = True
        if readable:
            payload = json.dumps(merged, ensure_ascii=False)
            conn.execute(
                text(f"UPDATE {TABLE} SET profile_json = :profile, summary = :summary WHERE id = :id"),
                {"profile": payload, "summary": payload[:PROFILE_SUMMARY_CAP], "id": keeper.id},
            )
        conn.execute(
            text(f"DELETE FROM {TABLE} WHERE id = :id"), [{"id": row.id} for row in stale]
        )
        deleted += len(stale)
    return len(groups), deleted


def ensure_customer_memory_unique(conn: Connection) -> MigrationResult:
    """Make (channel, external_id) unique on ``customer_memories``; idempotent."""
    if not inspect(conn).has_table(TABLE) or _has_unique_cover(conn):
        return _NOOP

    _lock_table(conn)
    # Another worker may have finished while we waited for the lock.
    if _has_unique_cover(conn):
        return _NOOP

    duplicate_groups, deleted_rows = _merge_duplicates(conn)
    conn.execute(
        text(f"CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME} ON {TABLE} (channel, external_id)")
    )
    if not _has_unique_cover(conn):
        # IF NOT EXISTS skipped it because an index of that name covers other columns.
        raise RuntimeError(
            f"{INDEX_NAME} exists but does not enforce uniqueness on {sorted(COLUMNS)}; "
            "drop or rename it and restart"
        )
    if deleted_rows:
        logger.warning(
            "customer_memories: merged %d duplicate profile group(s), removed %d stale row(s)",
            duplicate_groups,
            deleted_rows,
        )
    logger.info("customer_memories: created unique index %s", INDEX_NAME)
    return MigrationResult(duplicate_groups, deleted_rows, True)
