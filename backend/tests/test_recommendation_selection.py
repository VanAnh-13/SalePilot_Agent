"""Public recommendation contracts for ordering, diversity and exclusions."""

import unittest
from unittest.mock import patch

from app.agent import recommendation
from app.catalog.category_model import Category, Slot


CATEGORY = Category(code=999, slug="test", display="Test", sheet="", aliases=())


def product(sku, *, brand="A", price=10, model=None, rating=None, width=None):
    return {
        "sku": sku,
        "model_code": model or sku,
        "brand": brand,
        "name": sku,
        "price_vnd": price,
        "rating": rating,
        "norm": {"width_cm": width},
    }


def recommend(products, *, category=CATEGORY, **need):
    with (
        patch.object(recommendation, "get_category", return_value=category),
        patch.object(recommendation.repository, "by_category", return_value=products),
        patch.object(recommendation.repository, "source", return_value="test"),
        patch.object(recommendation, "compare", return_value={"tradeoffs": []}),
    ):
        return recommendation.recommend_top3({"category": category.slug, "budget_flexible": True, **need})


class RecommendationSelectionTests(unittest.TestCase):
    def assert_skus(self, result, expected):
        self.assertEqual([item["sku"] for item in result["top3"]], expected)

    def test_first_pass_prefers_brand_diversity(self):
        result = recommend([
            product("a1", price=10), product("a2", price=11),
            product("b1", brand="B", price=12), product("c1", brand="C", price=13),
        ])
        self.assert_skus(result, ["a1", "b1", "c1"])

    def test_fallback_fills_with_same_brand(self):
        result = recommend([product(f"a{i}", price=i) for i in range(1, 5)])
        self.assert_skus(result, ["a1", "a2", "a3"])

    def test_fallback_keeps_already_selected_order(self):
        result = recommend([
            product("a1", price=10), product("a2", price=11), product("b1", brand="B", price=12),
        ])
        self.assert_skus(result, ["a1", "b1", "a2"])

    def test_model_variants_are_deduplicated_across_both_passes(self):
        result = recommend([
            product("a-blue", price=10, model="same"),
            product("a-red", price=11, model="same"),
            product("b", brand="B", price=12), product("a-other", price=13),
        ])
        self.assert_skus(result, ["a-blue", "b", "a-other"])

    def test_score_precedes_price_and_ties_keep_input_order(self):
        result = recommend([
            product("cheaper", brand="A", price=10),
            product("first-high", brand="B", price=20, rating=5),
            product("second-high", brand="C", price=20, rating=5),
        ])
        self.assert_skus(result, ["first-high", "second-high", "cheaper"])
        self.assertEqual([item["match_score"] for item in result["top3"]], [0.6, 0.6, 0.0])

    def test_missing_price_is_not_a_candidate(self):
        result = recommend([product("missing", price=None), product("priced")])
        self.assert_skus(result, ["priced"])
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["rejection_count"], 0)

    def test_hard_limit_accepts_boundary_and_rejects_unknown_or_excess(self):
        category = Category(code=999, slug="test", display="Test", sheet="", aliases=(), slots=(
            Slot(key="max_width", label="width", kind="max_constraint", spec_key="width_cm", hardness="hard", missing_policy="exclude"),
        ))
        result = recommend([
            product("boundary", width=70), product("unknown"), product("wide", width=71),
        ], category=category, max_width=70)
        self.assert_skus(result, ["boundary"])
        self.assertEqual(result["candidate_count"], 3)
        self.assertEqual(result["rejection_count"], 2)
