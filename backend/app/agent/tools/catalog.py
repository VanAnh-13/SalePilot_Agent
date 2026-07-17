import json

from langchain_core.tools import tool

from app.agent.catalog_domain import compare, extract_need_from_text, get_by_sku, recommend_top3, search
from app.agent.tools.runtime import note_tool


@tool
async def search_products(
    query: str = "",
    budget_vnd: int = 0,
    room_m2: float = 0,
    inverter_only: bool = False,
    brand: str = "",
    limit: int = 6,
) -> str:
    """Tìm máy lạnh theo từ khóa, ngân sách (VND), diện tích phòng (m2), inverter, hãng."""
    note_tool("search_products")
    results = search(
        query,
        budget_vnd=budget_vnd or None,
        room_m2=room_m2 or None,
        inverter=True if inverter_only else None,
        brand=brand,
        limit=limit,
    )
    return json.dumps({"results": results, "source": "catalog:search"}, ensure_ascii=False)


@tool
async def get_product_detail(sku: str) -> str:
    """Chi tiết 1 SKU máy lạnh (giá, BTU, m2, ồn, KM). Không bịa — chỉ catalog."""
    note_tool("get_product_detail")
    p = get_by_sku(sku)
    if not p:
        return json.dumps({"error": f"Không có SKU {sku}", "source": "catalog"}, ensure_ascii=False)
    return json.dumps(p, ensure_ascii=False)


@tool
async def compare_products(skus_csv: str) -> str:
    """So sánh 2–5 SKU (csv: AC-001,AC-002). Trả trade-off dễ hiểu + nguồn catalog."""
    note_tool("compare_products")
    skus = [s.strip() for s in skus_csv.replace(";", ",").split(",") if s.strip()]
    return json.dumps(compare(skus), ensure_ascii=False)


@tool
async def recommend_top3(
    room_m2: float = 0,
    budget_vnd: int = 0,
    priorities: str = "",
    force: bool = False,
    free_text: str = "",
) -> str:
    """Đề xuất top 3 máy lạnh theo nhu cầu. Thiếu room_m2 hoặc budget → trả câu hỏi làm rõ (trừ force=true).
    priorities: csv vd tiet_kiem_dien,em,gia_re,cong_suat_lon
    """
    note_tool("recommend_top3")
    need: dict = {}
    if free_text:
        need = extract_need_from_text(free_text)
    if room_m2:
        need["room_m2"] = room_m2
    if budget_vnd:
        need["budget_vnd"] = budget_vnd
    if priorities:
        need["priority"] = [p.strip() for p in priorities.split(",") if p.strip()]
    if force:
        need["force"] = True
        need["budget_flexible"] = True
    return json.dumps(recommend_top3(need), ensure_ascii=False)
