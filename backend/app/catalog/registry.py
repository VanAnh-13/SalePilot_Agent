"""Runtime-selectable category registry.

Production uses the DMX crawl taxonomy. Reproducible workbook experiments set
``SALEPILOT_CATALOG_REGISTRY=workbook`` before importing the agent domain.
Import scripts continue to use their concrete registry directly.
"""

from __future__ import annotations

import os

from app.catalog.category_model import CategoryRegistry

REGISTRY_NAME = os.getenv("SALEPILOT_CATALOG_REGISTRY", "crawl").strip().casefold()

if REGISTRY_NAME == "workbook":
    from app.catalog.categories import (
        BY_CODE,
        BY_SLUG,
        CATEGORIES,
        REGISTRY,
        Category,
        Priority,
        Slot,
        detect_category,
        detect_negated_categories,
        detect_unsupported,
        get_category,
    )
elif REGISTRY_NAME == "crawl":
    from app.catalog.crawl_categories import (
        BY_CODE,
        BY_SLUG,
        CATEGORIES,
        REGISTRY,
        Category,
        Priority,
        Slot,
        detect_category,
        detect_negated_categories,
        detect_unsupported,
        get_category,
    )
else:
    raise RuntimeError(
        "SALEPILOT_CATALOG_REGISTRY must be 'crawl' or 'workbook', "
        f"got {REGISTRY_NAME!r}"
    )

__all__ = [
    "REGISTRY_NAME",
    "BY_CODE",
    "BY_SLUG",
    "CATEGORIES",
    "REGISTRY",
    "Category",
    "CategoryRegistry",
    "Priority",
    "Slot",
    "detect_category",
    "detect_negated_categories",
    "detect_unsupported",
    "get_category",
]
