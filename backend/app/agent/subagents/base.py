import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.agent.llm import get_chat_model
from app.agent.prompts import subagent_prompt
from app.agent.tools.catalog import compare_products, get_product_detail, recommend_top3, search_products
from app.agent.tools.crm import create_lead, escalate_to_human, schedule_followup, update_lead_status
from app.agent.tools.knowledge import search_knowledge
from app.agent.tools.order import create_order_draft
from app.agent.tools.runtime import get_ctx, note_tool

SUBAGENTS: dict[str, list] = {
    "catalog": [search_products, get_product_detail, compare_products, recommend_top3],
    "knowledge": [search_knowledge],
    "crm": [create_lead, update_lead_status, schedule_followup],
    "order": [create_order_draft],
    "escalation": [escalate_to_human],
}

MAX_SUBAGENT_STEPS = 4


async def run_subagent(name: str, task: str, context: str = "") -> dict[str, Any]:
    name = name.lower().strip()
    if name not in SUBAGENTS:
        return {
            "agent": name,
            "task": task,
            "summary": f"Unknown agent '{name}'. Valid: {list(SUBAGENTS)}",
            "data": {},
            "tools_used": [],
            "ok": False,
        }

    tools = SUBAGENTS[name]
    tools_by_name = {t.name: t for t in tools}
    model = get_chat_model().bind_tools(tools)
    used_before = list(get_ctx().used_tools)

    user_blob = task if not context else f"{task}\n\nContext:\n{context}"
    messages: list = [
        SystemMessage(
            content=subagent_prompt(name)
            + "\nDùng tool khi cần. Kết thúc bằng tóm tắt ngắn cho Lead (có sku/source nếu catalog)."
        ),
        HumanMessage(content=user_blob),
    ]

    final_text = ""
    for _ in range(MAX_SUBAGENT_STEPS):
        ai: AIMessage = await model.ainvoke(messages)
        messages.append(ai)
        if not ai.tool_calls:
            final_text = ai.content if isinstance(ai.content, str) else str(ai.content or "")
            break
        for tc in ai.tool_calls:
            note_tool(f"{name}:{tc['name']}")
            tool_fn = tools_by_name.get(tc["name"])
            if not tool_fn:
                result = json.dumps({"error": f"tool {tc['name']} not allowed for {name}"})
            else:
                try:
                    result = await tool_fn.ainvoke(tc["args"])
                except Exception as e:
                    result = json.dumps({"error": str(e)}, ensure_ascii=False)
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
    else:
        plain = get_chat_model()
        ai = await plain.ainvoke(
            messages + [HumanMessage(content="Tóm tắt kết quả cho lead agent (ngắn).")]
        )
        final_text = ai.content if isinstance(ai.content, str) else str(ai.content or "")

    used_after = list(get_ctx().used_tools)
    tools_used = used_after[len(used_before) :]
    if not final_text:
        final_text = "Hoàn thành task (xem tools)."

    return {
        "agent": name,
        "task": task,
        "summary": final_text[:2000],
        "data": {},
        "tools_used": tools_used,
        "ok": True,
    }
