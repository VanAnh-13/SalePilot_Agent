import asyncio
import json
from typing import Any

from langchain_core.tools import tool

from app.agent.constants import DELEGATE_TASK_CAP, LEAD_SUBAGENTS, TRACE_DETAIL_CAP
from app.agent.memory.tools import recall_customer, remember_customer
from app.agent.run_bag import bag_trace, get_run_bag, reset_run_bag
from app.agent.sandbox.tools import run_sandbox
from app.agent.skills.tools import activate_skill, list_skills_tool
from app.agent.subagents.base import SUBAGENTS, run_subagent
from app.agent.tools.catalog import (
    compare_products,
    get_product_detail,
    list_categories,
    recommend_top3,
    search_products,
)
from app.agent.tools.knowledge import search_knowledge
from app.agent.tools.crm import (
    create_lead,
    escalate_to_human,
    schedule_followup,
    update_lead_status,
)
from app.agent.tools.order import check_order_status, create_order_draft
from app.agent.tools.runtime import get_ctx
from app.agent.web.tools import fetch_page
from app.config import get_settings

__all__ = ["LEAD_TOOLS", "delegate", "delegate_many", "finalize", "get_run_bag", "reset_run_bag"]


async def _run_one(agent: str, task: str, context: str = "") -> dict[str, Any]:
    bag = get_run_bag()
    agent = agent.lower().strip()
    max_n = get_settings().max_subagents_per_turn
    if bag["delegates"] >= max_n:
        return {
            "agent": agent,
            "ok": False,
            "summary": f"Max {max_n} sub-agents/turn reached",
            "tools_used": [],
        }
    if agent not in SUBAGENTS:
        return {
            "agent": agent,
            "ok": False,
            "summary": f"Invalid agent. Valid: {list(LEAD_SUBAGENTS)}",
            "tools_used": [],
        }
    bag["delegates"] += 1
    bag_trace("lead", "delegate", f"→ {agent}: {task[:DELEGATE_TASK_CAP]}")
    bag_trace(agent, "start", task[:TRACE_DETAIL_CAP])
    result = await run_subagent(agent, task, context)
    bag["results"].append(result)
    tools = ", ".join(result.get("tools_used") or []) or "none"
    bag_trace(agent, "tool", tools)
    bag_trace(agent, "end", (result.get("summary") or "")[:TRACE_DETAIL_CAP])
    return {
        "agent": result["agent"],
        "ok": result["ok"],
        "summary": result["summary"],
        "tools_used": result["tools_used"],
    }


@tool
async def delegate(agent: str, task: str, context: str = "") -> str:
    """Giao việc cho 1 sub-agent. agent: catalog|knowledge|crm|order|escalation."""
    result = await _run_one(agent, task, context)
    return json.dumps(result, ensure_ascii=False)


@tool
async def delegate_many(tasks_json: str) -> str:
    """Chạy song song nhiều sub-agent. tasks_json: [{"agent":"catalog","task":"..."}]. Số lượng tối đa theo cấu hình `max_subagents_per_turn`."""
    try:
        tasks = json.loads(tasks_json) if isinstance(tasks_json, str) else tasks_json
    except json.JSONDecodeError:
        return json.dumps({"error": "tasks_json invalid"}, ensure_ascii=False)
    if not isinstance(tasks, list) or not tasks:
        return json.dumps({"error": "need non-empty list"}, ensure_ascii=False)

    max_n = get_settings().max_subagents_per_turn
    tasks = tasks[:max_n]
    bag_trace("lead", "delegate_many", f"parallel n={len(tasks)}")

    async def one(item: dict) -> dict:
        return await _run_one(
            str(item.get("agent", "")),
            str(item.get("task", "")),
            str(item.get("context", "")),
        )

    results = await asyncio.gather(*[one(t) for t in tasks if isinstance(t, dict)])
    return json.dumps({"results": list(results), "parallel": True}, ensure_ascii=False)


@tool
async def finalize(reply: str) -> str:
    """Hoàn tất lượt: gửi câu trả lời tiếng Việt cuối cùng cho khách hàng."""
    reply = (reply or "").strip()
    if not reply:
        return json.dumps({"error": "reply rỗng"}, ensure_ascii=False)
    bag = get_run_bag()
    bag["final"] = reply
    ctx = get_ctx()
    bag_trace("lead", "finalize", reply[:TRACE_DETAIL_CAP])
    return json.dumps(
        {
            "ok": True,
            "needs_human": ctx.needs_human,
            "lead_id": ctx.lead_id,
            "message": "Đã chốt câu trả lời cho khách.",
        },
        ensure_ascii=False,
    )


LEAD_TOOLS = [
    # Deterministic tools are called DIRECTLY — no nested sub-agent ReAct loop.
    # This is the hot path and the main latency win. The same applies to the
    # CRM/order writes below: saving a phone number must not cost a full extra
    # LLM round-trip through a sub-agent.
    recommend_top3,
    search_products,
    compare_products,
    get_product_detail,
    list_categories,
    search_knowledge,
    create_lead,
    update_lead_status,
    schedule_followup,
    create_order_draft,
    check_order_status,
    escalate_to_human,
    # delegate/delegate_many stay for genuinely multi-step sub-agent work
    # (research-style tasks), and every tool advertised to the model is bound.
    delegate,
    delegate_many,
    finalize,
    recall_customer,
    remember_customer,
    list_skills_tool,
    activate_skill,
    run_sandbox,
    fetch_page,
]
