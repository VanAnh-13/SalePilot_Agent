"""Seed products + sample leads into SQLite."""

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, select

from app.db.session import async_session, init_db
from app.models.entities import Lead, Product

DATA = ROOT / "data"


async def main() -> None:
    Path(ROOT / "data").mkdir(parents=True, exist_ok=True)
    await init_db()
    products = json.loads((DATA / "products.json").read_text(encoding="utf-8"))
    async with async_session() as session:
        # Product details live in the JSON snapshot. Clear the legacy SQL mirror so it
        # cannot expose stale AC stock or prices absent from the refrigerator sheet.
        await session.execute(delete(Product))
        print(f"Loaded {len(products)} refrigerator products from JSON snapshot")

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
                    channel="zalo",
                    external_id="zalo-demo-001",
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
