import asyncio
import json
import re
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent.catalog_domain import (
    detect_category,
    extract_need_from_text,
    merge_needs,
    recommend_top3,
    resolve_followup_answer,
)
from app.agent.lead_tools import LEAD_TOOLS
from app.agent.run_bag import get_run_bag, reset_run_bag
from app.agent.llm import get_chat_model, has_llm_key
from app.agent.memory.store import (
    get_memory_summary,
    load_need,
    load_profile,
    maybe_extract_from_text,
    save_need,
)
from app.agent.offline import _format_top3, run_offline_multi_agent
from app.agent.prompts import lead_system_prompt
from app.agent.skills.writer import maybe_write_skill_from_run
from app.agent.state import AgentState
from app.agent.tools.runtime import ToolContext, get_ctx, set_ctx
from app.agent.trajectory.export import save_trajectory
from app.config import get_settings


def _build_graph():
    model = get_chat_model().bind_tools(LEAD_TOOLS)
    tool_node = ToolNode(LEAD_TOOLS)

    async def lead_node(state: AgentState) -> dict[str, Any]:
        messages = list(state.get("messages") or [])
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=lead_system_prompt()), *messages]
        bag = get_run_bag()
        # inject activated skill bodies
        if bag.get("skill_bodies"):
            skill_blob = "\n\n".join(
                f"[Skill:{n}]\n{body[:6000]}" for n, body in bag["skill_bodies"].items()
            )
            if not any(
                isinstance(m, HumanMessage) and str(m.content).startswith("[Active skills]")
                for m in messages[-4:]
            ):
                messages = [
                    *messages,
                    HumanMessage(content=f"[Active skills]\n{skill_blob}"),
                ]
        if bag["results"] and not any(
            isinstance(m, HumanMessage) and str(m.content).startswith("[Sub-agent results]")
            for m in messages[-3:]
        ):
            brief = "\n".join(
                f"- {r['agent']}: {r['summary'][:400]}" for r in bag["results"][-5:]
            )
            messages = [
                *messages,
                HumanMessage(
                    content=f"[Sub-agent results]\n{brief}\n\nHãy tiếp tục delegate/delegate_many hoặc finalize."
                ),
            ]
        response = await model.ainvoke(messages)
        return {"messages": [response], "trace": list(bag["trace"])}

    def should_continue(state: AgentState) -> str:
        bag = get_run_bag()
        if bag.get("final"):
            return END
        messages = state.get("messages") or []
        if not messages:
            return END
        last = messages[-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        if isinstance(last, AIMessage) and last.content:
            content = last.content if isinstance(last.content, str) else str(last.content)
            if content.strip() and not bag.get("final"):
                bag["final"] = content.strip()
                bag["trace"].append(
                    {"agent": "lead", "event": "finalize", "detail": content[:200]}
                )
        return END

    graph = StateGraph(AgentState)
    graph.add_node("lead", lead_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("lead")
    graph.add_conditional_edges("lead", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "lead")
    return graph.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


def _prepare_ctx(
    *,
    channel: str,
    external_id: str,
    conversation_id: int | None,
    lead_id: int | None,
    customer_name: str,
) -> ToolContext:
    ctx = ToolContext(
        channel=channel,
        external_id=external_id,
        conversation_id=conversation_id,
        lead_id=lead_id,
        customer_name=customer_name,
    )
    set_ctx(ctx)
    return ctx


def _system_with_memory(base: str, memory_summary: str) -> str:
    if not memory_summary:
        return base
    return base + f"\n\n[Customer memory]\n{memory_summary}\nDùng remember_customer để cập nhật khi có fact mới."


# --------------------------------------------------------------------------- #
# Fast-path (B): for a clear product-recommendation intent, skip the ReAct
# graph entirely — run the deterministic recommend engine, then make at most ONE
# LLM call to phrase the result. Anything ambiguous (policy/FAQ, escalation,
# leaving a phone, comparison, no category) falls through to the full graph.
# --------------------------------------------------------------------------- #

_FAQ_KW = (
    "bảo hành", "bao hanh", "giao hàng", "giao hang", "lắp đặt", "lap dat",
    "trả góp", "tra gop", "đổi trả", "doi tra", "chính sách", "chinh sach",
    "vệ sinh", "khui hộp", "khui hop", "hoá đơn", "hóa đơn",
)
_ESC_KW = ("gặp người", "gap nguoi", "tư vấn viên", "tu van vien", "nhân viên", "nhan vien", "khiếu nại", "khieu nai")
_CMP_KW = ("so sánh", "so sanh", "compare", "đối chiếu", "doi chieu")
_PHONE_RE = re.compile(r"0\d{8,10}")


def _looks_like_recommend(user_text: str, need: dict) -> bool:
    t = (user_text or "").lower()
    if _PHONE_RE.search(t.replace(" ", "").replace(".", "")):
        return False
    if any(k in t for k in _FAQ_KW) or any(k in t for k in _ESC_KW) or any(k in t for k in _CMP_KW):
        return False
    return bool(need.get("category"))


def _format_need_more(rec: dict[str, Any]) -> str:
    display = (rec.get("category_display") or "sản phẩm").lower()
    asks = rec.get("ask") or []
    return f"Để gợi ý {display} sát nhu cầu, em cần thêm:\n" + "\n".join(f"- {a}" for a in asks)


async def _phrase_recommendation(user_text: str, rec: dict[str, Any]) -> str:
    """One LLM call to turn the structured top-3 into a natural Vietnamese reply."""
    top = [
        {k: p.get(k) for k in ("name", "sku", "price_display", "why", "gift_promotion")}
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


async def _try_fast_path(
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
        # Interpret this turn under the category already in play, so a short slot
        # answer on a follow-up turn ("9kg", "5 người") is captured even when the
        # user doesn't repeat the product name. A freshly named category wins.
        detected = detect_category(user_text)
        ctx_category = (detected.slug if detected else None) or stored.get("category")
        fresh = extract_need_from_text(user_text, ctx_category)
        need = merge_needs(stored, fresh)
        # A short follow-up ("50", "phòng ngủ", "9") answers the slot we just
        # asked about — unless the user switched category this turn.
        switching = bool(
            detected and stored.get("category") and detected.slug != stored.get("category")
        )
        if not switching:
            need = resolve_followup_answer(need, stored, user_text)
        if need.get("budget_vnd") is None:
            prof = await load_profile(channel, external_id)
            if prof.get("budget_vnd"):
                need["budget_vnd"] = int(prof["budget_vnd"])
        if not _looks_like_recommend(user_text, need):
            return None

        _prepare_ctx(
            channel=channel, external_id=external_id, conversation_id=conversation_id,
            lead_id=lead_id, customer_name=customer_name,
        )
        rec = recommend_top3(need)
        if need.get("category"):
            await save_need(channel, external_id, need)

        tools_used: list[str] = []
        if rec.get("need_more"):
            reply = _format_need_more(rec)
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
                        _phrase_recommendation(user_text, rec), timeout=25
                    )
                except Exception:
                    reply = ""
            if not reply.strip():
                reply = _format_top3(rec)
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
                from app.services.leads import upsert_lead_record

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
                    score=0.6 if prof.get("phone") else 0.5,
                    status="qualified",
                    conversation_id=conversation_id,
                )
                lead_id = lead.id
                agents.append("crm")
                trace.append({"agent": "crm", "event": "save_lead", "detail": f"lead#{lead.id}"})
            except Exception:
                pass  # never let a dashboard write break the customer reply
        else:
            return None  # no priced match — let the full graph offer to widen budget

        if not reply.strip():
            return None

        memory_after = await load_profile(channel, external_id)
        run_id = await save_trajectory(
            channel=channel, external_id=external_id, conversation_id=conversation_id,
            user_text=user_text, reply=reply, trace=trace, agents=agents,
            tools=tools_used, memory=memory_after, skills=[],
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
        }
    except Exception:
        return None  # any hiccup → fall back to the full graph


async def run_agent(
    user_text: str,
    *,
    history: list[dict[str, str]] | None = None,
    channel: str = "web",
    external_id: str = "",
    conversation_id: int | None = None,
    lead_id: int | None = None,
    customer_name: str = "Khách",
) -> dict[str, Any]:
    memory_before = await load_profile(channel, external_id)
    memory_summary = await get_memory_summary(channel, external_id)
    await maybe_extract_from_text(channel, external_id, user_text)

    if not has_llm_key():
        result = await run_offline_multi_agent(
            user_text,
            channel=channel,
            external_id=external_id,
            conversation_id=conversation_id,
            lead_id=lead_id,
            customer_name=customer_name,
        )
        memory_after = await load_profile(channel, external_id)
        run_id = await save_trajectory(
            channel=channel,
            external_id=external_id,
            conversation_id=conversation_id,
            user_text=user_text,
            reply=result["reply"],
            trace=result.get("trace") or [],
            agents=result.get("used_agents") or [],
            tools=result.get("used_tools") or [],
            memory=memory_after,
            skills=[],
        )
        result["run_id"] = run_id
        result["memory"] = memory_after
        result["memory_summary"] = await get_memory_summary(channel, external_id)
        return result

    # Fast-path (B): clear recommend intent → deterministic engine + 1 LLM call.
    fast = await _try_fast_path(
        user_text,
        channel=channel,
        external_id=external_id,
        conversation_id=conversation_id,
        lead_id=lead_id,
        customer_name=customer_name,
        memory_summary=memory_summary,
        memory_before=memory_before,
    )
    if fast is not None:
        return fast

    reset_run_bag()
    _prepare_ctx(
        channel=channel,
        external_id=external_id,
        conversation_id=conversation_id,
        lead_id=lead_id,
        customer_name=customer_name,
    )

    sys = _system_with_memory(lead_system_prompt(), memory_summary)
    messages: list = [SystemMessage(content=sys)]
    for h in history or []:
        role = h.get("role", "user")
        content = h.get("content", "")
        if role == "assistant":
            messages.append(AIMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))
    messages.append(HumanMessage(content=user_text))

    graph = get_graph()
    llm_error: Exception | None = None
    try:
        await graph.ainvoke(
            {
                "messages": messages,
                "channel": channel,
                "external_id": external_id,
                "conversation_id": conversation_id,
                "lead_id": lead_id,
                "customer_name": customer_name,
                "needs_human": False,
                "plan": "",
                "active_agents": [],
                "subagent_results": [],
                "trace": [],
                "final_reply": "",
            },
            config={"recursion_limit": 24},
        )
    except Exception as exc:  # LLM timeout / rate-limit / endpoint down
        # Never surface a raw 500 to the customer: degrade to a friendly message
        # and keep serving. The deterministic recommend fast-path already handles
        # clear product intents without the LLM, so this only affects the
        # ambiguous / FAQ / compare queries that need reasoning.
        llm_error = exc

    bag = get_run_bag()
    ctx = get_ctx()
    reply = bag.get("final") or ""
    if not reply:
        if llm_error is not None:
            bag["trace"].append(
                {"agent": "lead", "event": "llm_error", "detail": type(llm_error).__name__}
            )
            reply = (
                "Xin lỗi, hiện em chưa kết nối được trợ lý AI (mạng/LLM đang bận). "
                "Anh/chị mô tả nhu cầu kèm ngân sách giúp em nhé "
                "(vd: “tủ lạnh cho 4 người dưới 15 triệu”, “máy lạnh phòng 20m² tầm 12 triệu”) "
                "— em sẽ gợi ý sản phẩm ngay, hoặc để lại SĐT để tư vấn viên gọi lại ạ."
            )
        else:
            reply = (
                "Em xin lỗi, hệ thống multi-agent chưa chốt được câu trả lời. "
                "Bạn thử hỏi lại giúp em nhé."
            )

    agents_used = sorted({r["agent"] for r in bag["results"] if r.get("agent")})
    used_agents = ["lead", *agents_used]
    skill_name = maybe_write_skill_from_run(
        user_text=user_text, agents=used_agents, reply=reply
    )
    if skill_name:
        bag["trace"].append(
            {"agent": "lead", "event": "auto_skill", "detail": skill_name}
        )

    memory_after = await load_profile(channel, external_id)
    run_id = await save_trajectory(
        channel=channel,
        external_id=external_id,
        conversation_id=conversation_id,
        user_text=user_text,
        reply=reply,
        trace=list(bag["trace"]),
        agents=used_agents,
        tools=list(ctx.used_tools),
        memory=memory_after,
        skills=list(bag.get("active_skills") or []),
    )

    return {
        "reply": reply,
        "used_tools": list(ctx.used_tools),
        "used_agents": used_agents,
        "trace": list(bag["trace"]),
        "subagent_results": list(bag["results"]),
        "needs_human": ctx.needs_human,
        "lead_id": ctx.lead_id,
        "conversation_id": conversation_id,
        "run_id": run_id,
        "memory": memory_after,
        "memory_summary": await get_memory_summary(channel, external_id),
        "active_skills": list(bag.get("active_skills") or []),
        "memory_before": memory_before,
    }


async def run_agent_stream(
    user_text: str,
    *,
    history: list[dict[str, str]] | None = None,
    channel: str = "web",
    external_id: str = "",
    conversation_id: int | None = None,
    lead_id: int | None = None,
    customer_name: str = "Khách",
) -> AsyncIterator[dict[str, Any]]:
    result = await run_agent(
        user_text,
        history=history,
        channel=channel,
        external_id=external_id,
        conversation_id=conversation_id,
        lead_id=lead_id,
        customer_name=customer_name,
    )
    if result.get("memory_summary"):
        yield {"type": "memory", "summary": result["memory_summary"]}
    for step in result["trace"]:
        yield {"type": "trace", **step}
    reply = result["reply"]
    step = max(12, len(reply) // 20 or 12)
    for i in range(0, len(reply), step):
        yield {"type": "token", "content": reply[i : i + step]}
    yield {
        "type": "done",
        "reply": reply,
        "used_tools": result["used_tools"],
        "used_agents": result["used_agents"],
        "trace": result["trace"],
        "needs_human": result["needs_human"],
        "lead_id": result["lead_id"],
        "conversation_id": result["conversation_id"],
        "run_id": result.get("run_id"),
        "memory": result.get("memory"),
        "active_skills": result.get("active_skills"),
    }
