"""Public contract tests for concrete catalog category registries."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.catalog import categories, crawl_categories, registry
from app.catalog.category_model import CategoryRegistry


class CategoryRegistryContractTests(unittest.TestCase):
    def test_runtime_selector_exposes_the_stable_registry(self):
        self.assertIsInstance(registry.REGISTRY, CategoryRegistry)
        self.assertIs(registry.get_category("tu_lanh"), registry.REGISTRY.get_category("tu_lanh"))

    def test_concrete_modules_expose_the_shared_registry_interface(self):
        for module in (categories, crawl_categories):
            with self.subTest(module=module.__name__):
                self.assertIsInstance(module.REGISTRY, CategoryRegistry)

                fridge = module.REGISTRY.get_category("tu_lanh")
                self.assertIsNotNone(fridge)
                self.assertEqual(fridge.slug, "tu_lanh")
                self.assertIs(module.REGISTRY.get_category(fridge.code), fridge)
                self.assertIs(module.get_category("tu_lanh"), fridge)

    def test_detection_negation_and_unsupported_guardrails_are_preserved(self):
        with patch("app.catalog.repository.distinct_categories", return_value=[]):
            for module in (categories, crawl_categories):
                with self.subTest(module=module.__name__):
                    detected = module.REGISTRY.detect_category(
                        "Không phải tủ lạnh, tôi cần máy giặt cho gia đình"
                    )
                    self.assertIsNotNone(detected)
                    self.assertEqual(detected.slug, "may_giat")
                    self.assertIn(
                        "tu_lanh",
                        module.REGISTRY.detect_negated_categories(
                            "Không phải tủ lạnh, tôi cần máy giặt"
                        ),
                    )
                    self.assertEqual(
                        module.REGISTRY.detect_unsupported("Tôi cần mua ô tô"),
                        ("ô tô", ""),
                    )

    def test_generic_category_factory_has_one_shared_behavior(self):
        workbook_generic = categories.make_generic(999, "Thiết bị Nhà bếp")
        crawl_generic = crawl_categories.make_generic(999, "Thiết bị Nhà bếp")

        self.assertEqual(workbook_generic, crawl_generic)
        self.assertEqual(workbook_generic.slug, "thiet_bi_nha_bep")
        self.assertTrue(workbook_generic.generic)


if __name__ == "__main__":
    unittest.main()
