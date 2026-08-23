import logging
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent.constants import GRAPH_RECURSION_LIMIT, TRACE_DETAIL_CAP
from app.agent.events import RunResult, batched_events, done_event
from app.agent.fast_path import try_fast_path as _try_fast_path
from app.agent.lead_tools import LEAD_TOOLS
from app.agent.llm import get_chat_model, has_llm_key
from app.agent.memory.store import get_memory_summary, load_profile, maybe_extract_from_text
from app.agent.offline import run_offline_multi_agent
from app.agent.prompts import lead_system_prompt
from app.agent.run_bag import get_run_bag, reset_run_bag
from app.agent.skills.loader import SKILL_BODY_CAP, load_skill_body
from app.agent.skills.matcher import match_skills
from app.agent.skills.writer import maybe_write_skill_from_run
from app.agent.state import AgentState
from app.agent.tools.runtime import get_ctx, prepare_ctx
from app.agent.trajectory.export import save_trajectory
from app.config import get_settings
from app.observability.metrics import record_run

logger = logging.getLogger(__name__)

# Look-back windows and caps for the lead-node message injection (skill bodies
# and sub-agent results) and the finalize trace entry.
SKILL_MARKER_LOOKBACK = 4
SUBAGENT_MARKER_LOOKBACK = 3
SUBAGENT_RESULTS_KEEP = 5
SUBAGENT_BRIEF_CAP = 400


def _record_route(result: dict[str, Any], route: str, started: float) -> dict[str, Any]:
    """Tag the run with its serving route and record latency for /runs/metrics."""
    result["route"] = route
    record_run(route, (perf_counter() - started) * 1000.0)
    return result


def _mark_final_message(bag: dict[str, Any], content: str) -> None:
    """Record the lead's plain-text answer as the final reply.

    Extracted from the graph edge decision so the routing side-effect (mutating
    the run bag) is explicit rather than buried in `should_continue`.
    """
    bag["final"] = content.strip()
    bag["trace"].append(
        {"agent": "lead", "event": "finalize", "detail": content[:TRACE_DETAIL_CAP]}
    )


def _build_graph():
    model = get_chat_model().bind_tools(LEAD_TOOLS)
    tool_node = ToolNode(LEAD_TOOLS)

    async def lead_node(state: AgentState) -> dict[str, Any]:
        messages = list(state.get("messages") or [])
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=lead_system_prompt()), *messages]
        bag = get_run_bag()
        # inject activated skill bodies (already capped once at bag insertion)
        if bag.get("skill_bodies"):
            skill_blob = "\n\n".join(
                f"[Skill:{n}]\n{body}" for n, body in bag["skill_bodies"].items()
            )
            skill_content = f"[Active skills]\n{skill_blob}"
            replaced = False
            for i, m in enumerate(messages):
                if isinstance(m, HumanMessage) and str(m.content).startswith("[Active skills]"):
                    messages[i] = HumanMessage(content=skill_content)
                    replaced = True
                    break
            if not replaced:
                messages = [*messages, HumanMessage(content=skill_content)]
        if bag["results"]:
            brief = "\n".join(
                f"- {r['agent']}: {r['summary'][:SUBAGENT_BRIEF_CAP]}"
                for r in bag["results"][-SUBAGENT_RESULTS_KEEP:]
            )
            result_content = f"[Sub-agent results]\n{brief}\n\nHãy tiếp tục delegate/delegate_many hoặc finalize."
            replaced = False
            for i, m in enumerate(messages):
                if isinstance(m, HumanMessage) and str(m.content).startswith("[Sub-agent results]"):
                    messages[i] = HumanMessage(content=result_content)
                    replaced = True
                    break
            if not replaced:
                messages = [*messages, HumanMessage(content=result_content)]
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
                _mark_final_message(bag, content)
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


def _system_with_memory(base: str, memory_summary: str) -> str:
    if not memory_summary:
        return base
    return base + f"\n\n[Customer memory]\n{memory_summary}\nDùng remember_customer để cập nhật khi có fact mới."


def _auto_activate_skills(user_text: str) -> None:
    """Load lexically matching skills into the run bag (data-driven matcher)."""
    if not get_settings().auto_activate_skills:
        return
    bag = get_run_bag()
    for name in match_skills(user_text):
        body = load_skill_body(name)
        if not body:
            continue
        active = bag.setdefault("active_skills", [])
        if name not in active:
            active.append(name)
        bag.setdefault("skill_bodies", {})[name] = body[:SKILL_BODY_CAP]
        bag["trace"].append({"agent": "lead", "event": "skill", "detail": f"auto:{name}"})


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
_RECURSION_REPLY = (
    "Em đã tra nhiều bước cho câu này nhưng chưa chốt được — anh/chị cho em thêm "
    "chi tiết (ngân sách, diện tích phòng, số người dùng) để em đề xuất sát nhu cầu nhé ạ."
)


