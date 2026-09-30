"""True token streaming on the LLM graph route."""

from __future__ import annotations

import os
import unittest
from unittest.mock import AsyncMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("TRAJECTORY_ENABLED", "false")

from langchain_core.language_models.chat_models import BaseChatModel  # noqa: E402
from langchain_core.messages import AIMessage, AIMessageChunk  # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult  # noqa: E402

import app.agent.graph as graph_mod  # noqa: E402
from app.agent.graph import run_agent_stream  # noqa: E402

CHUNKS = ["Chào ", "anh/chị, ", "em là ", "trợ lý ", "SalePilot."]


class _StreamingFakeModel(BaseChatModel):
    """Streams five real chunks so token-level events are observable."""

    @property
    def _llm_type(self) -> str:
        return "streaming-fake"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        text = "".join(CHUNKS)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        for piece in CHUNKS:
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=piece))
            if run_manager is not None:
                await run_manager.on_llm_new_token(piece, chunk=chunk)
            yield chunk


class StreamingTests(unittest.IsolatedAsyncioTestCase):
    async def test_llm_route_streams_tokens_then_done(self):
        events = []
        with (
            patch.object(graph_mod, "has_llm_key", return_value=True),
            patch.object(graph_mod, "get_chat_model", return_value=_StreamingFakeModel()),
            patch.object(graph_mod, "_try_fast_path", new=AsyncMock(return_value=None)),
            patch.object(graph_mod, "load_profile", new=AsyncMock(return_value={})),
            patch.object(graph_mod, "get_memory_summary", new=AsyncMock(return_value="")),
            patch.object(graph_mod, "maybe_extract_from_text", new=AsyncMock()),
            patch.object(graph_mod, "save_trajectory", new=AsyncMock(return_value="run-1")),
            patch.object(graph_mod, "maybe_write_skill_from_run", return_value=None),
        ):
            graph_mod._graph = None  # rebuild with the fake model
            try:
                async for event in run_agent_stream(
                    "chính sách bảo hành thế nào ạ",
                    channel="web",
                    external_id="stream-1",
                ):
                    events.append(event)
            finally:
                graph_mod._graph = None

        tokens = [e["content"] for e in events if e["type"] == "token"]
        dones = [e for e in events if e["type"] == "done"]
        self.assertTrue(dones)
        done = dones[-1]
        # Real streaming means several incremental tokens, not one final blob.
        self.assertGreaterEqual(len(tokens), 4)
        self.assertEqual("".join(tokens), "".join(CHUNKS))
        self.assertEqual(done["reply"], "".join(CHUNKS))
        self.assertEqual(done["run_id"], "run-1")
        # Every token arrives BEFORE the done event.
        first_done_idx = events.index(dones[0])
        last_token_idx = max(i for i, e in enumerate(events) if e["type"] == "token")
        self.assertLess(last_token_idx, first_done_idx)

    async def test_offline_route_keeps_batched_events(self):
        fake_result = {
            "reply": "Trả lời offline." * 5,
            "used_tools": [],
            "used_agents": ["lead"],
            "trace": [{"agent": "lead", "event": "start"}],
            "needs_human": False,
            "lead_id": None,
            "conversation_id": 7,
            "run_id": "run-2",
            "memory": {},
            "memory_summary": "SĐT: 09xx",
            "active_skills": [],
            "decision": None,
        }
        events = []
        with (
            patch.object(graph_mod, "has_llm_key", return_value=False),
            patch.object(graph_mod, "load_profile", new=AsyncMock(return_value={})),
            patch.object(graph_mod, "get_memory_summary", new=AsyncMock(return_value="")),
            patch.object(graph_mod, "maybe_extract_from_text", new=AsyncMock()),
            patch.object(graph_mod, "_run_offline_route", new=AsyncMock(return_value=fake_result)),
        ):
            async for event in run_agent_stream(
                "alo", channel="web", external_id="stream-2"
            ):
                events.append(event)

        types = [e["type"] for e in events]
        self.assertEqual(types[0], "memory")
        self.assertIn("trace", types)
        self.assertGreater(types.count("token"), 1)
        self.assertEqual(types[-1], "done")
        self.assertEqual(events[-1]["reply"], fake_result["reply"])


if __name__ == "__main__":
    raise SystemExit(unittest.main())
