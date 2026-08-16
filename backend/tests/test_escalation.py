"""Escalation service + tool: real ticket rows and takeover state (hermetic sqlite)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

_TMP = tempfile.mkdtemp(prefix="salepilot_escalation_")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP}/escalation.db"
os.environ["TRAJECTORY_ENABLED"] = "false"

from sqlalchemy import select  # noqa: E402

from app.agent.tools.crm import escalate_to_human  # noqa: E402
from app.agent.tools.runtime import ToolContext, set_ctx  # noqa: E402
from app.db.session import async_session, init_db  # noqa: E402
from app.models.entities import Conversation, OutboxMessage  # noqa: E402
from app.services.conversation import get_or_create_conversation  # noqa: E402
from app.services.escalation import (  # noqa: E402
    is_taken_over,
    open_escalation,
    resolve_takeover,
)

CHANNEL = "web"
EXT = "escalation-test-1"


class EscalationTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        import asyncio

        asyncio.run(init_db())

    async def asyncSetUp(self):
        async with async_session() as session:
            for conv in (
                await session.execute(
                    select(Conversation).where(Conversation.external_id == EXT)
                )
            ).scalars():
                await session.delete(conv)
            for msg in (
                await session.execute(select(OutboxMessage).where(OutboxMessage.user_id == EXT))
            ).scalars():
                await session.delete(msg)
            await session.commit()

    async def test_open_escalation_creates_ticket_and_flags_conversation(self):
        conv = await get_or_create_conversation(channel=CHANNEL, external_id=EXT, customer_name="T")
        ticket = await open_escalation(
            conversation_id=conv.id,
            channel=CHANNEL,
            external_id=EXT,
            reason="Khách khiếu nại",
            summary="Khách muốn gặp người",
        )
        self.assertIsNotNone(ticket)
        async with async_session() as session:
            managed = await session.get(Conversation, conv.id)
            self.assertEqual(managed.status, "escalated")
            self.assertTrue(managed.needs_human)
            row = (
                await session.execute(
                    select(OutboxMessage).where(
                        OutboxMessage.user_id == EXT,
                        OutboxMessage.direction == "escalation",
                    )
                )
            ).scalar_one()
            self.assertEqual(row.status, "pending_human")
            self.assertIn("gặp người", row.content)
        self.assertTrue(await is_taken_over(CHANNEL, EXT))

    async def test_resolve_takeover_reopens_conversation(self):
        conv = await get_or_create_conversation(channel=CHANNEL, external_id=EXT, customer_name="T")
        await open_escalation(
            conversation_id=conv.id,
            channel=CHANNEL,
            external_id=EXT,
            reason="test",
        )
        self.assertTrue(await is_taken_over(CHANNEL, EXT))
        resolved = await resolve_takeover(CHANNEL, EXT)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.status, "open")
        self.assertFalse(resolved.needs_human)
        self.assertFalse(await is_taken_over(CHANNEL, EXT))

    async def test_escalate_tool_writes_ticket_and_truthful_message(self):
        conv = await get_or_create_conversation(channel=CHANNEL, external_id=EXT, customer_name="T")
        set_ctx(
            ToolContext(
                channel=CHANNEL,
                external_id=EXT,
                conversation_id=conv.id,
                lead_id=None,
                customer_name="T",
            )
        )
        raw = await escalate_to_human.ainvoke({"reason": "yêu cầu gặp người", "summary": "khách bực"})
        data = json.loads(raw)
        self.assertTrue(data["escalated"])
        self.assertIsNotNone(data["ticket_id"])
        self.assertNotIn("ticket cho team CSKH", data["message"])
        self.assertTrue(await is_taken_over(CHANNEL, EXT))


if __name__ == "__main__":
    raise SystemExit(unittest.main())
