"""Smart policy document chunker for the SalePilot knowledge base.

Splits Vietnamese policy Markdown documents into retrieval-optimal chunks,
enriching each chunk with structured metadata so the retrieval layer can
apply metadata-aware scoring (e.g., boost warranty chunks when the query
contains "bảo hành").

Design (SRP / OCP):
  - ``ChunkMetadataExtractor`` detects metadata from chunk text (single
    responsibility: metadata only).
  - ``SmartChunker`` splits a document into chunks (single responsibility:
    chunking only).
  - New metadata detectors can be added without touching SmartChunker (OCP).
  - All detection patterns are declared as data, not scattered in control flow.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Metadata detection — patterns declared as data (OCP-compliant)
# ---------------------------------------------------------------------------

# policy_type: term → canonical tag
_POLICY_TYPE_PATTERNS: list[tuple[str, str]] = [
    ("bảo hành", "bao_hanh"),
    ("đổi trả", "doi_tra"),
    ("giao hàng", "giao_hang"),
    ("lắp đặt", "lap_dat"),
    ("hoàn tiền", "hoan_tien"),
    ("kiểm tra", "kiem_tra"),
    ("khui hộp", "khui_hop"),
    ("dữ liệu", "du_lieu"),
    ("điều khoản", "dieu_khoan"),
    ("nội quy", "noi_quy"),
    ("chất lượng", "chat_luong"),
    ("vật tư", "vat_tu"),
    ("linh kiện", "linh_kien"),
]

# product_groups: term → group slug
_PRODUCT_GROUP_PATTERNS: list[tuple[str, str]] = [
    ("điện thoại", "dien_thoai"),
    ("laptop", "laptop"),
    ("máy tính bảng", "may_tinh_bang"),
    ("tivi", "tivi"),
    ("tủ lạnh", "tu_lanh"),
    ("máy lạnh", "may_lanh"),
    ("máy giặt", "may_giat"),
    ("máy lọc nước", "may_loc_nuoc"),
    ("máy nước nóng", "may_nuoc_nong"),
    ("máy hút bụi", "may_hut_bui"),
    ("loa", "loa"),
    ("tai nghe", "tai_nghe"),
    ("apple", "apple"),
]

# product_status: term → status slug
_PRODUCT_STATUS_PATTERNS: list[tuple[str, str]] = [
    ("hàng mới", "moi"),
    ("hàng trưng bày", "trung_bay"),
    ("hàng cũ", "cu"),
    ("thanh lý", "thanh_ly"),
]


@dataclass
class ChunkMetadata:
    policy_type: list[str] = field(default_factory=list)
    product_groups: list[str] = field(default_factory=list)
    product_status: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_type": self.policy_type,
            "product_groups": self.product_groups,
            "product_status": self.product_status,
        }


class ChunkMetadataExtractor:
    """Extract structured metadata from a chunk of Vietnamese policy text.

    Single responsibility: detect metadata tags from text.
    Does not chunk, does not write.
    """

    def extract(self, text: str) -> ChunkMetadata:
        low = text.lower()
        return ChunkMetadata(
            policy_type=self._match(low, _POLICY_TYPE_PATTERNS),
            product_groups=self._match(low, _PRODUCT_GROUP_PATTERNS),
            product_status=self._match(low, _PRODUCT_STATUS_PATTERNS),
        )

    @staticmethod
    def _match(text: str, patterns: list[tuple[str, str]]) -> list[str]:
        return [slug for term, slug in patterns if term in text]


# ---------------------------------------------------------------------------
# Chunking strategies
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    text: str
    index: int
    heading: str
    metadata: ChunkMetadata


def _extract_heading(text: str, max_len: int = 80) -> str:
    """First non-empty line, trimmed to max_len."""
    first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    first = re.sub(r"^#+\s*", "", first)  # strip Markdown heading markers
    return first[:max_len] + ("…" if len(first) > max_len else "")


class SmartChunker:
    """Split a policy document into retrieval-optimal chunks with metadata.

    Splitting strategy (highest to lowest priority):
      1. Split on Markdown headings (## / ###) — preserves document structure.
      2. If a section exceeds ``max_chars``, split further on blank lines
         (paragraph-level).
      3. If a paragraph still exceeds ``max_chars``, split on sentences.

    Single responsibility: chunking only.
    Metadata extraction is delegated to ``ChunkMetadataExtractor``.
    """

    def __init__(
        self,
        max_chars: int = 800,
        min_chars: int = 80,
        extractor: ChunkMetadataExtractor | None = None,
    ) -> None:
        self._max_chars = max_chars
        self._min_chars = min_chars
        self._extractor = extractor or ChunkMetadataExtractor()

    def chunk(self, text: str) -> list[Chunk]:
        sections = self._split_by_headings(text)
        raw_chunks: list[str] = []
        for section in sections:
            if len(section) <= self._max_chars:
                raw_chunks.append(section)
            else:
                raw_chunks.extend(self._split_by_paragraphs(section))

        # Filter trivially short chunks, assign index + metadata
        chunks: list[Chunk] = []
        for i, text_chunk in enumerate(raw_chunks):
            stripped = text_chunk.strip()
            if len(stripped) < self._min_chars:
                continue
            chunks.append(
                Chunk(
                    text=stripped,
                    index=i,
                    heading=_extract_heading(stripped),
                    metadata=self._extractor.extract(stripped),
                )
            )
        return chunks

    def _split_by_headings(self, text: str) -> list[str]:
        """Split on Markdown ## or ### headings, keeping heading with section."""
        parts = re.split(r"(?m)^(?=#{1,3}\s)", text)
        return [p.strip() for p in parts if p.strip()]

    def _split_by_paragraphs(self, text: str) -> list[str]:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        chunks: list[str] = []
        current = ""
        for para in paragraphs:
            candidate = f"{current}\n\n{para}".strip() if current else para
            if len(candidate) <= self._max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                # Para itself might still be too long — split on sentences
                if len(para) > self._max_chars:
                    chunks.extend(self._split_by_sentences(para))
                    current = ""
                else:
                    current = para
        if current:
            chunks.append(current)
        return chunks

    def _split_by_sentences(self, text: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks: list[str] = []
        current = ""
        for sent in sentences:
            candidate = f"{current} {sent}".strip() if current else sent
            if len(candidate) <= self._max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = sent
        if current:
            chunks.append(current)
        return chunks
