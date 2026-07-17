"""Rule-based multi-agent path when no LLM API key — refrigerator advisor."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from app.agent.catalog_domain import extract_need_from_text, recommend_top3
from app.agent.memory.store import get_memory_summary, maybe_extract_from_text
from app.agent.run_bag import get_run_bag, reset_run_bag
from app.agent.tools.crm import create_lead, escalate_to_human
from app.agent.tools.knowledge import search_knowledge
from app.agent.tools.runtime import ToolContext, get_ctx, set_ctx


def _trace(agent: str, event: str, detail: str = "") -> None:
    get_run_bag()["trace"].append({"agent": agent, "event": event, "detail": detail})


def _format_top3(rec: dict[str, Any]) -> str:
    if rec.get("need_more"):
        asks = rec.get("ask") or []
        return "Để gợi ý tủ lạnh sát nhu cầu, em cần thêm:\n" + "\n".join(f"- {a}" for a in asks)
    if not rec.get("ok"):
        return (
            str(rec.get("message") or "Không tìm thấy mẫu phù hợp với các giới hạn đã chọn.")
            + " Bạn có muốn tăng ngân sách hoặc nới kích thước không ạ?"
        )

    lines = ["Em gợi ý **top 3 tủ lạnh** phù hợp từ bảng sản phẩm:\n"]
    for i, p in enumerate(rec.get("top3") or [], 1):
        lines.append(
            f"{i}. **{p['name']}** (`{p['sku']}`) — {p['price_display']}"
            f" · {p.get('usable_capacity_l')} lít"
            f" · {p.get('household_size_label') or 'chưa có nhãn số người'}"
            f" · {p.get('why', '')}"
            f" · nguồn: {p.get('source')}"
        )
    trade = rec.get("tradeoffs") or []
    if trade:
        lines.append("\n**Trade-off nhanh:**")
        for t in trade:
            lines.append(f"- {t}")
    lines.append("\n" + (rec.get("disclaimer") or ""))
    lines.append("Anh/chị muốn em so sánh kỹ 2 mẫu nào, hoặc để lại SĐT để tư vấn viên gọi lại ạ?")
    return "\n".join(lines)


async def run_offline_multi_agent(
    user_text: str,
    *,
    channel: str = "web",
    external_id: str = "",
    conversation_id: int | None = None,
    lead_id: int | None = None,
    customer_name: str = "Khách",
) -> dict[str, Any]:
    reset_run_bag()
    set_ctx(
        ToolContext(
            channel=channel,
            external_id=external_id,
            conversation_id=conversation_id,
            lead_id=lead_id,
            customer_name=customer_name,
        )
    )
    bag = get_run_bag()
    t = user_text.lower()
    parts: list[str] = []
    agents: list[str] = []

    await maybe_extract_from_text(channel, external_id, user_text)
    mem = await get_memory_summary(channel, external_id)
    if mem:
        _trace("lead", "memory", mem[:200])

    _trace("lead", "start", "offline refrigerator advisor")

    stock_question = any(
        k in t for k in ("còn hàng", "con hang", "tồn kho", "ton kho", "khả năng giao hàng")
    )
    need_faq = stock_question or any(
        k in t
        for k in (
            "bảo hành",
            "bao hanh",
            "lắp",
            "giao",
            "ship",
            "trả góp",
            "đổi",
            "trả",
            "vệ sinh",
            "đổi cũ",
        )
    )
    need_escalate = any(k in t for k in ("gặp người", "tư vấn viên", "nhân viên", "khiếu nại"))
    phone_m = re.search(r"0\d{8,10}", user_text.replace(" ", "").replace(".", ""))
    need_crm = bool(phone_m) or any(k in t for k in ("gọi lại", "để lại sđt", "liên hệ em"))

    extracted_need = extract_need_from_text(user_text)
    need_product = any(
        k in t
        for k in (
            "tủ lạnh",
            "tu lanh",
            "side by side",
            "multi door",
            "ngăn đá",
            "ngan da",
            "dung tích",
            "dung tich",
            "lít",
            "lit",
            "người",
            "nguoi",
            "triệu",
            "inverter",
            "lấy nước",
            "làm đá",
            "đông mềm",
            "gợi ý",
            "so sánh",
            "nên mua",
            "top",
            "rẻ",
            "tiết kiệm",
        )
    ) or bool(extracted_need.get("household_size")) or bool(extracted_need.get("capacity_l"))
    if stock_question and not any(
        extracted_need.get(key)
        for key in ("household_size", "capacity_l", "budget_vnd", "max_width_cm")
    ):
        need_product = False

    async def do_knowledge() -> str | None:
        if not need_faq:
            return None
        _trace("lead", "delegate", "→ knowledge")
        raw = await search_knowledge.ainvoke({"query": user_text})
        data = json.loads(raw)
        hits = data.get("results") or []
        if hits:
            summary = "Theo chính sách/FAQ:\n" + "\n".join(
                f"- {h.get('question')}: {h.get('answer')}" for h in hits[:2]
            )
        else:
            summary = data.get("fallback") or "Em sẽ kiểm tra chính sách chi tiết ạ."
        bag["results"].append(
            {"agent": "knowledge", "summary": summary, "tools_used": ["search_knowledge"], "ok": True}
        )
        _trace("knowledge", "end", summary[:160])
        agents.append("knowledge")
        return summary

    async def do_catalog() -> str | None:
        if not need_product and not need_faq:
            # still try if greeting with product intent later
            pass
        if not need_product:
            return None
        _trace("lead", "delegate", "→ catalog")
        need = extracted_need
        from app.agent.tools.runtime import note_tool

        note_tool("recommend_top3")
        rec = recommend_top3(need)
        bag["results"].append(
            {
                "agent": "catalog",
                "summary": json.dumps(rec, ensure_ascii=False)[:800],
                "tools_used": ["recommend_top3"],
                "ok": True,
            }
        )
        _trace("catalog", "end", "recommend_top3")
        agents.append("catalog")
        return _format_top3(rec)

    cat_s, kn_s = await asyncio.gather(do_catalog(), do_knowledge())
    if cat_s:
        parts.append(cat_s)
    if kn_s:
        parts.append(kn_s)

    if need_crm:
        phone = phone_m.group(0) if phone_m else ""
        _trace("lead", "delegate", "→ crm")
        raw = await create_lead.ainvoke(
            {
                "name": customer_name,
                "phone": phone,
                "interest": user_text[:200],
                "budget_vnd": extracted_need.get("budget_vnd") or 0,
                "notes": "offline refrigerator advisor",
                "score": 0.7 if phone else 0.5,
            }
        )
        bag["results"].append(
            {"agent": "crm", "summary": raw, "tools_used": ["create_lead"], "ok": True}
        )
        agents.append("crm")
        parts.append("Em đã ghi nhận thông tin liên hệ. Tư vấn viên có thể gọi lại trong giờ hành chính ạ.")

    if need_escalate:
        raw = await escalate_to_human.ainvoke(
            {"reason": "Khách yêu cầu gặp người", "summary": user_text[:300]}
        )
        bag["results"].append(
            {"agent": "escalation", "summary": raw, "tools_used": ["escalate_to_human"], "ok": True}
        )
        agents.append("escalation")
        parts.append("Em đã chuyển yêu cầu cho tư vấn viên người ạ.")

    if not parts:
        parts.append(
            "Xin chào! Em là SalePilot — trợ lý AI tư vấn **tủ lạnh** theo nhu cầu thật "
            "(không chỉ liệt kê thông số).\n"
            "Anh/chị cho em biết: **nhà có bao nhiêu người** và **ngân sách khoảng bao nhiêu**, "
            "mình ưu tiên **tiết kiệm điện / kiểu tủ / kích thước / bảo quản thực phẩm** ạ?"
        )

    if mem and need_product:
        parts.insert(0, f"(Em nhớ: {mem})")

    reply = "\n\n".join(parts)
    bag["final"] = reply
    _trace("lead", "finalize", reply[:200])
    ctx = get_ctx()
    return {
        "reply": reply,
        "used_tools": list(ctx.used_tools),
        "used_agents": ["lead", *agents],
        "trace": list(bag["trace"]),
        "subagent_results": list(bag["results"]),
        "needs_human": ctx.needs_human,
        "lead_id": ctx.lead_id,
        "conversation_id": conversation_id,
    }
