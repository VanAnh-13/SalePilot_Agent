from __future__ import annotations

import unittest
from copy import deepcopy

from app.agent.catalog_domain import extract_need_from_text, recommend_top3
from app.agent.decision import DECISION_SCHEMA_VERSION, build_decision
from app.catalog import repository
from tests.catalog_fixture import installed_catalog_fixture


class DecisionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog_fixture = installed_catalog_fixture()
        cls.catalog_fixture.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.catalog_fixture.__exit__(None, None, None)

    def test_complete_need_has_provenance(self):
        need = extract_need_from_text("tủ lạnh gia đình 4 người dưới 15 triệu tiết kiệm điện")
        rec, decision = recommend_top3(need), build_decision(need)
        self.assertEqual(decision["schema_version"], DECISION_SCHEMA_VERSION)
        self.assertTrue(decision.get("decision_hash"))
        if rec.get("ok"):
            self.assertTrue(decision["top3"])
            item = decision["top3"][0]
            self.assertIn("provenance", item)
            self.assertIn("constraints", item)
            self.assertIn("score_components", item)
            # Evidence fields must survive packaging so evaluators can re-check
            # hard constraints against catalog facts, not model-authored status.
            self.assertTrue(
                any(key in item for key in ("width_cm", "usable_capacity_l", "household_min", "price_vnd"))
            )
            self.assertIsNotNone(item.get("source_row"))

    def test_impossible_budget_no_fabricated_top3(self):
        need = extract_need_from_text("tủ lạnh gia đình 4 người dưới 500 nghìn")
        decision = build_decision(need)
        self.assertFalse(decision.get("ok") and decision.get("top3"))
        # Fail-closed evidence: every priced candidate was evaluated and rejected.
        self.assertIsInstance(decision["candidate_count"], int)
        self.assertGreater(decision["candidate_count"], 0)
        self.assertEqual(decision["rejection_count"], decision["candidate_count"])

    def test_missing_slot_clarify(self):
        need = extract_need_from_text("cần máy lạnh tầm 12 triệu")
        decision = build_decision(need)
        self.assertTrue(decision.get("need_more") or decision.get("missing_slots"))
        # No candidate set was evaluated, so no counts are claimed.
        self.assertIsNone(decision["candidate_count"])
        self.assertIsNone(decision["rejection_count"])

    def test_evidence_counts_cover_selected_candidates(self):
        need = extract_need_from_text("tủ lạnh gia đình 4 người dưới 15 triệu")
        rec = recommend_top3(need)
        decision = build_decision(need, rec)
        if rec.get("ok"):
            self.assertIsInstance(decision["candidate_count"], int)
            self.assertIsInstance(decision["rejection_count"], int)
            self.assertGreaterEqual(decision["rejection_count"], 0)
            self.assertGreaterEqual(
                decision["candidate_count"] - decision["rejection_count"],
                len(decision["top3"]),
            )

    def test_hash_is_stable_for_operational_memory_but_changes_with_evidence(self):
        need = extract_need_from_text("tủ lạnh gia đình 4 người dưới 15 triệu")
        first = build_decision(need)
        operational = dict(need, raw="different wording", last_skus=["temporary"])
        second = build_decision(operational)
        self.assertEqual(first["decision_hash"], second["decision_hash"])

        rec = recommend_top3(need)
        changed = deepcopy(rec)
        if changed.get("top3"):
            changed["top3"][0]["source_row"] = 999999
            changed["top3"][0]["width_cm"] = 999
            third = build_decision(need, changed)
            self.assertNotEqual(first["decision_hash"], third["decision_hash"])

    def test_hash_is_stable_across_catalog_transport_backend(self):
        need = extract_need_from_text("tủ lạnh gia đình 4 người dưới 15 triệu")
        first = build_decision(need)
        old_source = repository._SOURCE  # noqa: SLF001
        try:
            repository._SOURCE = "postgres"  # noqa: SLF001
            second = build_decision(need)
        finally:
            repository._SOURCE = old_source  # noqa: SLF001
        self.assertEqual(first["source"]["catalog_hash"], second["source"]["catalog_hash"])
        self.assertEqual(first["decision_hash"], second["decision_hash"])

    def test_catalog_digest_ignores_transport_source_and_normalizes_nulls(self):
        base = {
            "sku": "one",
            "category": "tu_lanh",
            "category_code": 1943,
            "price_vnd": 10,
            "norm": {"width_cm": 60},
            "source": "products_detail.json",
        }
        mirror = dict(base, source="postgres", source_row=None)
        self.assertEqual(repository._docs_digest([base]), repository._docs_digest([mirror]))  # noqa: SLF001
        changed = dict(base, source_row=12)
        self.assertNotEqual(repository._docs_digest([base]), repository._docs_digest([changed]))  # noqa: SLF001


if __name__ == "__main__":
    raise SystemExit(unittest.main())
