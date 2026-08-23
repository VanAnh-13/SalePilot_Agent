"""Seed sample leads into PostgreSQL and warm the catalog cache.

The product catalog lives in PostgreSQL (loaded by ``etl_to_postgres``) with
MongoDB as the secondary store, so this script only ensures the CRM tables exist
and holds a couple of demo leads.
"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.db.session import async_session, init_db
from app.models.entities import Lead

DATA = ROOT / "data"


async def main() -> None:
    Path(ROOT / "data").mkdir(parents=True, exist_ok=True)
    await init_db()
    async with async_session() as session:
        from app.catalog import repository

        count = repository.load()
        print(f"Catalog: {count} products from {repository.source()}")

        lead_exists = (await session.execute(select(Lead))).scalars().first()
        if not lead_exists:
            samples = [
                Lead(
                    name="Anh Minh",
                    phone="0901234567",
                    channel="web",
                    interest="Tủ lạnh cho gia đình 4 người",
                    budget_vnd=15000000,
                    status="qualified",
                    score=0.7,
                    notes="Sample seed refrigerator",
                ),
                Lead(
                    name="Chị Lan",
                    phone="0912345678",
                    channel="web",
                    external_id="web-demo-001",
                    interest="Tủ lạnh Multi Door cho gia đình 5 người",
                    budget_vnd=25000000,
                    status="new",
                    score=0.5,
                    notes="Sample seed refrigerator",
                ),
            ]
            session.add_all(samples)
            print(f"Seeded {len(samples)} leads")
        await session.commit()
    # bust catalog cache
    try:
        from app.agent.catalog_domain import reload_products

        reload_products()
    except Exception:
        pass
    print("seed_db done")


if __name__ == "__main__":
    asyncio.run(main())
