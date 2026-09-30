"""Rolling LLM conversation summary in customer memory."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

_TMP = tempfile.mkdtemp(prefix="salepilot_memory_summary_")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP}/memory_summary.db"
os.environ["TRAJECTORY_ENABLED"] = "false"

from langchain_core.language_models.chat_models import BaseChatModel  # noqa: E402
from langchain_core.messages import AIMessage  # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatResult  # noqa: E402

from app.agent.memory.store import (  # noqa: E402
    get_memory_summary,
    load_profile,
    maybe_summarize_conversation,
)
from app.config import get_settings  # noqa: E402
from app.db.session import init_db  # noqa: E402


class _SummaryModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "summary-fake"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content="Khách cần tủ lạnh dưới 15tr, đã đề xuất top 3."))]
        )


def _history(n: int) -> list[dict[str, str]]:
    return [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"tin nhắn số {i}"}
        for i in range(n)
    ]


class MemorySummaryTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        import asyncio

        asyncio.run(init_db())

    async def test_summary_written_at_threshold_and_visible_in_memory_summary(self):
        ch, ext = "web", "summary-1"
        with (
            patch("app.agent.llm.has_llm_key", return_value=True),
            patch("app.agent.llm.get_chat_model", return_value=_SummaryModel()),
        ):
            # Below threshold: no summary yet.
            self.assertIsNone(await maybe_summarize_conversation(ch, ext, _history(4)))
            # At threshold: summary written.
            got = await maybe_summarize_conversation(ch, ext, _history(6))
            self.assertIsNotNone(got)
            # 2 more messages (< threshold delta) → not refreshed.
            got2 = await maybe_summarize_conversation(ch, ext, _history(8))
            self.assertEqual(got2, got)

        profile = await load_profile(ch, ext)
        self.assertIn("tủ lạnh", profile.get("conv_summary", ""))
        self.assertEqual(profile.get("conv_summary_len"), 6)
        summary_text = await get_memory_summary(ch, ext)
        self.assertIn("tóm_tắt=", summary_text)

    async def test_offline_and_disabled_skip(self):
        ch, ext = "web", "summary-2"
        with patch("app.agent.llm.has_llm_key", return_value=False):
            self.assertIsNone(await maybe_summarize_conversation(ch, ext, _history(20)))

        os.environ["MEMORY_SUMMARY_ENABLED"] = "false"
        get_settings.cache_clear()
        try:
            with patch("app.agent.llm.has_llm_key", return_value=True):
                self.assertIsNone(await maybe_summarize_conversation(ch, ext, _history(20)))
        finally:
            os.environ.pop("MEMORY_SUMMARY_ENABLED", None)
            get_settings.cache_clear()


if __name__ == "__main__":
    raise SystemExit(unittest.main())
