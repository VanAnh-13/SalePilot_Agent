"""Upgraded databases must gain the customer_memories unique index.

``Base.metadata.create_all`` never alters an existing table, so a deployment
created before the UniqueConstraint existed keeps accepting duplicate
(channel, external_id) rows. That also means the IntegrityError retry in
``_write_profile`` never fires. These tests pin the explicit backfill + index
migration that closes that gap.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from sqlalchemy import create_engine, inspect, text  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.models.base import Base  # noqa: E402
import app.models.entities  # noqa: E402,F401 — register tables on Base.metadata
from app.services import memory_schema  # noqa: E402

_TMP = tempfile.mkdtemp(prefix="salepilot_memory_schema_")

# customer_memories exactly as created before the UniqueConstraint existed:
# same columns and the two non-unique indexes, no uniqueness anywhere.
LEGACY_DDL = (
    """
    CREATE TABLE customer_memories (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        channel VARCHAR(32) NOT NULL,
        external_id VARCHAR(128) NOT NULL,
        profile_json TEXT NOT NULL,
        summary TEXT NOT NULL,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX ix_customer_memories_channel ON customer_memories (channel)",
    "CREATE INDEX ix_customer_memories_external_id ON customer_memories (external_id)",
)

INSERT_ROW = text(
    "INSERT INTO customer_memories (id, channel, external_id, profile_json, summary, updated_at)"
    " VALUES (:id, :channel, :external_id, :profile_json, :summary, :updated_at)"
)


def _row(id_, channel, external_id, profile, updated_at, summary="old"):
    return {
        "id": id_,
        "channel": channel,
        "external_id": external_id,
        "profile_json": profile if isinstance(profile, str) else json.dumps(profile),
        "summary": summary,
        "updated_at": updated_at,
    }


def _legacy_engine(rows=()):
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        for ddl in LEGACY_DDL:
            conn.execute(text(ddl))
        for row in rows:
            conn.execute(INSERT_ROW, row)
    return engine


def _unique_index_count(conn) -> int:
    # index_list columns: seq, name, unique, origin, partial
    return sum(1 for r in conn.execute(text("PRAGMA index_list('customer_memories')")) if r[2])


def _rows_for(conn, channel, external_id):
    return conn.execute(
        text(
            "SELECT id, profile_json, summary FROM customer_memories"
            " WHERE channel = :c AND external_id = :e ORDER BY id"
        ),
        {"c": channel, "e": external_id},
    ).all()


def _write_legacy_file(path, rows):
    db = sqlite3.connect(path)
    try:
        for ddl in LEGACY_DDL:
            db.execute(ddl)
        for r in rows:
            db.execute(
                "INSERT INTO customer_memories (id, channel, external_id, profile_json, summary,"
                " updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (r["id"], r["channel"], r["external_id"], r["profile_json"], r["summary"], r["updated_at"]),
            )
        db.commit()
    finally:
        db.close()


def _read_file_state(path):
    db = sqlite3.connect(path)
    try:
        dupes = db.execute(
            "SELECT COUNT(*) FROM (SELECT 1 FROM customer_memories GROUP BY channel, external_id"
            " HAVING COUNT(*) > 1)"
        ).fetchone()[0]
        total = db.execute("SELECT COUNT(*) FROM customer_memories").fetchone()[0]
        unique_indexes = sum(1 for r in db.execute("PRAGMA index_list('customer_memories')") if r[2])
        return dupes, total, unique_indexes
    finally:
        db.close()


LEGACY_DUPLICATES = (
    _row(1, "web", "c1", {"name": "An", "phone": "111", "interests": ["tu lanh"]}, "2026-01-01 00:00:00"),
    _row(2, "web", "c1", {"phone": "222", "notes": ["hoi bao hanh"]}, "2026-01-02 00:00:00"),
    _row(3, "web", "c2", {"name": "Binh"}, "2026-01-01 00:00:00"),
    _row(4, "other", "c1", {"name": "Chi"}, "2026-01-01 00:00:00"),
)


