import json

from langchain_core.tools import tool
from app.agent.catalog_domain import get_by_sku
from app.agent.tools.runtime import get_ctx, note_tool
from app.db.session import async_session
from app.models.entities import OrderDraft


@tool
async def create_order_draft(items_json: str, notes: str = "") -> str:
    """Tạo đơn nháp tủ lạnh. items_json: JSON list [{sku, qty}]."""
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
    for item in items:
        if not isinstance(item, dict):
            return json.dumps({"error": "Mỗi item phải có sku và qty"}, ensure_ascii=False)
        sku = str(item.get("sku", "")).strip()
        qty_raw = item.get("qty", 1)
        try:
            qty = int(qty_raw)
        except (TypeError, ValueError):
            return json.dumps({"error": f"Số lượng không hợp lệ cho SKU {sku}"}, ensure_ascii=False)
        if isinstance(qty_raw, bool) or str(qty) != str(qty_raw).strip() or not 1 <= qty <= 10:
            return json.dumps(
                {"error": f"Số lượng cho SKU {sku} phải là số nguyên từ 1 đến 10"},
                ensure_ascii=False,
            )
        product = get_by_sku(sku)
        if not product:
            return json.dumps({"error": f"SKU không tồn tại: {sku}"}, ensure_ascii=False)
        if product.get("price_vnd") is None:
            return json.dumps(
                {"error": f"SKU {sku} chưa có giá hiện hành trong bảng nguồn"},
                ensure_ascii=False,
            )
        line_total = int(product["price_vnd"]) * qty
        total += line_total
        lines.append(
            {
                "sku": product["sku"],
                "name": product["name"],
                "qty": qty,
                "unit_price": product["price_vnd"],
                "line_total": line_total,
                "stock": None,
                "source": product.get("source"),
            }
        )
    async with async_session() as session:
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
