"""Shared parsers for messy Vietnamese product-spec text.

These helpers turn spreadsheet cells like ``"313 lít"``, ``"1.5 HP"``,
``"Từ 30 - 40m²"`` or ``"Dàn lạnh: 45/34/29 dB"`` into numbers the ranking
engine can reason about. They are deliberately forgiving: unknown or empty
text returns ``None`` rather than raising.
"""

from __future__ import annotations

import re
from typing import Any


def clean(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def numbers(value: Any) -> list[float]:
    """Every numeric token in the text (thousand/decimal aware for the first)."""
    text = clean(value)
    if not text:
        return []
    out: list[float] = []
    for token in re.findall(r"-?\d[\d.,]*", text):
        parsed = _parse_number_token(token)
        if parsed is not None:
            out.append(parsed)
    return out


def _parse_number_token(number: str) -> float | None:
    separators = [i for i, ch in enumerate(number) if ch in ".,"]
    if not separators:
        cleaned = number
    else:
        last = separators[-1]
        decimals = len(number) - last - 1
        if len(separators) == 1:
            if decimals == 3:
                cleaned = number.replace(".", "").replace(",", "")
            else:
                cleaned = number.replace(",", ".")
        elif decimals in {1, 2}:
            dec_sep = number[last]
            thou_sep = "," if dec_sep == "." else "."
            cleaned = number.replace(thou_sep, "").replace(dec_sep, ".")
        else:
            cleaned = number.replace(".", "").replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        # Multi-separator tokens like "17.2.1" (an OS/firmware version) leave
        # multiple dots after stripping thousand separators — unparseable. Honor
        # the module contract ("returns None rather than raising") instead of
        # aborting the whole catalog import with a ValueError.
        return None


def number(value: Any) -> float | None:
    """First numeric value in the text (e.g. ``"16 GB"`` -> ``16.0``)."""
    values = numbers(value)
    return values[0] if values else None


def integer(value: Any) -> int | None:
    result = number(value)
    return int(round(result)) if result is not None else None


def min_number(value: Any) -> float | None:
    values = numbers(value)
    return min(values) if values else None


def max_number(value: Any) -> float | None:
    values = numbers(value)
    return max(values) if values else None


def yes_no(value: Any) -> bool | None:
    text = (clean(value) or "").casefold()
    if not text:
        return None
    if text in {"có", "co", "yes"}:
        return True
    if text in {"không", "khong", "không có", "khong co", "no"}:
        return False
    return None


def dimension_cm(value: Any, axis: str) -> float | None:
    """Extract one labeled dimension from a combined Vietnamese dimension cell."""
    text = (clean(value) or "").casefold()
    aliases = {
        "width": ("ngang", "rộng", "rong"),
        "height": ("cao",),
        "depth": ("sâu", "sau"),
    }
    labels = aliases.get(axis, ())
    if not text or not labels:
        return None
    pattern = rf"(?:{'|'.join(re.escape(label) for label in labels)})\s*(\d+(?:[.,]\d+)?)\s*cm"
    match = re.search(pattern, text)
    return float(match.group(1).replace(",", ".")) if match else None


def price(value: Any) -> int | None:
    """Parse a VND price cell into a plain integer (or ``None``)."""
    text = clean(value)
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    if not digits:
        return None
    result = int(digits)
    return result or None


def split_features(value: Any) -> list[str]:
    text = clean(value)
    if not text:
        return []
    return [item.strip() for item in re.split(r"\s*\|\s*", text) if item.strip()]


_PEOPLE_RE = re.compile(
    r"(?:từ|tu\s)?\s*(trên|tren|hơn|hon|dưới|duoi)?\s*(\d+)\s*"
    r"(?:(?:[-–]|đến|den)\s*(\d+)\s*)?ng[uươ]ờ?i",
)


def people_range(label: Any) -> tuple[int | None, int | None]:
    """People capacity, anchored on the word ``người`` so unrelated numbers in
    the same cell are ignored.

    ``"3 - 4 người"`` -> ``(3, 4)`` ; ``"Trên 5 người"`` -> ``(6, None)`` ;
    ``"656 lít - Trên 5 người"`` -> ``(6, None)`` (the litres are skipped).
    """
    text = clean(label)
    if not text:
        return None, None
    m = _PEOPLE_RE.search(text.casefold())
    if not m:
        return None, None
    mod, a_raw, b_raw = m.group(1), m.group(2), m.group(3)
    a = int(a_raw)
    b = int(b_raw) if b_raw else None
    if mod in {"trên", "tren", "hơn", "hon"}:
        return a + 1, None
    if mod in {"dưới", "duoi"}:
        return None, a
    if b is not None:
        return a, b
    return a, a


def area_range(label: Any) -> tuple[float | None, float | None]:
    """Room area range for air conditioners.

    ``"Từ 30 - 40m² (từ 80 đến 120m³)"`` -> ``(30, 40)``
    ``"Dưới 15m²"`` -> ``(None, 15)`` ; ``"Trên 40m²"`` -> ``(40, None)``
    Only the m² figures (before any ``m³`` part) are considered.
    """
    text = clean(label)
    if not text:
        return None, None
    low = text.casefold()
    # Keep only the portion describing m² (drop the m³ clause in parentheses).
    m2_part = re.split(r"m³|\(", low)[0]
    values = [float(v.replace(",", ".")) for v in re.findall(r"\d+(?:[.,]\d+)?", m2_part)]
    if not values:
        return None, None
    if "dưới" in m2_part or "duoi" in m2_part or "<" in m2_part:
        return None, values[0]
    if "trên" in m2_part or "tren" in m2_part or ">" in m2_part:
        return values[0], None
    if len(values) >= 2:
        return values[0], values[1]
    return values[0], values[0]
