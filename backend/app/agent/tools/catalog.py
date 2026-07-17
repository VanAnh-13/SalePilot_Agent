import json

from langchain_core.tools import tool

from app.agent.catalog_domain import (
    compare,
    get_by_sku,
    recommendation_need,
    recommend_top3 as rank_top3,
    search,
)
from app.agent.tools.runtime import note_tool


@tool
async def search_products(
    query: str = "",
    budget_vnd: int = 0,
    household_size: int = 0,
    min_capacity_l: int = 0,
    max_width_cm: float = 0,
    max_height_cm: float = 0,
    max_depth_cm: float = 0,
    energy_saving_only: bool = False,
    brand: str = "",
    style: str = "",
    priced_only: bool = False,
    limit: int = 6,
) -> str:
    """Tìm tủ lạnh theo từ khóa, giá, số người, dung tích, kích thước, hãng và kiểu tủ."""
    note_tool("search_products")
    results = search(
        query,
        budget_vnd=budget_vnd or None,
        household_size=household_size or None,
        min_capacity_l=min_capacity_l or None,
        max_width_cm=max_width_cm or None,
        max_height_cm=max_height_cm or None,
        max_depth_cm=max_depth_cm or None,
        energy_saving=True if energy_saving_only else None,
        brand=brand,
        style=style,
        priced_only=priced_only,
        limit=limit,
    )
    return json.dumps(
        {"results": results, "source": "google_sheet:category_code=38"},
        ensure_ascii=False,
    )


@tool
async def get_product_detail(sku: str) -> str:
    """Chi tiết 1 SKU tủ lạnh từ Google Sheet: dung tích, kích thước, công nghệ, giá."""
    note_tool("get_product_detail")
    p = get_by_sku(sku)
    if not p:
        return json.dumps({"error": f"Không có SKU {sku}", "source": "catalog"}, ensure_ascii=False)
    return json.dumps(p, ensure_ascii=False)


@tool
async def compare_products(skus_csv: str) -> str:
    """So sánh 2–5 SKU tủ lạnh theo giá, dung tích, kích thước và mức giảm giá."""
    note_tool("compare_products")
    skus = [s.strip() for s in skus_csv.replace(";", ",").split(",") if s.strip()]
    return json.dumps(compare(skus), ensure_ascii=False)


@tool
async def recommend_top3(
    household_size: int = 0,
    capacity_l: int = 0,
    budget_vnd: int = 0,
    priorities: str = "",
    preferred_styles: str = "",
    max_width_cm: float = 0,
    max_height_cm: float = 0,
    max_depth_cm: float = 0,
    force: bool = False,
    free_text: str = "",
) -> str:
    """Đề xuất top 3 tủ lạnh. Thiếu số người/dung tích hoặc ngân sách thì hỏi lại.
    priorities: tiet_kiem_dien,gia_re,lay_nuoc_ngoai,tu_dong,dong_mem,bao_quan
    """
    note_tool("recommend_top3")
    need = recommendation_need(
        household_size=household_size or None,
        capacity_l=capacity_l or None,
        budget_vnd=budget_vnd or None,
        priorities=[p.strip() for p in priorities.split(",") if p.strip()],
        preferred_styles=[p.strip() for p in preferred_styles.split(",") if p.strip()],
        max_width_cm=max_width_cm or None,
        max_height_cm=max_height_cm or None,
        max_depth_cm=max_depth_cm or None,
        force=force,
        free_text=free_text,
    )
    return json.dumps(rank_top3(need), ensure_ascii=False)
