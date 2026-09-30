"""Direct tool binding, delegate_many reachability, and order recovery."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

_TMP = tempfile.mkdtemp(prefix="salepilot_tools_direct_")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP}/tools_direct.db"
os.environ["TRAJECTORY_ENABLED"] = "false"

from app.agent import lead_tools  # noqa: E402
from app.agent.lead_tools import LEAD_TOOLS, delegate_many  # noqa: E402
from app.agent.run_bag import get_run_bag, reset_run_bag  # noqa: E402
from app.agent.tools.order import check_order_status, create_order_draft  # noqa: E402
from app.agent.tools.runtime import ToolContext, set_ctx  # noqa: E402
from app.db.session import init_db  # noqa: E402


def _bound_names() -> set[str]:
    return {t.name for t in LEAD_TOOLS}


class BoundToolsTests(unittest.TestCase):
    def test_every_advertised_tool_is_bound(self):
        """The prompt advertises these — every one must be callable."""
        bound = _bound_names()
        for name in (
            "delegate",
            "delegate_many",  # was defined-but-unbound (prompt lie) before
            "create_lead",
            "update_lead_status",
            "schedule_followup",
            "create_order_draft",
            "check_order_status",
            "escalate_to_human",
        ):
            self.assertIn(name, bound, name)


class DelegateManyTests(unittest.IsolatedAsyncioTestCase):
    async def test_delegate_many_runs_agents_in_parallel_and_caps(self):
        reset_run_bag()
        set_ctx(
            ToolContext(
                channel="web",
                external_id="delegate-many-1",
                conversation_id=None,
                lead_id=None,
                customer_name="T",
            )
        )

        async def fake_subagent(name, task, context=""):
            return {
                "agent": name,
                "task": task,
                "summary": f"done {name}",
                "tools_used": [],
                "ok": True,
            }

        with patch.object(lead_tools, "run_subagent", new=AsyncMock(side_effect=fake_subagent)):
            raw = await delegate_many.ainvoke(
                {"tasks_json": json.dumps(
                    [{"agent": "crm", "task": "a"}, {"agent": "order", "task": "b"}]
                )}
            )
        data = json.loads(raw)
        self.assertTrue(data["parallel"])
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual({r["agent"] for r in data["results"]}, {"crm", "order"})
        self.assertEqual(get_run_bag()["delegates"], 2)


class OrderRecoveryTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        import asyncio

        asyncio.run(init_db())

    async def asyncSetUp(self):
        reset_run_bag()
        set_ctx(
            ToolContext(
                channel="web",
                external_id="order-recovery-1",
                conversation_id=None,
                lead_id=None,
                customer_name="T",
            )
        )

    async def test_unpriced_sku_creates_flagged_draft_not_abort(self):
        products = {
            "PRICED": {"sku": "PRICED", "name": "Có giá", "price_vnd": 10_000_000, "source": "s"},
            "NOPRICE": {"sku": "NOPRICE", "name": "Chưa có giá", "price_vnd": None, "source": "s"},
        }
        with patch(
            "app.agent.tools.order.get_by_sku", side_effect=lambda sku: products.get(sku)
        ):
            raw = await create_order_draft.ainvoke(
                {"items_json": json.dumps([{"sku": "PRICED", "qty": 1}, {"sku": "NOPRICE", "qty": 2}])}
            )
        data = json.loads(raw)
        self.assertIn("order_draft_id", data)
        by_sku = {line["sku"]: line for line in data["items"]}
        self.assertEqual(by_sku["PRICED"]["needs_price"], False)
        self.assertTrue(by_sku["NOPRICE"]["needs_price"])
        self.assertIsNone(by_sku["NOPRICE"]["unit_price"])
        self.assertTrue(any("NOPRICE" in w for w in data["warnings"]))
        # Total only counts priced lines — never a fabricated price.
        self.assertEqual(data["total_vnd"], 10_000_000)

    async def test_check_order_status_finds_latest_draft_of_conversation(self):
        products = {"PRICED": {"sku": "PRICED", "name": "Có giá", "price_vnd": 5_000_000, "source": "s"}}
        with patch(
            "app.agent.tools.order.get_by_sku", side_effect=lambda sku: products.get(sku)
        ):
            created = json.loads(
                await create_order_draft.ainvoke({"items_json": json.dumps([{"sku": "PRICED", "qty": 1}])})
            )
        raw = await check_order_status.ainvoke({"order_draft_id": created["order_draft_id"]})
        data = json.loads(raw)
        self.assertTrue(data["found"])
        self.assertEqual(data["orders"][0]["order_draft_id"], created["order_draft_id"])
        self.assertEqual(data["orders"][0]["status"], "draft")


if __name__ == "__main__":
    raise SystemExit(unittest.main())
