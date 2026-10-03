"""LLM "fast path" — deterministic recommend engine + one optional phrase call.

For a clear product-recommendation intent, skip the ReAct graph entirely: run the
deterministic recommend engine, then make at most ONE LLM call to phrase the
result. Anything ambiguous (policy/FAQ, escalation, leaving a phone, comparison,
no category) falls through to the full graph.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.constants import (
    LEAD_SCORE_BASE,
    LEAD_SCORE_QUALIFIED,
    LEAD_STATUS_QUALIFIED,
    RECOMMEND_PHRASE_FIELDS,
)
from app.agent.consultation import consult
from app.agent.intent import (
    COMPARE_KEYWORDS,
    ESCALATION_KEYWORDS,
    FAQ_KEYWORDS,
    fill_budget_from_profile,
    format_need_more,
    has_intent,
    merge_turn_need,
    phone_in_text,
)
from app.agent.llm import get_chat_model
from app.agent.memory.store import get_memory_summary, load_need, load_profile, save_need
from app.agent.responses import format_recommendation
from app.agent.tools.runtime import prepare_ctx
from app.agent.trajectory.export import save_trajectory
from app.config import get_settings
from app.services.leads import upsert_lead_record

logger = logging.getLogger(__name__)


def looks_like_recommend(user_text: str, need: dict[str, Any]) -> bool:
    if phone_in_text(user_text):
        return False
    if (
        has_intent(user_text, FAQ_KEYWORDS)
        or has_intent(user_text, ESCALATION_KEYWORDS)
        or has_intent(user_text, COMPARE_KEYWORDS)
    ):
        return False
    return bool(need.get("category"))


async def save_consultation_lead(
    *,
    customer_name: str,
    channel: str,
    external_id: str,
    conversation_id: int | None,
    need: dict[str, Any],
    rec: dict[str, Any],
) -> dict[str, Any]:
    """Upsert the finished consultation onto the owner dashboard.

    A CRM write must never break the customer reply: failures are logged
    and reported back as an empty result.
    """
    prof = await load_profile(channel, external_id)
    skus = ", ".join(need.get("last_skus", [])[:3])
    lead = await upsert_lead_record(
        name=customer_name,
        phone=str(prof.get("phone") or ""),
        channel=channel,
        external_id=external_id,
        interest=rec.get("category_display") or need.get("category") or "",
        budget_vnd=need.get("budget_vnd"),
        notes=f"Đã tư vấn {rec.get('category_display', '')}. Đề xuất: {skus}.".strip(),
        score=LEAD_SCORE_QUALIFIED if prof.get("phone") else LEAD_SCORE_BASE,
        status=LEAD_STATUS_QUALIFIED,
        conversation_id=conversation_id,
    )
    return {"lead_id": lead.id, "summary": f"lead#{lead.id}"}


async def phrase_recommendation(user_text: str, rec: dict[str, Any]) -> str:
    """One LLM call to turn the structured top-3 into a natural Vietnamese reply."""
    top = [
        {k: p.get(k) for k in RECOMMEND_PHRASE_FIELDS}
        for p in (rec.get("top3") or [])
    ]
    payload = {"top3": top, "tradeoffs": rec.get("tradeoffs"), "disclaimer": rec.get("disclaimer")}
    sys = (
        "Bạn là tư vấn viên điện máy thân thiện. Viết lại kết quả top-3 (JSON) thành lời tư vấn "
        "tiếng Việt tự nhiên, TỐI ĐA 120 từ: mỗi sản phẩm 1 dòng (tên — giá — 1 lý do), "
        "1 câu trade-off, 1 câu CTA. TUYỆT ĐỐI không thêm số/thông số ngoài JSON."
    )
    human = f"Khách hỏi: {user_text}\n\nKết quả (JSON):\n{json.dumps(payload, ensure_ascii=False)}"
    model = get_chat_model()
    ai = await model.ainvoke([SystemMessage(content=sys), HumanMessage(content=human)])
    return ai.content if isinstance(ai.content, str) else str(ai.content or "")


async def try_fast_path(
    user_text: str,
    *,
    channel: str,
    external_id: str,
    conversation_id: int | None,
    lead_id: int | None,
    customer_name: str,
    memory_summary: str,
    memory_before: dict[str, Any],
) -> dict[str, Any] | None:
    try:
        stored = await load_need(channel, external_id)
        need, _ = await merge_turn_need(user_text, stored)
        await fill_budget_from_profile(need, channel=channel, external_id=external_id)
        if not looks_like_recommend(user_text, need):
            return None

        prepare_ctx(
            channel=channel, external_id=external_id, conversation_id=conversation_id,
            lead_id=lead_id, customer_name=customer_name,
        )
        consultation_result = consult(need)
        rec = consultation_result.recommendation
        decision = consultation_result.decision
        if need.get("category"):
            await save_need(channel, external_id, need)

        tools_used: list[str] = []
        if rec.get("need_more"):
            reply = format_need_more(rec)
            agents = ["lead"]
            trace = [{"agent": "lead", "event": "fast_path", "detail": f"ask:{rec.get('category')}"}]
        elif rec.get("ok") and rec.get("top3"):
            # Optionally phrase nicely with ONE LLM call; never let a slow/failed
            # endpoint drag us down — on timeout/error/disabled, use the instant
            # deterministic formatter instead of the (much slower) full graph.
            reply = ""
            if get_settings().fast_path_phrasing:
                try:
                    reply = await asyncio.wait_for(
                        phrase_recommendation(user_text, rec),
                        timeout=get_settings().fast_path_phrasing_timeout_s,
                    )
                except Exception:
                    reply = ""
            if not reply.strip():
                reply = format_recommendation(rec)
            need["last_skus"] = [p["sku"] for p in rec["top3"] if p.get("sku")]
            await save_need(channel, external_id, need)
            agents = ["lead", "catalog"]
            tools_used = ["recommend_top3"]
            trace = [
                {"agent": "lead", "event": "fast_path", "detail": f"recommend:{rec.get('category')}"},
                {"agent": "catalog", "event": "recommend_top3", "detail": f"{len(rec['top3'])} SP"},
            ]
            # Consultation finished → record it on the owner dashboard as a lead
            # (upsert per customer so repeat turns update instead of duplicating).
            try:
                crm = await save_consultation_lead(
                    customer_name=customer_name,
                    channel=channel,
                    external_id=external_id,
                    conversation_id=conversation_id,
                    need=need,
                    rec=rec,
                )
                lead_id = crm["lead_id"]
                agents.append("crm")
                trace.append({"agent": "crm", "event": "save_lead", "detail": crm["summary"]})
            except Exception:
                # never let a dashboard write break the customer reply
                logger.warning(
                    "fast-path lead upsert failed (channel=%s external_id=%s)",
                    channel,
                    external_id,
                    exc_info=True,
                )
        else:
            return None  # no priced match — let the full graph offer to widen budget

        if not reply.strip():
            return None

        memory_after = await load_profile(channel, external_id)
        run_id = await save_trajectory(
            channel=channel, external_id=external_id, conversation_id=conversation_id,
            user_text=user_text, reply=reply, trace=trace, agents=agents,
            tools=tools_used, memory=memory_after, skills=[],
            decision=decision,
        )
        return {
            "reply": reply,
            "used_tools": tools_used,
            "used_agents": agents,
            "trace": trace,
            "subagent_results": [],
            "needs_human": False,
            "lead_id": lead_id,
            "conversation_id": conversation_id,
            "run_id": run_id,
            "memory": memory_after,
            "memory_summary": await get_memory_summary(channel, external_id),
            "active_skills": [],
            "memory_before": memory_before,
            "fast_path": True,
            "decision": decision,
        }
    except Exception:
        logger.warning(
            "fast-path failed, falling back to full graph (channel=%s external_id=%s)",
            channel,
            external_id,
            exc_info=True,
        )
        return None  # any hiccup → fall back to the full graph
