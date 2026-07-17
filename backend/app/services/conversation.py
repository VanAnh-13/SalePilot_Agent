import json

from sqlalchemy import select

from app.db.session import async_session
from app.models.entities import Conversation, Message


async def get_or_create_conversation(
    *,
    channel: str,
    external_id: str,
    customer_name: str = "Khách",
) -> Conversation:
    async with async_session() as session:
        stmt = (
            select(Conversation)
            .where(
                Conversation.channel == channel,
                Conversation.external_id == external_id,
                Conversation.status.in_(["open", "escalated"]),
            )
            .order_by(Conversation.id.desc())
        )
        conv = (await session.execute(stmt)).scalars().first()
        if conv:
            return conv
        conv = Conversation(
            channel=channel,
            external_id=external_id or f"{channel}-anon",
            customer_name=customer_name,
            status="open",
        )
        session.add(conv)
        await session.commit()
        await session.refresh(conv)
        return conv


async def append_message(
    conversation_id: int,
    role: str,
    content: str,
    meta: dict | None = None,
) -> Message:
    async with async_session() as session:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            meta_json=json.dumps(meta or {}, ensure_ascii=False),
        )
        session.add(msg)
        conv = await session.get(Conversation, conversation_id)
        if conv:
            conv.updated_at = msg.created_at  # type: ignore
        await session.commit()
        await session.refresh(msg)
        return msg


async def recent_history(conversation_id: int, limit: int = 12) -> list[dict[str, str]]:
    async with async_session() as session:
        rows = (
            (
                await session.execute(
                    select(Message)
                    .where(Message.conversation_id == conversation_id)
                    .order_by(Message.id.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
    rows = list(reversed(rows))
    out = []
    for m in rows:
        role = "assistant" if m.role == "assistant" else "user"
        out.append({"role": role, "content": m.content})
    return out
