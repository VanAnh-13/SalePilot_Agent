import json

from langchain_core.tools import tool

from app.agent.catalog_domain import (
    compare,
    get_by_sku,
    recommendation_need,
    recommend_top3 as recommend_top3_engine,  # aliased: the @tool below owns the name
    search,
)
from app.agent.decision import build_decision
from app.agent.run_bag import get_run_bag
from app.agent.tools.runtime import note_tool
from app.catalog.registry import CATEGORIES
from app.catalog import repository

_CATEGORY_HELP = ", ".join(f"{c.slug} ({c.display})" for c in CATEGORIES)


@tool
async def list_categories() -> str:
    """Liệt kê các ngành hàng SalePilot tư vấn được (slug, tên, số sản phẩm có giá)."""
    note_tool("list_categories")
    counts = repository.category_counts()
    return json.dumps(
        {"categories": list(counts.values()), "source": f"{repository.source()}:catalog"},
        ensure_ascii=False,
    )


@tool
async def search_products(
    query: str = "",
    category: str = "",
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
    """Tìm sản phẩm theo từ khóa + bộ lọc (giá, hãng, kích thước...).

    category: slug ngành hàng (vd: tu_lanh, may_lanh, may_giat, may_tinh_bang,
    dong_ho, man_hinh, may_in...) — nên truyền để kết quả đúng ngành.
    """
    note_tool("search_products")
    results = search(
        query,
        category=category or None,
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
        {"results": results, "source": f"{repository.source()}:catalog"},
        ensure_ascii=False,
    )


@tool
async def get_product_detail(sku: str) -> str:
    """Chi tiết 1 SKU: thông số chuẩn hóa + spec gốc tiếng Việt + giá."""
    note_tool("get_product_detail")
    p = get_by_sku(sku)
    if not p:
        return json.dumps({"error": f"Không có SKU {sku}", "source": "catalog"}, ensure_ascii=False)
    return json.dumps(p, ensure_ascii=False)


@tool
async def compare_products(skus_csv: str) -> str:
    """So sánh 2–5 SKU cùng ngành: giá, thông số chính và trade-off dễ hiểu."""
    note_tool("compare_products")
    skus = [s.strip() for s in skus_csv.replace(";", ",").split(",") if s.strip()]
    return json.dumps(compare(skus), ensure_ascii=False)


@tool
async def recommend_top3(
    category: str = "",
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
    """Đề xuất top 3 sản phẩm theo nhu cầu. Thiếu slot quan trọng thì trả câu hỏi ngược.

    category: slug ngành (tu_lanh, may_lanh, may_giat, may_say, may_rua_chen, tu_dong,
    may_nuoc_nong, dong_ho, may_tinh_de_ban, man_hinh, may_in, may_tinh_bang,
    micro_karaoke, micro_thu_am). Bỏ trống sẽ tự nhận diện từ free_text.
    free_text: mô tả nhu cầu gốc của khách (nên truyền nguyên văn) — engine tự
    bóc slot đặc thù ngành: diện tích phòng (m²) máy lạnh, kg máy giặt/sấy,
    inch màn hình, GB tablet/PC, lít tủ...
    priorities: keyword ưu tiên (tiet_kiem_dien, gia_re, chay_em, co_say, sim,
    pin_trau, nghe_goi, suc_khoe, do_hoa_game, gaming, laser, in_mau...).
    """
    note_tool("recommend_top3")
    need = recommendation_need(
        category=category or None,
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
    recommendation = recommend_top3_engine(need)
    try:
        decision = build_decision(need, recommendation)
        get_run_bag()["decision"] = decision
    except Exception:
        # The recommendation itself remains usable if provenance enrichment
        # encounters malformed third-party/catalog data.
        decision = None
    payload = dict(recommendation)
    if decision is not None:
        payload["decision"] = decision
    return json.dumps(payload, ensure_ascii=False)
