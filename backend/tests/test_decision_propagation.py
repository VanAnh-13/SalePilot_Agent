"""Decision contract propagation across offline / bag / stream paths."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.agent import consultation
from app.agent.offline import run_offline_multi_agent
from app.agent.run_bag import get_run_bag, reset_run_bag
from app.agent.tools.catalog import recommend_top3
from tests.catalog_fixture import installed_catalog_fixture


class DecisionPropagationTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog_fixture = installed_catalog_fixture()
        cls.catalog_fixture.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.catalog_fixture.__exit__(None, None, None)

    def test_consultation_packages_the_exact_ranked_result(self):
        need = {"category": "tu_lanh", "budget_vnd": 15_000_000}
        recommendation = {"ok": True, "top3": [{"sku": "one"}]}
        decision = {"schema_version": "test", "decision_hash": "hash"}
        with (
            patch.object(
                consultation,
                "recommend_top3",
                return_value=recommendation,
            ) as recommend,
            patch.object(
                consultation,
                "build_decision",
                return_value=decision,
            ) as package,
        ):
            result = consultation.consult(need)

        recommend.assert_called_once_with(result.need)
        package.assert_called_once_with(result.need, recommendation)
        self.assertIs(result.recommendation, recommendation)
        self.assertIs(result.decision, decision)
        self.assertIsNot(result.need, need)

    async def test_offline_recommend_includes_decision(self):
        with (
            patch("app.agent.offline.maybe_extract_from_text", new=AsyncMock()),
            patch("app.agent.offline.get_memory_summary", new=AsyncMock(return_value="")),
            patch("app.agent.offline.load_need", new=AsyncMock(return_value={})),
            patch("app.agent.offline.load_profile", new=AsyncMock(return_value={})),
            patch("app.agent.offline.save_need", new=AsyncMock()),
            patch.object(
                consultation,
                "recommend_top3",
                wraps=consultation.recommend_top3,
            ) as recommend,
        ):
            result = await run_offline_multi_agent(
                "tủ lạnh gia đình 4 người dưới 15 triệu",
                channel="web",
                external_id="decision-prop-offline",
            )
        self.assertEqual(recommend.call_count, 1)
        decision = result.get("decision")
        self.assertIsInstance(decision, dict)
        self.assertTrue(decision.get("schema_version"))
        self.assertTrue(decision.get("decision_hash"))

    async def test_catalog_tool_stores_decision_on_run_bag(self):
        reset_run_bag()
        raw = await recommend_top3.ainvoke(
            {
                "category": "tu_lanh",
                "household_size": 4,
                "budget_vnd": 15_000_000,
                "free_text": "tủ lạnh gia đình 4 người dưới 15 triệu",
            }
        )
        self.assertIn("decision", raw)
        bag = get_run_bag()
        self.assertIsInstance(bag.get("decision"), dict)
        self.assertEqual(bag["decision"].get("category") or bag["decision"].get("parsed_need", {}).get("category"), "tu_lanh")


if __name__ == "__main__":
    raise SystemExit(unittest.main())
