"""Serving routes preserve memory ordering, short-circuits and failure behavior."""

from contextlib import ExitStack
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.errors import GraphRecursionError

from app.agent import graph


class ServingSetupTests(unittest.IsolatedAsyncioTestCase):
    async def test_memory_precedes_routing_for_both_transports(self):
        for streaming in (False, True):
            for route in ("offline", "fast_path", None):
                with self.subTest(streaming=streaming, route=route), ExitStack() as stack:
                    calls = []
                    before = {"phone": "old"}
                    result = {"reply": "Xin chào", "trace": [], "used_agents": ["lead"], "used_tools": [], "needs_human": False, "lead_id": None, "conversation_id": None}

                    async def profile(*args):
                        calls.append("profile")
                        return before

                    async def summary(*args):
                        calls.append("summary")
                        return "saved memory"

                    async def extract(*args):
                        calls.append("extract")

                    async def early(*args, **kwargs):
                        calls.append("route")
                        self.assertIs(kwargs["memory_before"], before)
                        self.assertEqual(kwargs["memory_summary"], "saved memory")
                        return (result, route) if route else None

                    def prepare(*args, **kwargs):
                        calls.append("graph")
                        self.assertEqual(kwargs["history"], [{"role": "user", "content": "prior"}])
                        return {"messages": []}

                    async def tokens(state):
                        yield "Xin chào"

                    for name, replacement in (
                        ("load_profile", profile), ("get_memory_summary", summary),
                        ("maybe_extract_from_text", extract), ("_serve_early_routes", early),
                        ("_prepare_llm_graph", prepare), ("_stream_graph_tokens", tokens),
                    ):
                        stack.enter_context(patch.object(graph, name, replacement))
                    model = SimpleNamespace(ainvoke=AsyncMock())
                    stack.enter_context(patch.object(graph, "get_graph", return_value=model))
                    finalize = stack.enter_context(patch.object(graph, "_finalize_llm_run", new=AsyncMock(return_value=result)))
                    record = stack.enter_context(patch.object(graph, "record_run"))
                    kwargs = dict(channel="web", external_id="test", history=[{"role": "user", "content": "prior"}])
                    if streaming:
                        events = [event async for event in graph.run_agent_stream("hello", **kwargs)]
                        self.assertEqual(events[-1]["type"], "done")
                        self.assertEqual(events[-1]["reply"], result["reply"])
                        if route is None:
                            self.assertEqual(events[0], {"type": "memory", "summary": "saved memory"})
                    else:
                        self.assertEqual((await graph.run_agent("hello", **kwargs))["reply"], result["reply"])
                    self.assertEqual(calls, ["profile", "summary", "extract", "route"] + ([] if route else ["graph"]))
                    if route:
                        finalize.assert_not_awaited()
                        model.ainvoke.assert_not_awaited()
                        self.assertEqual(record.call_args.args[0], route)
                    else:
                        self.assertIs(finalize.call_args.kwargs["memory_before"], before)
                        self.assertIsNone(finalize.call_args.kwargs["llm_error"])

    async def test_graph_errors_reach_shared_fallback_for_both_transports(self):
        for streaming in (False, True):
            for error in (RuntimeError("provider unavailable"), GraphRecursionError("limit")):
                with self.subTest(streaming=streaming, error=type(error)), ExitStack() as stack:
                    stack.enter_context(patch.object(graph, "_prelude", new=AsyncMock(return_value=({}, ""))))
                    stack.enter_context(patch.object(graph, "_serve_early_routes", new=AsyncMock(return_value=None)))
                    stack.enter_context(patch.object(graph, "_prepare_llm_graph", return_value={}))
                    stack.enter_context(patch.object(graph, "get_graph", return_value=SimpleNamespace(ainvoke=AsyncMock(side_effect=error))))

                    async def fail_stream(state):
                        yield "partial"
                        raise error

                    stack.enter_context(patch.object(graph, "_stream_graph_tokens", fail_stream))
                    final = stack.enter_context(patch.object(graph, "_finalize_llm_run", new=AsyncMock(return_value={"reply": "fallback", "trace": [], "used_tools": [], "used_agents": ["lead"], "needs_human": False, "lead_id": None, "conversation_id": None})))
                    if streaming:
                        events = [event async for event in graph.run_agent_stream("hello")]
                        self.assertEqual(events[0], {"type": "token", "content": "partial"})
                        self.assertEqual(events[-1]["reply"], "fallback")
                    else:
                        self.assertEqual((await graph.run_agent("hello"))["reply"], "fallback")
                    self.assertIs(final.call_args.kwargs["llm_error"], error)


class ContextMessageTests(unittest.TestCase):
    def test_replaces_first_human_marker_in_place(self):
        system = SystemMessage(content="[Active skills] system")
        other = HumanMessage(content="question")
        duplicate = HumanMessage(content="[Active skills] duplicate")
        messages = [system, other, HumanMessage(content="[Active skills] old"), duplicate]
        graph._replace_context_message(messages, "[Active skills]", "[Active skills] new")
        self.assertEqual(len(messages), 4)
        self.assertIs(messages[0], system)
        self.assertIs(messages[1], other)
        self.assertEqual(messages[2].content, "[Active skills] new")
        self.assertIs(messages[3], duplicate)

    def test_appends_when_no_human_marker_exists(self):
        messages = [SystemMessage(content="[Sub-agent results] system")]
        graph._replace_context_message(messages, "[Sub-agent results]", "[Sub-agent results] new")
        self.assertEqual(len(messages), 2)
        self.assertIsInstance(messages[-1], HumanMessage)
