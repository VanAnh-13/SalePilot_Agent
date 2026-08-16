"""Rule-based multi-agent path when no LLM API key — multi-category advisor."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from app.agent.consultation import ConsultationResult, consult
from app.agent.catalog_domain import compare, extract_need_from_text
from app.agent.intent import fill_budget_from_profile, format_need_more, merge_turn_need
from app.agent.offline_routing import read_turn_signals
from app.agent.memory.store import (
    get_memory_summary,
    load_need,
    maybe_extract_from_text,
    save_need,
)
from app.agent.run_bag import get_run_bag, reset_run_bag
from app.agent.tools.crm import create_lead, escalate_to_human
from app.agent.tools.knowledge import search_knowledge
from app.agent.tools.runtime import ToolContext, get_ctx, note_tool, set_ctx
from app.catalog.registry import (
    CATEGORIES,
    detect_category,
    detect_negated_categories,
)


def _trace(agent: str, event: str, detail: str = "") -> None:
    get_run_bag()["trace"].append({"agent": agent, "event": event, "detail": detail})


def _format_top3(rec: dict[str, Any]) -> str:
    display = rec.get("category_display") or "sản phẩm"
    if rec.get("need_more"):
        return format_need_more(rec)
    if not rec.get("ok"):
        return (
            str(rec.get("message") or "Không tìm thấy mẫu phù hợp với các giới hạn đã chọn.")
            + " Bạn có muốn tăng ngân sách hoặc nới điều kiện không ạ?"
        )

    lines = [f"Em gợi ý **top 3 {display.lower()}** phù hợp từ dữ liệu catalog:\n"]
    for i, p in enumerate(rec.get("top3") or [], 1):
        promo = f" · 🎁 {p['gift_promotion'][:70]}" if p.get("gift_promotion") else ""
        lines.append(
            f"{i}. **{p['name']}** (`{p['sku']}`) — {p['price_display']}"
            f" · {p.get('why', '')}"
            f"{promo}"
        )
    trade = rec.get("tradeoffs") or []
    if trade:
        lines.append("\n**Trade-off nhanh:**")
        for t in trade:
            lines.append(f"- {t}")
    lines.append("\n" + (rec.get("disclaimer") or ""))
    lines.append("Anh/chị muốn em so sánh kỹ 2 mẫu nào, hoặc để lại SĐT để tư vấn viên gọi lại ạ?")
    return "\n".join(lines)


def _format_compare(cmp: dict[str, Any]) -> str:
    if not cmp.get("ok"):
        return (
            str(cmp.get("error") or "Cần ít nhất 2 sản phẩm hợp lệ để so sánh.")
            + " Anh/chị cho em mã SKU, hoặc để em gợi ý top 3 rồi so sánh giúp mình nhé."
        )
    lines = ["Em so sánh nhanh các sản phẩm anh/chị chọn:\n"]
    for it in cmp.get("items", []):
        extra = []
        if it.get("rating"):
            extra.append(f"{it['rating']}★")
        if it.get("sold"):
            extra.append(f"đã bán {it.get('sold_display') or it['sold']}")
        tail = (" · " + " · ".join(extra)) if extra else ""
        lines.append(f"- **{it['name']}** (`{it['sku']}`) — {it['price_display']}{tail}")
    trade = cmp.get("tradeoffs") or []
    if trade:
        lines.append("\n**Khác biệt chính (trade-off):**")
        for t in trade:
            lines.append(f"- {t}")
    lines.append("\nAnh/chị nghiêng về tiêu chí nào (giá / pin / hiệu năng / thương hiệu) để em chốt giúp ạ?")
    return "\n".join(lines)


def _catalog_welcome() -> str:
    categories = ", ".join(category.display.lower() for category in CATEGORIES)
    return (
        "Xin chào! Em là SalePilot — trợ lý AI tư vấn **điện máy & công nghệ** "
        "theo nhu cầu thật, dựa trên dữ liệu catalog hiện có "
        "(giá, khuyến mãi, đánh giá, lượt bán):\n"
        f"{categories}.\n"
        "Anh/chị đang cần sản phẩm gì, **ngân sách khoảng bao nhiêu** ạ? "
        "Em sẽ hỏi thêm vài ý (dùng cho ai / diện tích phòng / ưu tiên gì...) "
        "để gợi ý top 3 phù hợp nhất."
    )


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
    parts: list[str] = []
    agents: list[str] = []

    await maybe_extract_from_text(channel, external_id, user_text)
    mem = await get_memory_summary(channel, external_id)
    if mem:
        _trace("lead", "memory", mem[:200])

    _trace("lead", "start", "offline multi-category advisor")

    # Multi-turn: load accumulated need first so a follow-up like "RAM 16 GB"
    # can extract category-specific slots without re-naming the product family.
    stored_need = await load_need(channel, external_id)
    # "ko phải tủ lạnh" — drop a stored category the user just rejected.
    negated = detect_negated_categories(user_text)
    if stored_need.get("category") in negated:
        stored_need = {
            k: v for k, v in stored_need.items() if k in {"budget_vnd", "brand"}
        }
        await save_need(channel, external_id, stored_need)
    category = detect_category(user_text)
    merged_need, _ = await merge_turn_need(
        user_text, stored_need, resolve_followup=False
    )
    await fill_budget_from_profile(merged_need, channel=channel, external_id=external_id)
    # The turn's fresh extraction feeds the routing policy below.
    extract_category = category.slug if category else stored_need.get("category")
    extracted_need = extract_need_from_text(user_text, category=extract_category)

    # Pure routing policy: intent flags, product/compare routing, guardrails.
    signals = read_turn_signals(
        user_text,
        stored_need=stored_need,
        extracted_need=extracted_need,
        merged_need=merged_need,
        detected=category,
    )

    if signals.need_product and merged_need.get("category"):
        await save_need(channel, external_id, merged_need)

    if signals.unsupported:
        term, suggestion = signals.unsupported
        supported_list = ", ".join(c.display for c in CATEGORIES)
        lines = [
            f"Em xin lỗi, hiện bảng dữ liệu của em **chưa có ngành hàng {term}** "
            "nên em không thể tư vấn chính xác (em không đoán bừa thông số/giá ạ).",
            f"Em đang có dữ liệu: {supported_list}.",
        ]
        if suggestion:
            lines.append(suggestion)
        lines.append("Anh/chị muốn xem nhóm hàng nào trong số đó không ạ?")
        parts.append("\n".join(lines))
        _trace("lead", "guardrail", f"unsupported:{term}")

    async def do_knowledge() -> str | None:
        if not signals.need_faq:
            return None
        _trace("lead", "delegate", "→ knowledge")
        if signals.stock_question:
            # Catalog has no realtime inventory column; answer honestly instead of
            # ranking an unrelated policy chunk that happened to match keywords.
            summary = (
                "Em chưa có dữ liệu tồn kho thời gian thực trong catalog hiện tại, "
                "nên không thể khẳng định còn hàng theo từng SKU. "
                "Anh/chị chọn mẫu ưng ý rồi em hỗ trợ kiểm tra khả năng giao hàng "
                "qua cửa hàng/tư vấn viên ạ."
            )
            bag["results"].append(
                {
                    "agent": "knowledge",
                    "summary": summary,
                    "tools_used": ["stock_guardrail"],
                    "ok": True,
                }
            )
            _trace("knowledge", "end", summary[:160])
            agents.append("knowledge")
            return summary
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

    async def do_compare() -> str | None:
        if not signals.do_compare_now:
            return None
        _trace("lead", "delegate", "→ catalog (compare)")
        note_tool("compare_products")
        cmp = compare(signals.compare_skus)
        bag["results"].append(
            {
                "agent": "catalog",
                "summary": json.dumps(cmp, ensure_ascii=False)[:800],
                "tools_used": ["compare_products"],
                "ok": bool(cmp.get("ok")),
            }
        )
        _trace("catalog", "end", "compare_products")
        agents.append("catalog")
        return _format_compare(cmp)

    consultation_result: ConsultationResult | None = None

    async def do_catalog() -> str | None:
        nonlocal consultation_result
        if not signals.need_product:
            return None
        _trace("lead", "delegate", f"→ catalog ({merged_need.get('category') or 'auto'})")
        note_tool("recommend_top3")
        consultation_result = consult(merged_need)
        rec = consultation_result.recommendation
        # Remember the recommended SKUs so a later "so sánh 2 mẫu đầu" works.
        top_skus = [p["sku"] for p in (rec.get("top3") or [])]
        if top_skus:
            merged_need["last_skus"] = top_skus
            if merged_need.get("category"):
                await save_need(channel, external_id, merged_need)
        bag["results"].append(
            {
                "agent": "catalog",
                "summary": json.dumps(rec, ensure_ascii=False)[:800],
                "tools_used": ["recommend_top3"],
                "ok": True,
            }
        )
        _trace("catalog", "end", f"recommend_top3:{rec.get('category')}")
        agents.append("catalog")
        return _format_top3(rec)

    cmp_s, cat_s, kn_s = await asyncio.gather(do_compare(), do_catalog(), do_knowledge())
    if cmp_s:
        parts.append(cmp_s)
    if cat_s:
        parts.append(cat_s)
    if kn_s:
        parts.append(kn_s)

    if signals.need_crm:
        phone = signals.phone or ""
        _trace("lead", "delegate", "→ crm")
        raw = await create_lead.ainvoke(
            {
                "name": customer_name,
                "phone": phone,
                "interest": user_text[:200],
                "budget_vnd": merged_need.get("budget_vnd") or 0,
                "notes": "offline multi-category advisor",
                "score": 0.7 if phone else 0.5,
            }
        )
        bag["results"].append(
            {"agent": "crm", "summary": raw, "tools_used": ["create_lead"], "ok": True}
        )
        agents.append("crm")
        parts.append("Em đã ghi nhận thông tin liên hệ. Tư vấn viên có thể gọi lại trong giờ hành chính ạ.")

    if signals.need_escalate:
        raw = await escalate_to_human.ainvoke(
            {"reason": "Khách yêu cầu gặp người", "summary": user_text[:300]}
        )
        bag["results"].append(
            {"agent": "escalation", "summary": raw, "tools_used": ["escalate_to_human"], "ok": True}
        )
        agents.append("escalation")
        parts.append("Em đã chuyển yêu cầu cho tư vấn viên người ạ.")

    if not parts:
        parts.append(_catalog_welcome())

    if mem and signals.need_product:
        parts.insert(0, f"(Em nhớ: {mem})")

    reply = "\n\n".join(parts)
    bag["final"] = reply
    _trace("lead", "finalize", reply[:200])
    ctx = get_ctx()
    decision = consultation_result.decision if consultation_result else None
    return {
        "reply": reply,
        "used_tools": list(ctx.used_tools),
        "used_agents": ["lead", *agents],
        "trace": list(bag["trace"]),
        "subagent_results": list(bag["results"]),
        "needs_human": ctx.needs_human,
        "lead_id": ctx.lead_id,
        "conversation_id": conversation_id,
        "decision": decision,
    }
