"""Persistence for Zalo webhook events.

Single responsibility: every DB write/read the webhook needs lives here, so
the HTTP handler in channels/zalo/webhook.py only keeps protocol concerns
(signature, payload parsing, routing, replying).
"""

from __future__ import annotations

from sqlalchemy import select

from app.db.session import async_session
from app.models.entities import Conversation, OutboxMessage, ProcessedEvent


async def was_event_processed(event_id: str) -> bool:
    async with async_session() as session:
        existing = (
            await session.execute(
                select(ProcessedEvent).where(ProcessedEvent.event_id == event_id)
            )
        ).scalar_one_or_none()
        return existing is not None


async def mark_event_processed(event_id: str) -> None:
    async with async_session() as session:
        session.add(ProcessedEvent(event_id=event_id))
        await session.commit()


async def record_inbound_message(external_id: str, content: str) -> None:
    async with async_session() as session:
        session.add(
            OutboxMessage(
                channel="zalo",
                user_id=external_id,
                direction="inbound",
                content=content,
                status="received",
            )
        )
        await session.commit()


async def mark_conversation_escalated(conversation_id: int) -> None:
    async with async_session() as session:
        c = await session.get(Conversation, conversation_id)
        if c:
            c.needs_human = True
            c.status = "escalated"
            await session.commit()
