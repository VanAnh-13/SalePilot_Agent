"""Catalog-facing copy follows the selected registry instead of fixed claims."""

from __future__ import annotations

import unittest

from app.agent.offline import _catalog_welcome
from app.agent.prompts import lead_system_prompt, subagent_prompt
from app.agent.recommendation import recommend_top3
from app.catalog.registry import CATEGORIES


STALE_CATALOG_CLAIMS = ("13.000", "13,000", "hơn 100")


class CatalogMessagingTests(unittest.TestCase):
    def assert_no_stale_claims(self, text: str) -> None:
        for claim in STALE_CATALOG_CLAIMS:
            self.assertNotIn(claim, text)

    def test_lead_prompt_lists_registry_categories_without_fixed_counts(self) -> None:
        prompt = lead_system_prompt()

        for category in CATEGORIES:
            self.assertIn(category.display, prompt)
        self.assert_no_stale_claims(prompt)

    def test_catalog_subagent_prompt_has_no_fixed_inventory_count(self) -> None:
        self.assert_no_stale_claims(subagent_prompt("catalog"))

    def test_missing_category_question_lists_current_registry(self) -> None:
        result = recommend_top3({})
        question = " ".join(result["ask"])

        for category in CATEGORIES:
            self.assertIn(category.display, question)
        self.assert_no_stale_claims(question)

    def test_offline_welcome_lists_current_registry(self) -> None:
        welcome = _catalog_welcome()

        for category in CATEGORIES:
            self.assertIn(category.display.lower(), welcome)
        self.assert_no_stale_claims(welcome)


if __name__ == "__main__":
    unittest.main()
