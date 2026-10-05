"""Offline contract smoke for the FastAPI endpoints used by the stdio MCP server."""

import asyncio

import httpx

from app.db.session import init_db
from app.main import app


async def main() -> None:
    await init_db()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://salepilot.test") as client:
        products = await client.get(
            "/mcp/products",
            params={
                "category": "tu_lanh",
                "household_size": 4,
                "budget_vnd": 15_000_000,
                "priced_only": True,
                "limit": 2,
            },
        )
        assert products.status_code == 200, products.text
        product_page = products.json()
        assert product_page["count"] == 2 and product_page["total_count"] >= 2, product_page
        assert all(item["category_code"] == 38 for item in product_page["items"])
        fridge_skus = [item["sku"] for item in product_page["items"]]

        ac_products = await client.get(
            "/mcp/products",
            params={"category": "may_lanh", "priced_only": True, "limit": 2},
        )
        assert ac_products.status_code == 200, ac_products.text
        assert all(item["category_code"] == 36 for item in ac_products.json()["items"])

        detail = await client.get(f"/mcp/products/{fridge_skus[0]}")
        assert detail.status_code == 200, detail.text
        assert detail.json()["category_code"] == 38 and detail.json()["sku"] == fridge_skus[0]

        comparison = await client.post(
            "/mcp/product-comparisons",
            json={"skus": fridge_skus[:2]},
        )
        assert comparison.status_code == 200 and comparison.json()["ok"], comparison.text

        recommendation = await client.post(
            "/mcp/recommendations",
            json={
                "household_size": 4,
                "budget_vnd": 15_000_000,
                "priorities": ["tiet_kiem_dien"],
                "preferred_styles": ["Ngăn đá dưới"],
                "max_width_cm": 70,
            },
        )
        assert recommendation.status_code == 200 and recommendation.json()["top3"], recommendation.text

        ac_recommendation = await client.post(
            "/mcp/recommendations",
            json={
                "category": "may_lanh",
                "budget_vnd": 12_000_000,
                "priorities": ["tiet_kiem_dien", "chay_em"],
                "free_text": "phòng 20m2 chạy êm",
            },
        )
        assert ac_recommendation.status_code == 200, ac_recommendation.text
        ac_body = ac_recommendation.json()
        assert ac_body["top3"] and ac_body["category"] == "may_lanh", ac_body

        faq = await client.get("/mcp/knowledge/faq", params={"query": "bảo hành", "limit": 2})
        assert faq.status_code == 200 and faq.json()["count"] > 0, faq.text

        blocked_write = await client.post(
            "/mcp/leads",
            json={"confirmed": True, "phone": "0909999888", "interest": "Tủ lạnh"},
        )
        assert blocked_write.status_code in {401, 503}, blocked_write.text

    print("OK MCP API multi-category catalog, recommendation, FAQ, and protected lead write")


if __name__ == "__main__":
    asyncio.run(main())
