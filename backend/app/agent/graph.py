import asyncio
import json
import logging
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

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
from app.observability.metrics import record_run
from app.services.leads import upsert_lead_record

logger = logging.getLogger(__name__)


def _record_route(result: dict[str, Any], route: str, started: float) -> dict[str, Any]:
    """Tag the run with its serving route and record latency for /runs/metrics."""
    result["route"] = route
    record_run(route, (perf_counter() - started) * 1000.0)
    return result


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

def _looks_like_recommend(user_text: str, need: dict) -> bool:
    if phone_in_text(user_text):
        return False
    if (
        has_intent(user_text, FAQ_KEYWORDS)
        or has_intent(user_text, ESCALATION_KEYWORDS)
        or has_intent(user_text, COMPARE_KEYWORDS)
    ):
        return False
    return bool(need.get("category"))


async def _save_consultation_lead(
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
        score=0.6 if prof.get("phone") else 0.5,
        status="qualified",
        conversation_id=conversation_id,
    )
    return {"lead_id": lead.id, "summary": f"lead#{lead.id}"}


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
        need, _ = await merge_turn_need(user_text, stored)
        await fill_budget_from_profile(need, channel=channel, external_id=external_id)
        if not _looks_like_recommend(user_text, need):
            return None

        _prepare_ctx(
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
                crm = await _save_consultation_lead(
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


_LLM_ERROR_REPLY = (
    "Xin lỗi, hiện em chưa kết nối được trợ lý AI (mạng/LLM đang bận). "
    "Anh/chị mô tả nhu cầu kèm ngân sách giúp em nhé "
    "(vd: “tủ lạnh cho 4 người dưới 15 triệu”, “máy lạnh phòng 20m² tầm 12 triệu”) "
    "— em sẽ gợi ý sản phẩm ngay, hoặc để lại SĐT để tư vấn viên gọi lại ạ."
)
_NO_FINAL_REPLY = (
    "Em xin lỗi, hệ thống multi-agent chưa chốt được câu trả lời. "
    "Bạn thử hỏi lại giúp em nhé."
)


async def _run_offline_route(
    user_text: str,
    *,
    channel: str,
    external_id: str,
    conversation_id: int | None,
    lead_id: int | None,
    customer_name: str,
) -> dict[str, Any]:
    """Serve via the rule-based offline path and persist its trajectory."""
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
        decision=result.get("decision"),
    )
    result["run_id"] = run_id
    result["memory"] = memory_after
    result["memory_summary"] = await get_memory_summary(channel, external_id)
    return result


def _build_graph_messages(
    system_prompt: str,
    history: list[dict[str, str]] | None,
    user_text: str,
) -> list:
    messages: list = [SystemMessage(content=system_prompt)]
    for h in history or []:
        role = h.get("role", "user")
        content = h.get("content", "")
        if role == "assistant":
            messages.append(AIMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))
    messages.append(HumanMessage(content=user_text))
    return messages


async def _finalize_llm_run(
    *,
    user_text: str,
    channel: str,
    external_id: str,
    conversation_id: int | None,
    memory_before: dict[str, Any],
    started: float,
    llm_error: Exception | None = None,
) -> dict[str, Any]:
    """Shared post-processing for the LLM graph route (batch and streaming)."""
    bag = get_run_bag()
    ctx = get_ctx()
    route = "llm_graph"
    reply = bag.get("final") or ""
    if not reply:
        if llm_error is not None:
            route = "llm_error_fallback"
            bag["trace"].append(
                {"agent": "lead", "event": "llm_error", "detail": type(llm_error).__name__}
            )
            reply = _LLM_ERROR_REPLY
        else:
            reply = _NO_FINAL_REPLY

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
        decision=bag.get("decision"),
    )

    return _record_route(
        {
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
            "decision": bag.get("decision"),
        },
        route,
        started,
    )


def _graph_state(
    messages: list,
    *,
    channel: str,
    external_id: str,
    conversation_id: int | None,
    lead_id: int | None,
    customer_name: str,
) -> dict[str, Any]:
    return {
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
    }


