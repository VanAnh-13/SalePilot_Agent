"""Unified channel ingress: web + zalo share one path into the agent."""

from __future__ import annotations

from typing import Any

from app.agent.graph import run_agent
from app.services.conversation import append_message, get_or_create_conversation, recent_history


async def ingest_message(
    *,
    channel: str,
    external_id: str,
    text: str,
    customer_name: str = "Khách",
    conversation_id: int | None = None,
) -> dict[str, Any]:
    conv = await get_or_create_conversation(
        channel=channel,
        external_id=external_id,
        customer_name=customer_name,
    )
    conv_id = conversation_id or conv.id
    await append_message(conv_id, "user", text)
    history = await recent_history(conv_id)

    result = await run_agent(
        text,
        history=history[:-1],
        channel=channel,
        external_id=external_id,
        conversation_id=conv_id,
        lead_id=conv.lead_id,
        customer_name=customer_name,
    )
    await append_message(
        conv_id,
        "assistant",
        result["reply"],
        meta={
            "used_agents": result.get("used_agents"),
            "used_tools": result.get("used_tools"),
            "trace": result.get("trace"),
            "run_id": result.get("run_id"),
            "memory": result.get("memory"),
        },
    )
    result["conversation_id"] = conv_id
    return result
