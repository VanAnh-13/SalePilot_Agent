from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent.lead_tools import LEAD_TOOLS
from app.agent.run_bag import get_run_bag, reset_run_bag
from app.agent.llm import get_chat_model, has_llm_key
from app.agent.memory.store import get_memory_summary, load_profile, maybe_extract_from_text
from app.agent.offline import run_offline_multi_agent
from app.agent.prompts import lead_system_prompt
from app.agent.skills.writer import maybe_write_skill_from_run
from app.agent.state import AgentState
from app.agent.tools.runtime import ToolContext, get_ctx, set_ctx
from app.agent.trajectory.export import save_trajectory


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
                f"[Skill:{n}]\n{body[:2000]}" for n, body in bag["skill_bodies"].items()
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

    bag = get_run_bag()
    ctx = get_ctx()
    reply = bag.get("final") or ""
    if not reply:
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
