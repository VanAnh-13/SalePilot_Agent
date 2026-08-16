"""Vietnamese NLP package for SalePilot.

Public API::

    from app.nlp import ViNormalizer, AbbreviationRegistry, EntityExtractor

    normalizer = ViNormalizer()
    result = normalizer.normalize("máy giặt dc ko, giá 3990k")
"""

from app.nlp.abbreviations import AbbreviationRegistry
from app.nlp.entity_extractor import EntityExtractor, ExtractedEntities
from app.nlp.vi_normalizer import NormalizedText, ViNormalizer

__all__ = [
    "AbbreviationRegistry",
    "EntityExtractor",
    "ExtractedEntities",
    "NormalizedText",
    "ViNormalizer",
]
