"""Vietnamese abbreviation registry for SalePilot NLP.

Abbreviations are declared as data (OCP): adding new entries requires no
code change, only a new entry in the mappings below.

Design:
  - AbbreviationRegistry owns one responsibility: expand abbreviations.
  - Context-sensitive entries (e.g. "k" = 1000 in prices vs "không" in text)
    are flagged and skipped by expand_text; callers that need context-aware
    expansion should handle those separately.
  - All entries are derived from the real DMX chat history corpus.
"""

from __future__ import annotations

import re
from typing import NamedTuple


class AbbreviationEntry(NamedTuple):
    short: str
    full: str
    # When True, the mapping is context-dependent and NOT applied by
    # expand_text() to avoid false positives (e.g. "k" after a digit = 1000).
    context_sensitive: bool = False


# ---------------------------------------------------------------------------
# Corpus-derived abbreviations (from DMX chat history analysis)
# ---------------------------------------------------------------------------

_ENTRIES: tuple[AbbreviationEntry, ...] = (
    # Chat / texting shorthand
    AbbreviationEntry("dc", "được"),
    AbbreviationEntry("ko", "không"),
    AbbreviationEntry("k", "không", context_sensitive=True),   # "3990k" ≠ "không"
    AbbreviationEntry("ntn", "như thế nào"),
    AbbreviationEntry("nt", "như thế"),
    AbbreviationEntry("mn", "màn hình"),
    AbbreviationEntry("bt", "bình thường"),
    AbbreviationEntry("sp", "sản phẩm"),
    AbbreviationEntry("dt", "điện thoại"),
    AbbreviationEntry("mk", "màu khác"),
    AbbreviationEntry("hm", "hôm nay"),
    AbbreviationEntry("oke", "ok"),
    AbbreviationEntry("okk", "ok"),
    AbbreviationEntry("ạ", "ạ"),           # already correct, kept for normalization pass
    AbbreviationEntry("af", "à"),
    AbbreviationEntry("r", "rồi"),
    AbbreviationEntry("đc", "được"),
    AbbreviationEntry("m", "mình", context_sensitive=True),    # "m²" ≠ "mình"
    AbbreviationEntry("b", "bạn", context_sensitive=True),     # "b" standalone only
    # Domain shorthand
    AbbreviationEntry("dmx", "Điện Máy Xanh"),
    AbbreviationEntry("tgdd", "Thế Giới Di Động"),
    AbbreviationEntry("bh", "bảo hành"),
    AbbreviationEntry("gg", "Google"),
    AbbreviationEntry("px", "pixel"),
    # Product attributes
    AbbreviationEntry("ssd", "SSD"),
    AbbreviationEntry("ram", "RAM"),
    AbbreviationEntry("gb", "GB"),
    AbbreviationEntry("tb", "TB"),
    AbbreviationEntry("hdd", "HDD"),
    AbbreviationEntry("mah", "mAh"),
)


class AbbreviationRegistry:
    """Expand Vietnamese abbreviations in text (SRP: expansion only)."""

    def __init__(self, entries: tuple[AbbreviationEntry, ...] = _ENTRIES) -> None:
        # Only non-context-sensitive entries are used in bulk text expansion.
        self._map: dict[str, str] = {
            e.short: e.full
            for e in entries
            if not e.context_sensitive
        }
        # Build a regex that matches whole-word abbreviations only.
        escaped = sorted(self._map, key=len, reverse=True)  # longest first
        pattern = r"\b(" + "|".join(re.escape(s) for s in escaped) + r")\b"
        self._pattern = re.compile(pattern, re.IGNORECASE)

    def expand(self, text: str) -> str:
        """Return text with safe (non-context-sensitive) abbreviations expanded."""
        def replace(m: re.Match) -> str:
            return self._map.get(m.group(0).lower(), m.group(0))

        return self._pattern.sub(replace, text)

    def known_abbreviations(self) -> frozenset[str]:
        return frozenset(self._map)
