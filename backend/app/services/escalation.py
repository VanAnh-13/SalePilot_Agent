"""Human escalation: real ticket records and takeover state.

When the agent hands a conversation to a human advisor, this service
(a) marks the conversation escalated and (b) writes an OutboxMessage
ticket (direction="escalation", status="pending_human") that the owner
dashboard can see. While a conversation is taken over, the bot must not
auto-reply — callers check ``is_taken_over`` before running the agent.
"""

from __future__ import annotations

from sqlalchemy import select

from app.db.session import async_session
from app.models.entities import Conversation, Lead, OutboxMessage


async def open_escalation(
    *,
    conversation_id: int | None,
    channel: str,
    external_id: str,
    reason: str,
    summary: str = "",
    lead_id: int | None = None,
) -> OutboxMessage | None:
    """Mark the conversation escalated and write the internal ticket row.

    The OutboxMessage row is the dispatch record a human/owner consumes;
    pushing it to an external channel (email, Zalo OA to staff) is future
    work. Returns the ticket, or None when there is no conversation yet.
    """
    ticket: OutboxMessage | None = None
    async with async_session() as session:
        if conversation_id:
            conv = await session.get(Conversation, conversation_id)
            if conv:
                conv.needs_human = True
                conv.status = "escalated"
                conv.summary = summary or reason
        if lead_id:
            lead = await session.get(Lead, lead_id)
            if lead:
                lead.notes = ((lead.notes or "") + f"\n[ESCALATE] {reason}").strip()
        ticket = OutboxMessage(
            channel=channel,
            user_id=external_id,
            direction="escalation",
            content=(summary or reason)[:2000],
            status="pending_human",
        )
        session.add(ticket)
        await session.commit()
    return ticket


async def _get_conversation(channel: str, external_id: str) -> Conversation | None:
    async with async_session() as session:
        return (
            await session.execute(
                select(Conversation)
                .where(Conversation.channel == channel, Conversation.external_id == external_id)
                .order_by(Conversation.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()


async def is_taken_over(channel: str, external_id: str) -> bool:
    """True while the latest conversation for this customer is escalated."""
    conv = await _get_conversation(channel, external_id)
    return bool(conv and conv.status == "escalated")


async def resolve_takeover(channel: str, external_id: str) -> Conversation | None:
    """Hand the conversation back to the bot (owner action)."""
    conv = await _get_conversation(channel, external_id)
    if conv is None:
        return None
    async with async_session() as session:
        managed = await session.get(Conversation, conv.id)
        if managed is None:
            return None
        managed.status = "open"
        managed.needs_human = False
        await session.commit()
        return managed
