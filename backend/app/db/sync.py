"""Synchronous SQLAlchemy engine (psycopg2) for the catalog ranking path.

The FastAPI app uses an async engine (asyncpg) for CRM/memory. The product
ranking engine in :mod:`app.catalog` is synchronous, so it reads the catalog
through this separate sync engine against the same PostgreSQL database. The ETL
scripts reuse it too.
"""

from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.config import get_settings

_settings = get_settings()
sync_engine = create_engine(_settings.postgres_dsn, echo=False, future=True, pool_pre_ping=True)
SyncSession = sessionmaker(bind=sync_engine, expire_on_commit=False, future=True)


def ensure_catalog_columns() -> None:
    """Apply additive catalog columns to databases created before the field existed."""
    with sync_engine.begin() as conn:
        columns = {column["name"] for column in inspect(conn).get_columns("products")}
        if "source_row" not in columns:
            conn.execute(text("ALTER TABLE products ADD COLUMN source_row INTEGER"))


def create_all() -> None:
    """Create every table (CRM + catalog + KB) via the sync engine."""
    from app.models.base import Base
    import app.models.entities  # noqa: F401 — ensure models are registered

    Base.metadata.create_all(sync_engine)
    ensure_catalog_columns()
