"""Retail memory fields: address, purchase history, marketing consent."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

_TMP = tempfile.mkdtemp(prefix="salepilot_memory_retail_")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP}/memory_retail.db"
os.environ["TRAJECTORY_ENABLED"] = "false"

from app.agent.memory.store import (  # noqa: E402
    DEFAULT_PROFILE,
    get_memory_summary,
    load_profile,
    merge_profile,
)
from app.agent.memory.tools import remember_customer  # noqa: E402
from app.agent.tools.runtime import ToolContext, set_ctx  # noqa: E402
from app.db.session import init_db  # noqa: E402


class RetailMemoryTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        import asyncio

        asyncio.run(init_db())

    async def test_defaults_are_safe_and_present(self):
        self.assertEqual(DEFAULT_PROFILE["address"], "")
        self.assertEqual(DEFAULT_PROFILE["purchase_history"], [])
        self.assertIs(DEFAULT_PROFILE["marketing_consent"], False)

    async def test_fields_persist_with_caps_and_summary(self):
        ch, ext = "web", "retail-1"
        await merge_profile(ch, ext, address="Số 12 Ngô Quyền, Hà Nội", purchase_sku="SKU-1")
        # Same SKU twice in a row → single history entry (dedupe like notes).
        await merge_profile(ch, ext, purchase_sku="SKU-1")
        await merge_profile(ch, ext, purchase_sku="SKU-2", marketing_consent=True)
        profile = await load_profile(ch, ext)
        self.assertEqual(profile["address"], "Số 12 Ngô Quyền, Hà Nội")
        self.assertEqual([e["sku"] for e in profile["purchase_history"]], ["SKU-1", "SKU-2"])
        self.assertTrue(profile["marketing_consent"])
        summary = await get_memory_summary(ch, ext)
        self.assertIn("địa_chỉ=", summary)
        self.assertIn("đã_mua=2", summary)
        self.assertIn("đồng_ý_marketing=có", summary)

    async def test_consent_defaults_false_and_tool_roundtrip(self):
        ch, ext = "web", "retail-2"
        set_ctx(
            ToolContext(
                channel=ch, external_id=ext, conversation_id=None, lead_id=None, customer_name="T"
            )
        )
        raw = await remember_customer.ainvoke(
            {"phone": "0912345678", "address": "25 Lý Thường Kiệt"}
        )
        data = json.loads(raw)
        self.assertTrue(data["ok"])
        self.assertIs(data["profile"]["marketing_consent"], False)  # never assumed
        raw2 = await remember_customer.ainvoke({"purchased_sku": "SKU-9", "marketing_consent": True})
        data2 = json.loads(raw2)
        self.assertTrue(data2["profile"]["marketing_consent"])
        self.assertEqual(data2["profile"]["purchase_history"][-1]["sku"], "SKU-9")


if __name__ == "__main__":
    raise SystemExit(unittest.main())