async def _stream_graph_tokens(state: dict[str, Any]) -> AsyncIterator[str]:
    """Yield lead-node reply text as the model produces it (true streaming).

    stream_mode="messages" emits one chunk per token for models that support
    streaming; tool-call fragments and non-lead nodes are filtered out.
    """
    graph = get_graph()
    async for msg, meta in graph.astream(state, config={"recursion_limit": 24}, stream_mode="messages"):
        if meta.get("langgraph_node") != "lead":
            continue
        if getattr(msg, "tool_call_chunks", None):
            continue
        content = getattr(msg, "content", "")
        if isinstance(content, str) and content:
            yield content


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
    started = perf_counter()
    memory_before = await load_profile(channel, external_id)
    memory_summary = await get_memory_summary(channel, external_id)
    await maybe_extract_from_text(channel, external_id, user_text)

    if not has_llm_key():
        result = await _run_offline_route(
            user_text,
            channel=channel,
            external_id=external_id,
            conversation_id=conversation_id,
            lead_id=lead_id,
            customer_name=customer_name,
        )
        return _record_route(result, "offline", started)

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
        return _record_route(fast, "fast_path", started)

    reset_run_bag()
    _prepare_ctx(
        channel=channel,
        external_id=external_id,
        conversation_id=conversation_id,
        lead_id=lead_id,
        customer_name=customer_name,
    )

    sys = _system_with_memory(lead_system_prompt(), memory_summary)
    messages = _build_graph_messages(sys, history, user_text)
    state = _graph_state(
        messages,
        channel=channel,
        external_id=external_id,
        conversation_id=conversation_id,
        lead_id=lead_id,
        customer_name=customer_name,
    )

    graph = get_graph()
    llm_error: Exception | None = None
    try:
        await graph.ainvoke(state, config={"recursion_limit": 24})
    except Exception as exc:  # LLM timeout / rate-limit / endpoint down
        # Never surface a raw 500 to the customer: degrade to a friendly message
        # and keep serving. The deterministic recommend fast-path already handles
        # clear product intents without the LLM, so this only affects the
        # ambiguous / FAQ / compare queries that need reasoning.
        llm_error = exc

    return await _finalize_llm_run(
        user_text=user_text,
        channel=channel,
        external_id=external_id,
        conversation_id=conversation_id,
        memory_before=memory_before,
        started=started,
        llm_error=llm_error,
    )


def _chunk_reply(reply: str) -> list[str]:
    """Split a fully-computed reply into UI-sized pieces (offline/fast routes)."""
    step = max(12, len(reply) // 20 or 12)
    return [reply[i : i + step] for i in range(0, len(reply), step)]


def _done_event(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "done",
        "reply": result["reply"],
        "used_tools": result["used_tools"],
        "used_agents": result["used_agents"],
        "trace": result["trace"],
        "needs_human": result["needs_human"],
        "lead_id": result["lead_id"],
        "conversation_id": result["conversation_id"],
        "run_id": result.get("run_id"),
        "memory": result.get("memory"),
        "active_skills": result.get("active_skills"),
        "decision": result.get("decision"),
    }


def _yield_batched(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Event sequence for routes that finish before streaming (offline/fast)."""
    events: list[dict[str, Any]] = []
    if result.get("memory_summary"):
        events.append({"type": "memory", "summary": result["memory_summary"]})
    for step in result["trace"]:
        events.append({"type": "trace", **step})
    for piece in _chunk_reply(result["reply"]):
        events.append({"type": "token", "content": piece})
    events.append(_done_event(result))
    return events


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
    started = perf_counter()
    memory_before = await load_profile(channel, external_id)
    memory_summary = await get_memory_summary(channel, external_id)
    await maybe_extract_from_text(channel, external_id, user_text)

    if not has_llm_key():
        result = await _run_offline_route(
            user_text,
            channel=channel,
            external_id=external_id,
            conversation_id=conversation_id,
            lead_id=lead_id,
            customer_name=customer_name,
        )
        result = _record_route(result, "offline", started)
        for event in _yield_batched(result):
            yield event
        return

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
        result = _record_route(fast, "fast_path", started)
        for event in _yield_batched(result):
            yield event
        return

    # LLM graph route: stream real tokens as the lead model produces them.
    reset_run_bag()
    _prepare_ctx(
        channel=channel,
        external_id=external_id,
        conversation_id=conversation_id,
        lead_id=lead_id,
        customer_name=customer_name,
    )
    sys = _system_with_memory(lead_system_prompt(), memory_summary)
    messages = _build_graph_messages(sys, history, user_text)
    state = _graph_state(
        messages,
        channel=channel,
        external_id=external_id,
        conversation_id=conversation_id,
        lead_id=lead_id,
        customer_name=customer_name,
    )

    if memory_summary:
        yield {"type": "memory", "summary": memory_summary}

    llm_error: Exception | None = None
    try:
        async for piece in _stream_graph_tokens(state):
            yield {"type": "token", "content": piece}
    except Exception as exc:  # provider died mid-stream → friendly fallback
        llm_error = exc

    result = await _finalize_llm_run(
        user_text=user_text,
        channel=channel,
        external_id=external_id,
        conversation_id=conversation_id,
        memory_before=memory_before,
        started=started,
        llm_error=llm_error,
    )
    for step in result["trace"]:
        yield {"type": "trace", **step}
    yield _done_event(result)
