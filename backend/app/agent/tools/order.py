import json

from langchain_core.tools import tool
from sqlalchemy import select

from app.agent.tools.runtime import get_ctx, note_tool
from app.db.session import async_session
from app.models.entities import OrderDraft, Product


@tool
async def create_order_draft(items_json: str, notes: str = "") -> str:
    """Tạo đơn nháp. items_json: JSON list [{sku, qty}] ví dụ [{"sku":"SF-001","qty":1}]."""
    note_tool("create_order_draft")
    ctx = get_ctx()
    try:
        items = json.loads(items_json) if isinstance(items_json, str) else items_json
    except json.JSONDecodeError:
        return json.dumps({"error": "items_json không hợp lệ"}, ensure_ascii=False)
    if not isinstance(items, list) or not items:
        return json.dumps({"error": "Cần ít nhất 1 item"}, ensure_ascii=False)

    lines = []
    total = 0
    async with async_session() as session:
        for it in items:
            sku = str(it.get("sku", "")).upper()
            qty = int(it.get("qty", 1))
            p = (await session.execute(select(Product).where(Product.sku == sku))).scalar_one_or_none()
            if not p:
                return json.dumps({"error": f"SKU không tồn tại: {sku}"}, ensure_ascii=False)
            if p.stock < qty:
                return json.dumps(
                    {"error": f"{p.name} chỉ còn {p.stock} sp, yêu cầu {qty}"},
                    ensure_ascii=False,
                )
            line_total = p.price_vnd * qty
            total += line_total
            lines.append(
                {
                    "sku": p.sku,
                    "name": p.name,
                    "qty": qty,
                    "unit_price": p.price_vnd,
                    "line_total": line_total,
                }
            )
        draft = OrderDraft(
            lead_id=ctx.lead_id,
            conversation_id=ctx.conversation_id,
            items_json=json.dumps(lines, ensure_ascii=False),
            total_vnd=total,
            status="draft",
            notes=notes,
        )
        session.add(draft)
        await session.commit()
        await session.refresh(draft)
        return json.dumps(
            {
                "order_draft_id": draft.id,
                "items": lines,
                "total_vnd": total,
                "total_display": f"{total:,}".replace(",", ".") + "đ",
                "status": "draft",
            },
            ensure_ascii=False,
        )
