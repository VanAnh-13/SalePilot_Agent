"""Hermetic catalog cache fixture shared by decision tests."""

from __future__ import annotations

import hashlib
from contextlib import contextmanager

from app.catalog import repository


def _fixture_products() -> list[dict]:
    products = []
    for index, (price, capacity, width) in enumerate(
        ((8_000_000, 300, 58), (12_000_000, 400, 65), (14_000_000, 500, 70)),
        start=1,
    ):
        products.append(
            {
                "sku": f"fixture-fridge-{index}",
                "model_code": f"fixture-{index}",
                "category": "tu_lanh",
                "category_code": 1943,
                "category_display": "Tủ lạnh",
                "brand": f"Brand{index}",
                "name": f"Tủ lạnh Fixture {capacity} lít",
                "price_vnd": price,
                "price_original_vnd": price,
                "price_sale_vnd": price,
                "has_current_price": True,
                "rating": 4.0 + index / 10,
                "sold": index * 100,
                "source": "tests:inline_catalog",
                "source_row": index,
                "norm": {
                    "usable_capacity_l": capacity,
                    "width_cm": width,
                    "household_min": 2,
                    "household_max": 5,
                    "has_inverter": True,
                },
                "specs": {},
                "search_text": f"tủ lạnh fixture {capacity} inverter",
            }
        )
    return products


@contextmanager
def installed_catalog_fixture():
    previous = (
        repository._CACHE,  # noqa: SLF001
        repository._LOADED,  # noqa: SLF001
        repository._SOURCE,  # noqa: SLF001
        repository._DISTINCT_CATS,  # noqa: SLF001
        repository._CATALOG_HASH,  # noqa: SLF001
    )
    products = _fixture_products()
    repository._CACHE = products  # noqa: SLF001
    repository._LOADED = True  # noqa: SLF001
    repository._SOURCE = "snapshot"  # noqa: SLF001
    repository._DISTINCT_CATS = None  # noqa: SLF001
    digest_payload = repr(products).encode("utf-8")
    repository._CATALOG_HASH = hashlib.sha256(digest_payload).hexdigest()  # noqa: SLF001
    try:
        yield
    finally:
        (
            repository._CACHE,  # noqa: SLF001
            repository._LOADED,  # noqa: SLF001
            repository._SOURCE,  # noqa: SLF001
            repository._DISTINCT_CATS,  # noqa: SLF001
            repository._CATALOG_HASH,  # noqa: SLF001
        ) = previous
