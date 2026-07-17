import json

from langchain_core.tools import tool

from app.agent.memory.store import load_profile, merge_profile
from app.agent.tools.runtime import get_ctx, note_tool


@tool
async def recall_customer() -> str:
    """Đọc hồ sơ memory của khách hiện tại (channel + external_id)."""
    note_tool("recall_customer")
    ctx = get_ctx()
    profile = await load_profile(ctx.channel, ctx.external_id)
    return json.dumps({"profile": profile}, ensure_ascii=False)


@tool
async def remember_customer(
    name: str = "",
    phone: str = "",
    budget_vnd: int = 0,
    interest: str = "",
    sku: str = "",
    note: str = "",
) -> str:
    """Lưu/cập nhật memory khách (tên, SĐT, budget, interest, SKU quan tâm, ghi chú)."""
    note_tool("remember_customer")
    ctx = get_ctx()
    profile = await merge_profile(
        ctx.channel,
        ctx.external_id,
        name=name or ctx.customer_name,
        phone=phone,
        budget_vnd=budget_vnd or None,
        interest=interest,
        sku=sku,
        note=note,
        last_intent=note or interest,
    )
    return json.dumps({"ok": True, "profile": profile}, ensure_ascii=False)
