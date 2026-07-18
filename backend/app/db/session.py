from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models.base import Base

settings = get_settings()


def _async_connect_args(url: str) -> dict:
    """Enable TLS for a remote managed Postgres (e.g. Neon) on the asyncpg driver.

    Local dev DBs (docker `postgres` service / localhost) don't serve TLS, so we
    only attach an SSL context when the host is clearly remote. asyncpg needs an
    SSLContext (it ignores libpq's `sslmode=` query param).
    """
    if not url.startswith("postgresql+asyncpg://"):
        return {}
    if any(h in url for h in ("@postgres", "localhost", "127.0.0.1")):
        return {}
    import ssl

    return {"ssl": ssl.create_default_context()}


engine = create_async_engine(
    settings.database_url, echo=False, connect_args=_async_connect_args(settings.database_url)
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    import app.models.entities  # noqa: F401 — register all tables on Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