class MemoryUniqueIndexMigrationTests(unittest.TestCase):
    def test_legacy_duplicates_are_merged_newest_wins_and_index_created(self):
        engine = _legacy_engine(LEGACY_DUPLICATES)
        self.addCleanup(engine.dispose)
        with engine.begin() as conn:
            result = memory_schema.ensure_customer_memory_unique(conn)

        self.assertEqual((result.duplicate_groups, result.deleted_rows, result.index_created), (1, 1, True))
        merged = {"name": "An", "phone": "222", "interests": ["tu lanh"], "notes": ["hoi bao hanh"]}
        with engine.connect() as conn:
            rows = _rows_for(conn, "web", "c1")
            self.assertEqual([r.id for r in rows], [2], "the newest row must be the survivor")
            self.assertEqual(json.loads(rows[0].profile_json), merged)
            self.assertEqual(rows[0].summary, json.dumps(merged, ensure_ascii=False)[:500])
            # Unrelated customers, including the same external_id on another channel, are untouched.
            self.assertEqual([r.id for r in _rows_for(conn, "web", "c2")], [3])
            self.assertEqual([r.id for r in _rows_for(conn, "other", "c1")], [4])
            self.assertEqual(json.loads(_rows_for(conn, "web", "c2")[0].profile_json), {"name": "Binh"})

    def test_duplicate_insert_raises_integrity_error_after_migration(self):
        engine = _legacy_engine(LEGACY_DUPLICATES)
        self.addCleanup(engine.dispose)
        with engine.begin() as conn:
            memory_schema.ensure_customer_memory_unique(conn)
        with self.assertRaises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(INSERT_ROW, _row(99, "web", "c2", {}, "2026-02-01 00:00:00"))

    def test_second_run_is_a_noop(self):
        engine = _legacy_engine(LEGACY_DUPLICATES)
        self.addCleanup(engine.dispose)
        with engine.begin() as conn:
            memory_schema.ensure_customer_memory_unique(conn)
        with engine.begin() as conn:
            before = conn.execute(text("SELECT id, profile_json, summary FROM customer_memories ORDER BY id")).all()
            result = memory_schema.ensure_customer_memory_unique(conn)
            after = conn.execute(text("SELECT id, profile_json, summary FROM customer_memories ORDER BY id")).all()
            self.assertEqual(_unique_index_count(conn), 1)
        self.assertEqual((result.duplicate_groups, result.deleted_rows, result.index_created), (0, 0, False))
        self.assertEqual(before, after)

    def test_legacy_table_without_duplicates_still_gets_the_index(self):
        engine = _legacy_engine(LEGACY_DUPLICATES[2:])
        self.addCleanup(engine.dispose)
        with engine.begin() as conn:
            result = memory_schema.ensure_customer_memory_unique(conn)
            self.assertEqual(_unique_index_count(conn), 1)
        self.assertEqual((result.duplicate_groups, result.deleted_rows, result.index_created), (0, 0, True))

    def test_fresh_database_gets_no_redundant_index(self):
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)
        with engine.begin() as conn:
            self.assertEqual(_unique_index_count(conn), 1, "create_all already enforces uniqueness")
            result = memory_schema.ensure_customer_memory_unique(conn)
            self.assertEqual(_unique_index_count(conn), 1)
            index_names = {ix["name"] for ix in inspect(conn).get_indexes("customer_memories")}
            self.assertNotIn(memory_schema.INDEX_NAME, index_names)
        self.assertFalse(result.index_created)

    def test_missing_table_is_a_noop(self):
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        with engine.begin() as conn:
            result = memory_schema.ensure_customer_memory_unique(conn)
        self.assertEqual((result.duplicate_groups, result.deleted_rows, result.index_created), (0, 0, False))

    def test_updated_at_tie_breaks_on_highest_id(self):
        same = "2026-03-01 00:00:00"
        engine = _legacy_engine(
            [_row(1, "web", "t", {"a": 1, "b": 1}, same), _row(2, "web", "t", {"b": 2}, same)]
        )
        self.addCleanup(engine.dispose)
        with engine.begin() as conn:
            memory_schema.ensure_customer_memory_unique(conn)
        with engine.connect() as conn:
            rows = _rows_for(conn, "web", "t")
        self.assertEqual([r.id for r in rows], [2])
        self.assertEqual(json.loads(rows[0].profile_json), {"a": 1, "b": 2})

    def test_unreadable_profiles_are_skipped_not_fatal(self):
        engine = _legacy_engine(
            [
                _row(1, "web", "bad-new", {"a": 1}, "2026-01-01 00:00:00"),
                _row(2, "web", "bad-new", "oops not json", "2026-01-02 00:00:00"),
                _row(3, "web", "list-old", "[1, 2]", "2026-01-01 00:00:00"),
                _row(4, "web", "list-old", {"b": 2}, "2026-01-02 00:00:00"),
                _row(5, "web", "all-bad", "[1]", "2026-01-01 00:00:00", summary="s1"),
                _row(6, "web", "all-bad", "oops", "2026-01-02 00:00:00", summary="s2"),
            ]
        )
        self.addCleanup(engine.dispose)
        with engine.begin() as conn:
            memory_schema.ensure_customer_memory_unique(conn)
        with engine.connect() as conn:
            kept = _rows_for(conn, "web", "bad-new")
            self.assertEqual([r.id for r in kept], [2])
            self.assertEqual(json.loads(kept[0].profile_json), {"a": 1})
            kept = _rows_for(conn, "web", "list-old")
            self.assertEqual(json.loads(kept[0].profile_json), {"b": 2})
            kept = _rows_for(conn, "web", "all-bad")
            self.assertEqual([(r.id, r.profile_json, r.summary) for r in kept], [(6, "oops", "s2")])

    def test_full_default_shaped_profiles_keep_data_from_both_rows(self):
        """Real rows carry every default key; empty newer defaults must not erase older data."""
        from app.agent.memory.store import default_profile

        older = {
            **default_profile(),
            "name": "An",
            "interests": ["a"],
            "notes": ["n1"],
            "last_intent": "mua tu lanh",
            "purchase_history": [{"sku": "S1"}],
            "need": {"category": "tu_lanh"},
            "marketing_consent": True,
        }
        newer = {
            **default_profile(),
            "phone": "0909",
            "budget_vnd": 15_000_000,
            "interests": ["a", "b"],
            "purchase_history": [{"sku": "S1"}, {"sku": "S2"}],
            "marketing_consent": False,
        }
        engine = _legacy_engine(
            [
                _row(1, "web", "full", older, "2026-01-01 00:00:00"),
                _row(2, "web", "full", newer, "2026-01-02 00:00:00"),
            ]
        )
        self.addCleanup(engine.dispose)
        with engine.begin() as conn:
            memory_schema.ensure_customer_memory_unique(conn)
        with engine.connect() as conn:
            rows = _rows_for(conn, "web", "full")
        self.assertEqual([r.id for r in rows], [2])
        merged = json.loads(rows[0].profile_json)
        self.assertEqual(merged["name"], "An", "older value survives an empty newer default")
        self.assertEqual(merged["phone"], "0909")
        self.assertEqual(merged["budget_vnd"], 15_000_000)
        self.assertEqual(merged["interests"], ["a", "b"], "lists are unioned without repeats")
        self.assertEqual(merged["notes"], ["n1"])
        self.assertEqual(merged["last_intent"], "mua tu lanh")
        self.assertEqual(merged["purchase_history"], [{"sku": "S1"}, {"sku": "S2"}])
        self.assertEqual(merged["need"], {"category": "tu_lanh"})
        self.assertIs(merged["marketing_consent"], False, "newest consent wins; never resurrected")
        self.assertEqual(set(merged), set(default_profile()))

    def test_null_keys_do_not_crash_and_are_left_alone(self):
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        with engine.begin() as conn:
            conn.execute(
                text(
                    "CREATE TABLE customer_memories (id INTEGER PRIMARY KEY AUTOINCREMENT,"
                    " channel VARCHAR(32), external_id VARCHAR(128), profile_json TEXT,"
                    " summary TEXT, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
                )
            )
            for i in (1, 2):
                conn.execute(
                    text(
                        "INSERT INTO customer_memories (id, channel, external_id, profile_json, summary)"
                        " VALUES (:id, 'web', NULL, '{}', '')"
                    ),
                    {"id": i},
                )
        with engine.begin() as conn:
            result = memory_schema.ensure_customer_memory_unique(conn)
            total = conn.execute(text("SELECT COUNT(*) FROM customer_memories")).scalar()
        self.assertEqual((result.duplicate_groups, result.deleted_rows, result.index_created), (0, 0, True))
        self.assertEqual(total, 2)

    def test_summary_cap_matches_the_memory_store(self):
        from app.agent.memory import store

        self.assertEqual(memory_schema.PROFILE_SUMMARY_CAP, store.PROFILE_SUMMARY_CAP)

    def test_conflicting_index_name_fails_loudly(self):
        engine = _legacy_engine(LEGACY_DUPLICATES[2:])
        self.addCleanup(engine.dispose)
        with engine.begin() as conn:
            conn.execute(text(f"CREATE INDEX {memory_schema.INDEX_NAME} ON customer_memories (summary)"))
        with self.assertRaises(RuntimeError):
            with engine.begin() as conn:
                memory_schema.ensure_customer_memory_unique(conn)

    def test_postgres_serializes_with_a_table_lock_before_backfilling(self):
        conn = MagicMock()
        conn.dialect.name = "postgresql"
        memory_schema._lock_table(conn)
        statement = str(conn.execute.call_args.args[0])
        self.assertIn("LOCK TABLE customer_memories IN SHARE ROW EXCLUSIVE MODE", statement)

        sqlite_conn = MagicMock()
        sqlite_conn.dialect.name = "sqlite"
        memory_schema._lock_table(sqlite_conn)
        sqlite_conn.execute.assert_not_called()


class StartupWiringTests(unittest.IsolatedAsyncioTestCase):
    async def test_async_init_db_migrates_a_legacy_database(self):
        from app.db import session as session_module

        path = os.path.join(_TMP, "legacy_async.db")
        _write_legacy_file(path, LEGACY_DUPLICATES)
        engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
        try:
            with patch.object(session_module, "engine", engine):
                await session_module.init_db()
        finally:
            await engine.dispose()
        dupes, total, unique_indexes = _read_file_state(path)
        self.assertEqual((dupes, total, unique_indexes), (0, 3, 1))

    async def test_sync_create_all_migrates_a_legacy_database(self):
        from app.db import sync as sync_module

        path = os.path.join(_TMP, "legacy_sync.db")
        _write_legacy_file(path, LEGACY_DUPLICATES)
        engine = create_engine(f"sqlite:///{path}")
        try:
            with patch.object(sync_module, "sync_engine", engine):
                sync_module.create_all()
        finally:
            engine.dispose()
        dupes, total, unique_indexes = _read_file_state(path)
        self.assertEqual((dupes, total, unique_indexes), (0, 3, 1))


if __name__ == "__main__":
    raise SystemExit(unittest.main())
