"""Shared category model and lookup behavior for catalog adapters.

Concrete catalog modules own their declarations and normalization rules.  This
module owns only the stable category shape plus deterministic registry
operations used by both the workbook and crawl adapters.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Spec:
    key: str
    col: str
    mode: str = "num"
    unit: str = ""


@dataclass(frozen=True)
class RangeSpec:
    key: str
    col: str
    kind: str


@dataclass(frozen=True)
class Slot:
    key: str
    label: str
    question: str = ""
    kind: str = "proximity"
    spec_key: str = ""
    range_key: str = ""
    unit: str = ""
    weight: float = 5.0
    extract: tuple[str, ...] = ()
    mult: float = 1.0
    primary: bool = False
    hardness: str = "soft"
    missing_policy: str = "allow_unknown"


@dataclass(frozen=True)
class Priority:
    key: str
    aliases: tuple[str, ...]
    mode: str = "bool"
    spec_key: str = ""
    value: str = ""
    weight: float = 3.0


@dataclass(frozen=True)
class Tradeoff:
    label: str
    spec_key: str
    mode: str
    unit: str = ""
    fmt: str = "num"


@dataclass(frozen=True)
class Category:
    code: int
    slug: str
    display: str
    sheet: str
    aliases: tuple[str, ...]
    specs: tuple[Spec, ...] = ()
    ranges: tuple[RangeSpec, ...] = ()
    name_specs: tuple[str, ...] = ()
    desc_specs: tuple[str, ...] = ()
    slots: tuple[Slot, ...] = ()
    priorities: tuple[Priority, ...] = ()
    tradeoffs: tuple[Tradeoff, ...] = ()
    generic: bool = False

    def spec_unit(self, key: str) -> str:
        for spec in self.specs:
            if spec.key == key:
                return spec.unit
        for slot in self.slots:
            if slot.spec_key == key and slot.unit:
                return slot.unit
        return ""


UnsupportedTerm = tuple[str, str, str]
GenericCategoryProvider = Callable[[], Mapping[str, Category]]

_NEGATION = re.compile(
    r"(?:(?:không|khong|ko|chẳng|chang)\s*(?:phải|phai|cần|can|mua|lấy|lay)?"
    r"|(?:đâu|dau)\s+(?:phải|phai))\s*$"
)


def unaccent(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFD", text)
    return "".join(char for char in nfkd if unicodedata.category(char) != "Mn")


def slugify(text: str) -> str:
    base = unaccent(str(text or "")).casefold()
    base = re.sub(r"[^a-z0-9]+", "_", base).strip("_")
    return base or "khac"


def make_generic(code: int, display: str) -> Category:
    display = str(display or "Sản phẩm").strip()
    slug = slugify(display)
    aliases = tuple(
        dict.fromkeys(
            alias
            for alias in (
                display.casefold(),
                unaccent(display).casefold(),
                slug.replace("_", " "),
            )
            if len(alias) >= 3
        )
    )
    return Category(
        code=int(code),
        slug=slug,
        display=display,
        sheet=display,
        aliases=aliases,
        generic=True,
    )


class CategoryRegistry:
    """Read-only lookup and Vietnamese intent-detection facade."""

    def __init__(
        self,
        categories: Iterable[Category],
        *,
        unsupported_terms: Iterable[UnsupportedTerm] = (),
        generic_categories: GenericCategoryProvider | None = None,
        ignore_unsupported_when_category_detected: bool = False,
    ) -> None:
        self.categories = tuple(categories)
        self.by_slug = {category.slug: category for category in self.categories}
        self.by_code = {category.code: category for category in self.categories}
        self.by_sheet = {category.sheet: category for category in self.categories}
        self.unsupported_terms = tuple(unsupported_terms)
        self._generic_categories = generic_categories
        self._ignore_unsupported_when_category_detected = (
            ignore_unsupported_when_category_detected
        )

    def _generic(self) -> Mapping[str, Category]:
        if self._generic_categories is None:
            return {}
        return self._generic_categories()

    def get_category(self, ref: str | int | None) -> Category | None:
        if ref is None:
            return None
        if isinstance(ref, int) or (
            isinstance(ref, str) and str(ref).strip().isdigit()
        ):
            code = int(ref)
            if category := self.by_code.get(code):
                return category
            return next(
                (category for category in self._generic().values() if category.code == code),
                None,
            )

        slug = str(ref).strip()
        if category := self.by_slug.get(slug):
            return category
        return self._generic().get(slug)

    @staticmethod
    def _is_negated(text: str, start: int) -> bool:
        prefix = text[max(0, start - 24) : start].strip()
        return bool(_NEGATION.search(prefix))

    @classmethod
    def _scan_aliases(
        cls,
        categories: Iterable[Category],
        text: str,
    ) -> tuple[int, Category] | None:
        best: tuple[int, Category] | None = None
        for category in categories:
            for alias in category.aliases:
                if not alias:
                    continue
                for match in re.finditer(re.escape(alias), text):
                    if cls._is_negated(text, match.start()):
                        continue
                    score = len(alias)
                    if best is None or score > best[0]:
                        best = score, category
                    break
        return best

    def detect_category(self, text: str) -> Category | None:
        normalized = (text or "").casefold()
        best = self._scan_aliases(self.categories, normalized)
        generic_best = self._scan_aliases(self._generic().values(), normalized)
        if generic_best and (best is None or generic_best[0] > best[0]):
            best = generic_best
        return best[1] if best else None

    def detect_negated_categories(self, text: str) -> set[str]:
        normalized = (text or "").casefold()
        negated: set[str] = set()
        for category in self.categories:
            for alias in category.aliases:
                for match in re.finditer(re.escape(alias), normalized):
                    if self._is_negated(normalized, match.start()):
                        negated.add(category.slug)
        return negated

    def detect_unsupported(self, text: str) -> tuple[str, str] | None:
        if (
            self._ignore_unsupported_when_category_detected
            and self.detect_category(text) is not None
        ):
            return None
        normalized = (text or "").casefold()
        for pattern, display, suggestion in self.unsupported_terms:
            if re.search(pattern, normalized):
                return display, suggestion
        return None
