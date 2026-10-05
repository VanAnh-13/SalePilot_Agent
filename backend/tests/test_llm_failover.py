"""Cross-provider failover: primary hard failure falls to the secondary."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from langchain_core.language_models.chat_models import BaseChatModel  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatResult  # noqa: E402

from app.agent.llm import _FailoverModel, get_chat_model  # noqa: E402


class _CountingModel(BaseChatModel):
    """Returns a fixed text and counts calls; optionally always fails."""

    text: str = "ok"
    fail: bool = False
    calls: int = 0

    @property
    def _llm_type(self) -> str:
        return "counting"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        object.__setattr__(self, "calls", self.calls + 1)
        if self.fail:
            raise RuntimeError("boom")
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self.text))])


class FailoverModelTests(unittest.IsolatedAsyncioTestCase):
    async def test_primary_failure_falls_back_to_secondary(self):
        primary = _CountingModel(fail=True)
        secondary = _CountingModel(text="từ secondary")
        model = _FailoverModel(primary=primary, secondary=secondary)
        ai = await model.ainvoke([HumanMessage(content="hi")])
        self.assertEqual(ai.content, "từ secondary")
        self.assertEqual(primary.calls, 1)
        self.assertEqual(secondary.calls, 1)

    async def test_healthy_primary_never_touches_secondary(self):
        primary = _CountingModel(text="từ primary")
        secondary = _CountingModel(text="không được dùng")
        model = _FailoverModel(primary=primary, secondary=secondary)
        ai = await model.ainvoke([HumanMessage(content="hi")])
        self.assertEqual(ai.content, "từ primary")
        self.assertEqual(secondary.calls, 0)

    def test_bind_tools_passes_through_both_providers(self):
        primary = _CountingModel(text="p")
        secondary = _CountingModel(text="s")
        model = _FailoverModel(primary=primary, secondary=secondary)
        bound = model.bind_tools([{"name": "t"}])
        self.assertIsInstance(bound, _FailoverModel)
        self.assertIs(bound.primary, primary)
        self.assertIs(bound.secondary, secondary)


class GetChatModelFailoverTests(unittest.TestCase):
    def test_both_keys_wrap_in_failover(self):
        from app.config import get_settings

        env = {
            "OPENAI_API_KEY": "k1",
            "ANTHROPIC_API_KEY": "k2",
            "LLM_MAX_RETRIES": "0",
        }
        with patch.dict(os.environ, env):
            get_settings.cache_clear()
            model = get_chat_model()
            get_settings.cache_clear()
        self.assertIsInstance(model, _FailoverModel)

    def test_single_key_returns_plain_model(self):
        from app.config import get_settings

        with patch.dict(os.environ, {"OPENAI_API_KEY": "k1", "ANTHROPIC_API_KEY": ""}):
            get_settings.cache_clear()
            model = get_chat_model()
            get_settings.cache_clear()
        self.assertNotIsInstance(model, _FailoverModel)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
