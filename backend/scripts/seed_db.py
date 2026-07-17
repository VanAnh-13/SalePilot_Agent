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
        # Always refresh product table from JSON (catalog source of truth for SQL mirror)
        await session.execute(delete(Product))
        for p in products:
            session.add(
                Product(
                    sku=p["sku"],
                    name=p["name"],
                    category=p.get("category", "may_lanh"),
                    price_vnd=p["price_vnd"],
                    stock=p["stock"],
                    description=p.get("description", ""),
                )
            )
        print(f"Seeded {len(products)} products (refreshed)")

        lead_exists = (await session.execute(select(Lead))).scalars().first()
        if not lead_exists:
            samples = [
                Lead(
                    name="Anh Minh",
                    phone="0901234567",
                    channel="web",
                    interest="Máy lạnh phòng ngủ 12m2",
                    budget_vnd=10000000,
                    status="qualified",
                    score=0.7,
                    notes="Sample seed AC",
                ),
                Lead(
                    name="Chị Lan",
                    phone="0912345678",
                    channel="zalo",
                    external_id="zalo-demo-001",
                    interest="Máy lạnh phòng khách 25m2",
                    budget_vnd=18000000,
                    status="new",
                    score=0.5,
                    notes="Sample seed AC",
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
