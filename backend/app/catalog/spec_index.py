"""Reverse index: spec attribute key → set of category codes.

Built dynamically from the loaded catalog so that every ``spec_product``
key that appears in any product is queryable without any hardcoded list.
The index is rebuilt whenever the catalog reloads.

Design:
  - SpecIndex has one responsibility: map spec keys → category codes.
  - It is constructed from data (DI-friendly); nothing is hardcoded.
  - save() / load() let callers persist the index as JSON alongside the
    catalog snapshot so the offline path works without a live catalog.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


class SpecIndex:
    """Reverse index: spec attribute key → frozenset of category codes."""

    def __init__(self, data: dict[str, set[int]] | None = None) -> None:
        self._index: dict[str, set[int]] = defaultdict(set)
        if data:
            for key, codes in data.items():
                self._index[key] = set(codes)

    # ------------------------------------------------------------------ #
    # Construction                                                          #
    # ------------------------------------------------------------------ #

    @classmethod
    def build(cls, products: list[dict[str, Any]]) -> "SpecIndex":
        """Build from a list of normalized catalog documents.

        Each document must have ``category_code`` (int) and optionally
        ``specs`` (dict of raw Vietnamese spec keys) or ``norm`` (dict of
        normalized spec keys).  Both are indexed.
        """
        instance = cls()
        for product in products:
            code = int(product.get("category_code") or 0)
            if not code:
                continue
            for key in (product.get("specs") or {}):
                instance._index[str(key)].add(code)
            for key in (product.get("norm") or {}):
                instance._index[str(key)].add(code)
        return instance

    # ------------------------------------------------------------------ #
    # Query                                                                 #
    # ------------------------------------------------------------------ #

    def categories_for_spec(self, spec_key: str) -> frozenset[int]:
        """Return category codes that carry the given spec attribute."""
        return frozenset(self._index.get(spec_key, set()))

    def specs_for_category(self, category_code: int) -> frozenset[str]:
        """Return all spec keys present in a given category."""
        return frozenset(key for key, codes in self._index.items() if category_code in codes)

    def all_spec_keys(self) -> frozenset[str]:
        """Full set of known spec attribute keys across all categories."""
        return frozenset(self._index)

    def __len__(self) -> int:
        return len(self._index)

    def summary(self) -> dict[str, Any]:
        """Human-readable summary for logging / health endpoints."""
        return {
            "total_spec_keys": len(self._index),
            "top_shared_keys": sorted(
                self._index.items(),
                key=lambda kv: -len(kv[1]),
            )[:10],
        }

    # ------------------------------------------------------------------ #
    # Persistence                                                           #
    # ------------------------------------------------------------------ #

    def save(self, path: Path) -> None:
        """Persist the index as JSON (lists, not sets, for JSON compat)."""
        serialisable = {key: sorted(codes) for key, codes in self._index.items()}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(serialisable, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "SpecIndex":
        """Restore from a previously saved JSON file.

        Returns an empty index if the file does not exist (offline-safe).
        """
        if not path.exists():
            return cls()
        raw: dict[str, list[int]] = json.loads(path.read_text(encoding="utf-8"))
        return cls({key: set(codes) for key, codes in raw.items()})
