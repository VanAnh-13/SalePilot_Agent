"""DMX crawl constraints remain hard in the production registry."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.agent import recommendation
from app.agent.catalog_domain import product_public, recommend_top3
from app.catalog import repository
from app.catalog.crawl_categories import BY_SLUG


def _recommend_with(product, cat, need):
    with (
        patch.object(recommendation, "get_category", return_value=cat),
        patch.object(repository, "by_category", return_value=[product]),
        patch.object(repository, "source", return_value="constraint-test"),
    ):
        return recommend_top3({"category": cat.slug, "force": True, **need})


class DmxConstraintTests(unittest.TestCase):
    def test_combined_dimension_cell_supplies_hard_width(self):
        cat = BY_SLUG["tu_lanh"]
        product = {
            "sku": "wide",
            "category": cat.slug,
            "category_code": cat.code,
            "price_vnd": 10_000_000,
            "has_current_price": True,
            "norm": {},
            "specs": {
                "Kích thước - Khối lượng": "Cao 180 cm - Ngang 64 cm - Sâu 70 cm"
            },
        }
        self.assertEqual(product_public(product)["width_cm"], 64)
        result = _recommend_with(
            product,
            cat,
            {"budget_vnd": 20_000_000, "max_width_cm": 60},
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["rejection_count"], 1)
        self.assertEqual(result["top3"], [])

    def test_air_conditioner_area_is_hard(self):
        cat = BY_SLUG["may_lanh"]
        product = {
            "sku": "small-room",
            "category": cat.slug,
            "category_code": cat.code,
            "price_vnd": 10_000_000,
            "has_current_price": True,
            "norm": {"area_min": 20, "area_max": 31},
            "specs": {},
        }
        result = _recommend_with(
            product,
            cat,
            {"budget_vnd": 20_000_000, "area_m2": 100},
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["rejection_count"], 1)
        self.assertEqual(result["top3"], [])


if __name__ == "__main__":
    raise SystemExit(unittest.main())
