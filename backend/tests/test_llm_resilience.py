"""LLM resilience: configurable retries + sub-agent error isolation."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("TRAJECTORY_ENABLED", "false")

from langchain_core.language_models.chat_models import BaseChatModel  # noqa: E402
from langchain_core.messages import AIMessage  # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatResult  # noqa: E402

from app.agent.llm import get_chat_model  # noqa: E402
from app.agent.subagents.base import run_subagent  # noqa: E402
from app.agent.run_bag import reset_run_bag
from app.agent.tools.runtime import ToolContext, set_ctx  # noqa: E402


class _ExplodingModel(BaseChatModel):
    """Simulates a provider that dies on every call."""

    @property
    def _llm_type(self) -> str:
        return "exploding"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        raise RuntimeError("provider exploded")

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        raise RuntimeError("provider exploded")


class _OkModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "ok"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="đã xong"))])


class RetryConfigTests(unittest.TestCase):
    def test_retry_count_comes_from_settings(self):
        from app.config import get_settings as _cached

        # get_settings is lru_cache'd; clear it so the patched env is read.
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key", "LLM_MAX_RETRIES": "3"}):
            _cached.cache_clear()
            model = get_chat_model()
            self.assertEqual(getattr(model, "max_retries", None), 3)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key", "LLM_MAX_RETRIES": "0"}):
            _cached.cache_clear()
            model = get_chat_model()
            self.assertEqual(getattr(model, "max_retries", None), 0)
        _cached.cache_clear()


class SubagentIsolationTests(unittest.IsolatedAsyncioTestCase):
    async def test_subagent_llm_failure_returns_error_result_not_raise(self):
        reset_run_bag()
        set_ctx(
            ToolContext(
                channel="web",
                external_id="llm-resilience-1",
                conversation_id=None,
                lead_id=None,
                customer_name="T",
            )
        )
        with patch("app.agent.subagents.base.get_chat_model", return_value=_ExplodingModel()):
            result = await run_subagent("crm", "ghi lead giúp em")
        self.assertFalse(result["ok"])
        self.assertIn("lỗi LLM", result["summary"])

    async def test_subagent_ok_path_unchanged(self):
        reset_run_bag()
        set_ctx(
            ToolContext(
                channel="web",
                external_id="llm-resilience-2",
                conversation_id=None,
                lead_id=None,
                customer_name="T",
            )
        )
        with patch("app.agent.subagents.base.get_chat_model", return_value=_OkModel()):
            result = await run_subagent("crm", "ghi lead giúp em")
        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"], "đã xong")


if __name__ == "__main__":
    raise SystemExit(unittest.main())
