"""Vietnamese text normalizer — public facade for the NLP package.

Combines AbbreviationRegistry and EntityExtractor into a single entry
point for callers that need both expansion and entity detection.

Design (Facade / DIP):
  - ViNormalizer depends on abstractions (the two SRP classes), not
    on concrete pattern logic.
  - Dependencies are injected so callers can substitute mock objects in tests.
  - normalize() is a pure function: same input → same output, no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.nlp.abbreviations import AbbreviationRegistry
from app.nlp.entity_extractor import EntityExtractor, ExtractedEntities


@dataclass
class NormalizedText:
    original: str
    expanded: str
    entities: ExtractedEntities

    def to_dict(self) -> dict[str, Any]:
        return {
            "original": self.original,
            "expanded": self.expanded,
            "entities": self.entities.to_dict(),
        }


class ViNormalizer:
    """Facade: Vietnamese text normalization for the SalePilot agent.

    Usage::

        normalizer = ViNormalizer()
        result = normalizer.normalize("máy giặt dc ko, giá 3990k")
        # result.expanded == "máy giặt được không, giá 3990k"
        # result.entities.prices_raw == ["3990k"]
    """

    def __init__(
        self,
        abbreviations: AbbreviationRegistry | None = None,
        extractor: EntityExtractor | None = None,
    ) -> None:
        self._abbreviations = abbreviations or AbbreviationRegistry()
        self._extractor = extractor or EntityExtractor()

    def normalize(self, text: str) -> NormalizedText:
        """Expand abbreviations and extract entities from Vietnamese text."""
        expanded = self._abbreviations.expand(text)
        entities = self._extractor.extract(text)  # extract from original (more robust)
        return NormalizedText(original=text, expanded=expanded, entities=entities)

    def expand(self, text: str) -> str:
        """Expand abbreviations only (no entity extraction)."""
        return self._abbreviations.expand(text)
