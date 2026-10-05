"""RAG metadata: boosts active on both KB sources + policy-filtered retrieval."""

from __future__ import annotations

import json
import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import app.rag.store as store  # noqa: E402
from app.agent.tools.knowledge import detect_policy_type, search_knowledge  # noqa: E402
from scripts.import_policies import POLICY_DOCS  # noqa: E402

_FAKE_KB = [
    {
        "id": "bao_hanh_doi_tra-01",
        "question": "Chính sách bảo hành & đổi trả — điều kiện",
        "answer": "Bảo hành 12 tháng cho hầu hết sản phẩm, đổi trả trong 7 ngày.",
        "topic": "bao_hanh_doi_tra",
        "source": "policies/x.md",
        "policy_type": ["bao_hanh", "doi_tra"],
        "product_groups": [],
    },
    {
        "id": "giao_hang_lap_dat-01",
        "question": "Chính sách giao hàng & lắp đặt — khu vực",
        "answer": "Giao hàng nội thành trong 1–3 ngày, miễn phí lắp đặt.",
        "topic": "giao_hang_lap_dat",
        "source": "policies/y.md",
        "policy_type": ["giao_hang", "lap_dat"],
        "product_groups": [],
    },
]


class RagMetadataTests(unittest.TestCase):
    def setUp(self):
        store._faq_cache = [dict(c) for c in _FAKE_KB]

    def tearDown(self):
        store.reload_kb()

    def test_policy_type_reconstruction_covers_all_known_topics(self):
        # Single source: the importer's POLICY_DOCS defines the topic universe.
        known_topics = {topic for _, topic in POLICY_DOCS.values()}
        self.assertEqual(known_topics, set(store._TOPIC_POLICY_TYPES))

    def test_boosts_derive_from_policy_signals_single_source(self):
        # Every POLICY_SIGNALS domain must be boosted — no keyword list drift.
        boost_signals = [tuple(signals) for field, signals, _ in store._METADATA_BOOSTS if field == "policy_type"]
        for signals in store.POLICY_SIGNALS.values():
            self.assertIn(tuple(signals), boost_signals)

    def test_boost_reorders_warranty_query_toward_warranty_chunk(self):
        # Same lexical signal ("chính sách") but the metadata boost must rank
        # the matching-domain chunk first.
        import asyncio

        hits = asyncio.run(store.search_policy("chính sách"))
        self.assertEqual(hits[0]["id"], _FAKE_KB[0]["id"])

    def test_policy_filter_excludes_other_domain(self):
        import asyncio

        hits = asyncio.run(store.search_policy("chính sách", policy_type="giao_hang"))
        self.assertTrue(hits)
        self.assertTrue(all("giao_hang" in h["id"] or h["id"].startswith("giao") for h in hits))

    def test_detect_policy_type_from_query(self):
        self.assertEqual(detect_policy_type("bảo hành bao lâu"), "bao_hanh")
        self.assertEqual(detect_policy_type("thay doi tra nhu the nao"), "doi_tra")
        self.assertEqual(detect_policy_type("ship nội thành không"), "giao_hang")
        self.assertIsNone(detect_policy_type("cửa hàng mở cửa mấy giờ"))

    def test_knowledge_tool_uses_filtered_retrieval(self):
        import asyncio

        raw = asyncio.run(search_knowledge.ainvoke({"query": "bảo hành thế nào"}))
        data = json.loads(raw)
        self.assertTrue(data["results"])
        self.assertTrue(
            all("bao_hanh" in h["id"] or "bảo hành" in h["question"].lower() for h in data["results"])
        )


if __name__ == "__main__":
    raise SystemExit(unittest.main())
