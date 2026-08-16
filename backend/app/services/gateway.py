"""Unified channel ingress: web + zalo share one path into the agent."""

from __future__ import annotations

import logging
from typing import Any

from app.agent.graph import run_agent
from app.agent.memory.store import maybe_summarize_conversation
from app.services.conversation import append_message, get_or_create_conversation, recent_history
from app.services.escalation import is_taken_over

logger = logging.getLogger(__name__)

TAKEOVER_REPLY = (
    "Hội thoại đang được tư vấn viên tiếp nhận. "
    "Tin nhắn của anh/chị đã được ghi lại và sẽ có người phản hồi ạ."
)


async def ingest_message(
    *,
    channel: str,
    external_id: str,
    text: str,
    customer_name: str = "Khách",
) -> dict[str, Any]:
    # Conversation is always derived server-side from (channel, external_id).
    # Never accept a caller-supplied conversation_id: that would allow IDOR
    # (one user hijacking another user's conversation history).
    conv = await get_or_create_conversation(
        channel=channel,
        external_id=external_id,
        customer_name=customer_name,
    )
    conv_id = conv.id
    await append_message(conv_id, "user", text)

    # Human takeover: after escalation the bot must stay silent. The message
    # above is still stored so the human advisor sees what the customer said.
    if await is_taken_over(channel, external_id):
        await append_message(conv_id, "assistant", TAKEOVER_REPLY, meta={"takeover": True})
        return {
            "reply": TAKEOVER_REPLY,
            "used_tools": [],
            "used_agents": ["lead"],
            "trace": [{"agent": "lead", "event": "human_takeover", "detail": "bot im lặng"}],
            "subagent_results": [],
            "needs_human": True,
            "lead_id": conv.lead_id,
            "conversation_id": conv_id,
            "run_id": None,
            "active_skills": [],
            "decision": None,
        }

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
            "decision": result.get("decision"),
            # memory intentionally excluded — PII only via admin /memory
        },
    )
    # Best-effort rolling summary of the stored conversation; skipped offline
    # or when disabled — must never affect the reply just served.
    try:
        await maybe_summarize_conversation(channel, external_id, await recent_history(conv_id))
    except Exception:
        logger.warning(
            "conversation summary failed (channel=%s external_id=%s)",
            channel,
            external_id,
            exc_info=True,
        )
    result["conversation_id"] = conv_id
    return result
