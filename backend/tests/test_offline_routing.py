"""Unit tests for the pure offline routing policy (no I/O)."""

from __future__ import annotations

import unittest

from app.agent.offline_routing import read_turn_signals
from app.catalog.registry import detect_category


def signals_for(text: str, *, stored: dict | None = None, extracted: dict | None = None):
    return read_turn_signals(
        text,
        stored_need=stored or {},
        extracted_need=extracted or {},
        merged_need={"category": (stored or {}).get("category")},
        detected=detect_category(text),
    )


class RoutingPolicyTests(unittest.TestCase):
    def test_plain_product_request_routes_to_catalog(self):
        s = signals_for("tủ lạnh cho gia đình 4 người dưới 15 triệu")
        self.assertTrue(s.need_product)
        self.assertFalse(s.need_faq)
        self.assertFalse(s.do_compare_now)

    def test_faq_and_stock_questions_do_not_route_to_catalog(self):
        s = signals_for("chính sách bảo hành thế nào")
        self.assertTrue(s.need_faq)
        s = signals_for("còn hàng không")
        self.assertTrue(s.stock_question)
        self.assertFalse(s.need_product)

    def test_phone_number_triggers_crm(self):
        s = signals_for("gọi lại giúp em số 0912345678 nhé")
        self.assertTrue(s.need_crm)
        self.assertEqual(s.phone, "0912345678")

    def test_escalation_keywords(self):
        s = signals_for("cho em gặp người tư vấn viên")
        self.assertTrue(s.need_escalate)

    def test_compare_with_two_skus_in_text_beats_recommend(self):
        s = signals_for("so sánh 358683 với 360309")
        self.assertTrue(s.compare_intent)
        self.assertTrue(s.do_compare_now)
        self.assertEqual(s.compare_skus[:2], ["358683", "360309"])
        self.assertFalse(s.need_product)

    def test_compare_without_skus_falls_back_to_last_recommendation(self):
        stored = {"category": "tu_lanh", "last_skus": ["111", "222", "333"]}
        s = signals_for("so sánh 2 mẫu vừa gợi ý", stored=stored)
        self.assertTrue(s.do_compare_now)
        self.assertEqual(s.compare_skus, ["111", "222", "333"])

    def test_unsupported_category_hits_guardrail(self):
        s = signals_for("tư vấn giúp em mua xe máy")
        self.assertIsNotNone(s.unsupported)
        self.assertFalse(s.need_product)

    def test_followup_slot_fills_need_without_category_named(self):
        stored = {"category": "may_tinh_de_ban"}
        extracted = {"ram_gb": 16}
        s = read_turn_signals(
            "RAM 16 GB",
            stored_need=stored,
            extracted_need=extracted,
            merged_need={"category": "may_tinh_de_ban"},
            detected=None,
        )
        self.assertTrue(s.need_product)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
