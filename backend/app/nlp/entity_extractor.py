"""Vietnamese entity extractor for SalePilot NLP.

Extracts typed entities from user messages without mutating the text.

Design (SRP):
  - EntityExtractor has one responsibility: detect + locate entities.
  - Each entity type is a separate method so callers can request only what
    they need (ISP).
  - Patterns are declared as module-level compiled constants (no hidden state).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Compiled patterns — declared once at module level
# ---------------------------------------------------------------------------

# Vietnamese mobile: 03x, 05x, 07x, 08x, 09x — 10 digits
_PHONE_RE = re.compile(r"\b(0[35789]\d{8})\b")

# Product / SKU codes: 5–8 digit sequences not preceded by a price unit
_SKU_RE = re.compile(r"(?<!\d)(\d{5,8})(?!\d)")

# Price with unit: "15 triệu", "3990k", "800 nghìn", "1,500,000 đ"
_PRICE_RE = re.compile(
    r"(\d[\d.,]*)(?:\s*(?:triệu|trieu|tr|triệu đồng|trieu dong|k|nghìn|nghin|ngàn|ngan"
    r"|đồng|dong|đ|vnđ|vnd)\b)",
    re.IGNORECASE,
)

# Vietnamese administrative units (province/district/ward)
_ADDRESS_RE = re.compile(
    r"\b(?:tỉnh|tp\.|thành phố|quận|huyện|phường|xã|thị trấn)\s+[A-Za-zÀ-ỹ\s]+",
    re.IGNORECASE,
)


@dataclass
class ExtractedEntities:
    phones: list[str] = field(default_factory=list)
    skus: list[str] = field(default_factory=list)
    prices_raw: list[str] = field(default_factory=list)
    address_fragments: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phones": self.phones,
            "skus": self.skus,
            "prices_raw": self.prices_raw,
            "address_fragments": self.address_fragments,
        }

    @property
    def has_any(self) -> bool:
        return any([self.phones, self.skus, self.prices_raw, self.address_fragments])


class EntityExtractor:
    """Extract typed entities from Vietnamese text (SRP: extraction only).

    Does not normalize, does not anonymize — those are separate concerns.
    """

    def extract(self, text: str) -> ExtractedEntities:
        return ExtractedEntities(
            phones=self.extract_phones(text),
            skus=self.extract_skus(text),
            prices_raw=self.extract_prices(text),
            address_fragments=self.extract_address_fragments(text),
        )

    def extract_phones(self, text: str) -> list[str]:
        return _PHONE_RE.findall(text)

    def extract_skus(self, text: str) -> list[str]:
        # Exclude numbers that are part of a detected phone or price. Bare ≥7-digit
        # numbers are prices (millions+), not catalog SKUs (≤6 digits or dash-coded).
        phone_digits = {m for m in _PHONE_RE.findall(text)}
        price_digits = {m.strip().replace(".", "").replace(",", "") for m in _PRICE_RE.findall(text)}
        return [
            m
            for m in _SKU_RE.findall(text)
            if m not in phone_digits
            and m not in price_digits
            and not (m.isdigit() and len(m) >= 7)
        ]

    def extract_prices(self, text: str) -> list[str]:
        return [m.strip() for m in _PRICE_RE.findall(text)]

    def extract_address_fragments(self, text: str) -> list[str]:
        return [m.strip() for m in _ADDRESS_RE.findall(text)]