async def _run_offline_route(
    user_text: str,
    *,
    channel: str,
    external_id: str,
    conversation_id: int | None,
    lead_id: int | None,
    customer_name: str,
) -> RunResult:
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
    try:
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
    except Exception:
        # Telemetry must never break the customer reply (dir unwritable, DB
        # insert error, ...). The fast path already guards this; match it here.
        logger.warning("save_trajectory failed (offline route)", exc_info=True)
        run_id = None
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
) -> RunResult:
    """Shared post-processing for the LLM graph route (batch and streaming)."""
    bag = get_run_bag()
    ctx = get_ctx()
    route = "llm_graph"
    reply = bag.get("final") or ""
    if not reply:
        if llm_error is not None:
            if isinstance(llm_error, GraphRecursionError):
                # Hit the lead↔tools recursion cap after (possibly successful)
                # tool work — the LLM was healthy, so don't misreport it as a
                # connectivity problem.
                route = "recursion_limit"
                bag["trace"].append(
                    {"agent": "lead", "event": "recursion_limit", "detail": "graph hit recursion cap"}
                )
                reply = _RECURSION_REPLY
            else:
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
    try:
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
    except Exception:
        logger.warning("save_trajectory failed (llm route)", exc_info=True)
        run_id = None

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
    async for msg, meta in graph.astream(
        state, config={"recursion_limit": GRAPH_RECURSION_LIMIT}, stream_mode="messages"
    ):
        if meta.get("langgraph_node") != "lead":
            continue
        if getattr(msg, "tool_call_chunks", None):
            continue
        content = getattr(msg, "content", "")
        if isinstance(content, str) and content:
            yield content


async def _prelude(
    channel: str, external_id: str, user_text: str
) -> tuple[dict[str, Any], str]:
    """Load memory (and extract any new facts) before choosing a route."""
    memory_before = await load_profile(channel, external_id)
    memory_summary = await get_memory_summary(channel, external_id)
    await maybe_extract_from_text(channel, external_id, user_text)
    return memory_before, memory_summary


async def _serve_early_routes(
    user_text: str,
    *,
    channel: str,
    external_id: str,
    conversation_id: int | None,
    lead_id: int | None,
    customer_name: str,
    memory_summary: str,
    memory_before: dict[str, Any],
) -> tuple[RunResult, str] | None:
    """Short-circuit the offline and fast-path routes; None → run the graph."""
    if not has_llm_key():
        result = await _run_offline_route(
            user_text,
            channel=channel,
            external_id=external_id,
            conversation_id=conversation_id,
            lead_id=lead_id,
            customer_name=customer_name,
        )
        return result, "offline"

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
        return fast, "fast_path"
    return None


def _prepare_llm_graph(
    user_text: str,
    *,
    channel: str,
    external_id: str,
    conversation_id: int | None,
    lead_id: int | None,
    customer_name: str,
    history: list[dict[str, str]] | None,
    memory_summary: str,
) -> dict[str, Any]:
    """Reset run state, activate skills, and assemble graph input state."""
    reset_run_bag()
    prepare_ctx(
        channel=channel,
        external_id=external_id,
        conversation_id=conversation_id,
        lead_id=lead_id,
        customer_name=customer_name,
    )
    _auto_activate_skills(user_text)
    sys = _system_with_memory(lead_system_prompt(), memory_summary)
    messages = _build_graph_messages(sys, history, user_text)
    return _graph_state(
        messages,
        channel=channel,
        external_id=external_id,
        conversation_id=conversation_id,
        lead_id=lead_id,
        customer_name=customer_name,
    )


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
    memory_before, memory_summary = await _prelude(channel, external_id, user_text)

    early = await _serve_early_routes(
        user_text,
        channel=channel,
        external_id=external_id,
        conversation_id=conversation_id,
        lead_id=lead_id,
        customer_name=customer_name,
        memory_summary=memory_summary,
        memory_before=memory_before,
    )
    if early is not None:
        result, route = early
        return _record_route(result, route, started)

    state = _prepare_llm_graph(
        user_text,
        channel=channel,
        external_id=external_id,
        conversation_id=conversation_id,
        lead_id=lead_id,
        customer_name=customer_name,
        history=history,
        memory_summary=memory_summary,
    )

    graph = get_graph()
    llm_error: Exception | None = None
    try:
        await graph.ainvoke(state, config={"recursion_limit": GRAPH_RECURSION_LIMIT})
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
    memory_before, memory_summary = await _prelude(channel, external_id, user_text)

    early = await _serve_early_routes(
        user_text,
        channel=channel,
        external_id=external_id,
        conversation_id=conversation_id,
        lead_id=lead_id,
        customer_name=customer_name,
        memory_summary=memory_summary,
        memory_before=memory_before,
    )
    if early is not None:
        result, route = early
        result = _record_route(result, route, started)
        for event in batched_events(result):
            yield event
        return

    state = _prepare_llm_graph(
        user_text,
        channel=channel,
        external_id=external_id,
        conversation_id=conversation_id,
        lead_id=lead_id,
        customer_name=customer_name,
        history=history,
        memory_summary=memory_summary,
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
    yield done_event(result)
