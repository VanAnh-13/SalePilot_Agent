"""Resource-lifecycle tests for catalog repository adapters."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.catalog import repository


class _PingFailureClient:
    def __init__(self) -> None:
        self.admin = self
        self.closed = False

    def command(self, _name: str) -> None:
        raise RuntimeError("mongo unavailable")

    def close(self) -> None:
        self.closed = True


class _QueryFailureClient:
    def __init__(self) -> None:
        self.closed = False

    def __getitem__(self, _name: str) -> _QueryFailureClient:
        return self

    def find(self, *_args: object, **_kwargs: object) -> object:
        raise RuntimeError("query failed")

    def close(self) -> None:
        self.closed = True


class CatalogRepositoryResourceTests(unittest.TestCase):
    def test_mongo_client_closes_when_ping_fails(self) -> None:
        client = _PingFailureClient()

        with patch("pymongo.MongoClient", return_value=client):
            with self.assertRaisesRegex(RuntimeError, "mongo unavailable"):
                repository.mongo_client()

        self.assertTrue(client.closed)

    def test_mongo_loader_closes_when_query_fails(self) -> None:
        client = _QueryFailureClient()
        settings = SimpleNamespace(
            mongodb_db="salepilot",
            mongodb_products_collection="products",
        )

        with (
            patch.object(repository, "get_settings", return_value=settings),
            patch.object(repository, "mongo_client", return_value=client),
        ):
            self.assertIsNone(repository._load_from_mongo())

        self.assertTrue(client.closed)


if __name__ == "__main__":
    unittest.main()
