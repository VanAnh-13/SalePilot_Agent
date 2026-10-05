import json
from typing import Any

from langchain_core.tools import tool
from sqlalchemy import select
from app.agent.catalog_domain import get_by_sku
from app.agent.catalog_queries import fmt_price
from app.agent.tools.runtime import get_ctx, note_tool
from app.db.session import async_session
from app.models.entities import OrderDraft

MIN_QUANTITY = 1
MAX_QUANTITY = 10
ORDER_STATUS_DRAFT = "draft"
RECENT_DRAFTS_LIMIT = 5


def _parse_items(items_json: str) -> tuple[list | None, str | None]:
    """Decode the items_json argument into a non-empty list, or an error string."""
    try:
        items = json.loads(items_json) if isinstance(items_json, str) else items_json
    except json.JSONDecodeError:
        return None, "items_json không hợp lệ"
    if not isinstance(items, list) or not items:
        return None, "Cần ít nhất 1 item"
    return items, None


def _parse_qty(sku: str, qty_raw: Any) -> tuple[int | None, str | None]:
    """Validate one line's quantity as an integer in [MIN_QUANTITY, MAX_QUANTITY]."""
    try:
        qty = int(qty_raw)
    except (TypeError, ValueError):
        return None, f"Số lượng không hợp lệ cho SKU {sku}"
    if (
        isinstance(qty_raw, bool)
        or str(qty) != str(qty_raw).strip()
        or not MIN_QUANTITY <= qty <= MAX_QUANTITY
    ):
        return None, f"Số lượng cho SKU {sku} phải là số nguyên từ {MIN_QUANTITY} đến {MAX_QUANTITY}"
    return qty, None


async def _build_lines(
    items: list,
) -> tuple[list, list, int, str | None]:
    """Resolve each item to a draft line; return (lines, warnings, total, error)."""
    lines = []
    warnings = []
    total = 0
    for item in items:
        if not isinstance(item, dict):
            return lines, warnings, total, "Mỗi item phải có sku và qty"
        sku = str(item.get("sku", "")).strip()
        qty, qty_err = _parse_qty(sku, item.get("qty", 1))
        if qty_err:
            return lines, warnings, total, qty_err
        product = get_by_sku(sku)
        if not product:
            return lines, warnings, total, f"SKU không tồn tại: {sku}"
        if product.get("price_vnd") is None:
            # Honest recovery: keep the line, flag it, never invent a price.
            warnings.append(
                f"SKU {sku} chưa có giá hiện hành trong bảng nguồn — cần báo giá từ cửa hàng."
            )
            lines.append(
                {
                    "sku": product["sku"],
                    "name": product["name"],
                    "qty": qty,
                    "unit_price": None,
                    "line_total": None,
                    "needs_price": True,
                    "stock": None,
                    "source": product.get("source"),
                }
            )
            continue
        line_total = int(product["price_vnd"]) * qty
        total += line_total
        lines.append(
            {
                "sku": product["sku"],
                "name": product["name"],
                "qty": qty,
                "unit_price": product["price_vnd"],
                "line_total": line_total,
                "needs_price": False,
                "stock": None,
                "source": product.get("source"),
            }
        )
    return lines, warnings, total, None


async def _persist_draft(ctx, lines: list, total: int, notes: str) -> OrderDraft:
    async with async_session() as session:
        draft = OrderDraft(
            lead_id=ctx.lead_id,
            conversation_id=ctx.conversation_id,
            items_json=json.dumps(lines, ensure_ascii=False),
            total_vnd=total,
            status=ORDER_STATUS_DRAFT,
            notes=notes,
        )
        session.add(draft)
        await session.commit()
        await session.refresh(draft)
        return draft


@tool
async def create_order_draft(items_json: str, notes: str = "") -> str:
    """Tạo đơn nháp sản phẩm. items_json: JSON list [{sku, qty}]. SKU chưa có giá vẫn vào đơn với cờ needs_price (không bịa giá)."""
    note_tool("create_order_draft")
    items, err = _parse_items(items_json)
    if err:
        return json.dumps({"error": err}, ensure_ascii=False)
    lines, warnings, total, err = await _build_lines(items)
    if err:
        return json.dumps({"error": err}, ensure_ascii=False)

    draft = await _persist_draft(get_ctx(), lines, total, notes)
    return json.dumps(
        {
            "order_draft_id": draft.id,
            "items": lines,
            "total_vnd": total,
            "total_display": fmt_price(total),
            "status": ORDER_STATUS_DRAFT,
            "warnings": warnings,
        },
        ensure_ascii=False,
    )


@tool
async def check_order_status(order_draft_id: int = 0) -> str:
    """Tra cứu đơn nháp đã tạo: theo order_draft_id, hoặc đơn mới nhất của hội thoại hiện tại khi bỏ trống."""
    note_tool("check_order_status")
    ctx = get_ctx()
    async with async_session() as session:
        stmt = select(OrderDraft).order_by(OrderDraft.id.desc()).limit(RECENT_DRAFTS_LIMIT)
        if order_draft_id:
            stmt = stmt.where(OrderDraft.id == order_draft_id)
        elif ctx.conversation_id:
            stmt = stmt.where(OrderDraft.conversation_id == ctx.conversation_id)
        else:
            return json.dumps(
                {
                    "found": False,
                    "message": (
                        "Chưa có đơn nháp nào cho hội thoại này. "
                        "Dùng create_order_draft để tạo mới ạ."
                    ),
                },
                ensure_ascii=False,
            )
        drafts = (await session.execute(stmt)).scalars().all()
    if not drafts:
        return json.dumps(
            {
                "found": False,
                "message": (
                    "Chưa có đơn nháp nào cho hội thoại này. "
                    "Dùng create_order_draft để tạo mới ạ."
                ),
            },
            ensure_ascii=False,
        )
    return json.dumps(
        {
            "found": True,
            "orders": [
                {
                    "order_draft_id": d.id,
                    "items": json.loads(d.items_json or "[]"),
                    "total_vnd": d.total_vnd,
                    "status": d.status,
                    "notes": d.notes,
                    "created": d.created_at.isoformat() if d.created_at else None,
                }
                for d in drafts
            ],
        },
        ensure_ascii=False,
    )
