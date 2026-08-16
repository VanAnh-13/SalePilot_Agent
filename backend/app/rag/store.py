import json
from pathlib import Path

from app.config import get_settings

_DATA = Path(__file__).resolve().parents[2] / "data"
_faq_cache: list[dict] | None = None
_product_cache: list[dict] | None = None


def reload_kb() -> None:
    global _faq_cache, _product_cache
    _faq_cache = None
    _product_cache = None


def _load_faq_from_pg() -> list[dict] | None:
    try:
        from sqlalchemy import select

        from app.db.sync import SyncSession
        from app.models.entities import KbDoc

        with SyncSession() as session:
            rows = session.execute(select(KbDoc)).scalars().all()
        return [
            {"id": r.id, "question": r.question, "answer": r.answer, "topic": r.topic, "source": r.source}
            for r in rows
        ] or None
    except Exception:
        return None


def _load_faq() -> list[dict]:
    """KB chunks — from PostgreSQL (primary), falling back to the JSON file."""
    global _faq_cache
    if _faq_cache is None:
        pg = _load_faq_from_pg()
        if pg is not None:
            _faq_cache = pg
        else:
            path = _DATA / "faq.json"
            _faq_cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    return _faq_cache


def _load_products() -> list[dict]:
    global _product_cache
    if _product_cache is None:
        path = _DATA / "products.json"
        _product_cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    return _product_cache


# ---------------------------------------------------------------------------
# Scoring — isolated in one place (SRP).  Callers pass context; Scorer
# applies lexical + metadata boosts without knowing about retrieval logic.
# ---------------------------------------------------------------------------

# Metadata field → query signal terms → score boost
# Declared as data so new domains only add entries here (OCP).
_METADATA_BOOSTS: list[tuple[str, list[str], float]] = [
    ("policy_type", ["bảo hành", "bao hanh", "bảo hành"], 1.5),
    ("policy_type", ["đổi trả", "doi tra", "hoàn tiền"], 1.5),
    ("policy_type", ["giao hàng", "giao hang", "ship", "vận chuyển"], 1.5),
    ("policy_type", ["lắp đặt", "lap dat", "lắp ráp"], 1.5),
    ("product_groups", ["điện thoại", "dien thoai", "iphone", "samsung"], 1.0),
    ("product_groups", ["laptop", "macbook", "máy tính xách tay"], 1.0),
    ("product_groups", ["tủ lạnh", "tu lanh"], 1.0),
    ("product_groups", ["máy lạnh", "may lanh", "điều hòa"], 1.0),
    ("product_groups", ["máy giặt", "may giat"], 1.0),
    ("product_groups", ["tivi", "ti vi", "tv"], 1.0),
]


class Scorer:
    """Compute relevance score for a FAQ chunk given a query.

    Single responsibility: scoring only.
    Combines lexical token overlap with optional metadata boosts.
    """

    def score(self, query: str, chunk: dict) -> float:
        q = query.lower().strip()
        text = (
            (chunk.get("question") or "")
            + " "
            + (chunk.get("answer") or "")
        ).lower()

        if not q:
            return 0.0

        # Lexical: token overlap
        lexical = 0.0
        for token in q.replace("?", " ").split():
            if len(token) < 2:
                continue
            if token in text:
                lexical += 1.0
        if q in text:
            lexical += 2.0

        if lexical == 0.0:
            return 0.0

        # Metadata boost: multiply lexical by boost factor when query matches
        boost = 1.0
        for meta_field, signals, factor in _METADATA_BOOSTS:
            field_values = chunk.get(meta_field) or []
            if not isinstance(field_values, list):
                continue
            if any(sig in q for sig in signals) and field_values:
                boost = max(boost, factor)

        return lexical * boost


_scorer = Scorer()


async def search_faq(query: str, k: int = 3) -> list[dict]:
    """Metadata-aware lexical retrieval — works offline without Chroma/embeddings."""
    faqs = _load_faq()
    scored = [(f, _scorer.score(query, f)) for f in faqs]
    ranked = sorted(scored, key=lambda x: -x[1])
    hits = [(f, s) for f, s in ranked if s > 0]
    return [
        {"id": f.get("id"), "question": f.get("question"), "answer": f.get("answer")}
        for f, _ in hits[:k]
    ]


async def search_policy(
    query: str,
    policy_type: str | None = None,
    product_group: str | None = None,
    k: int = 3,
) -> list[dict]:
    """Targeted policy retrieval with optional metadata pre-filtering.

    When ``policy_type`` or ``product_group`` are provided, only chunks
    matching those metadata tags are considered — this avoids cross-domain
    noise (e.g., a warranty query about TVs should not return phone policies).
    """
    faqs = _load_faq()

    def _matches_filters(chunk: dict) -> bool:
        if policy_type:
            types = chunk.get("policy_type") or []
            if policy_type not in types:
                return False
        if product_group:
            groups = chunk.get("product_groups") or []
            if product_group not in groups:
                return False
        return True

    candidates = [f for f in faqs if _matches_filters(f)] or faqs
    scored = [(f, _scorer.score(query, f)) for f in candidates]
    ranked = sorted(scored, key=lambda x: -x[1])
    hits = [(f, s) for f, s in ranked if s > 0]
    return [
        {"id": f.get("id"), "question": f.get("question"), "answer": f.get("answer")}
        for f, _ in hits[:k]
    ]


async def search_products_text(query: str, k: int = 5) -> list[dict]:
    products = _load_products()
    ranked = sorted(
        products,
        key=lambda p: _score(query, p.get("name", "") + " " + p.get("description", "") + " " + p.get("sku", "")),
        reverse=True,
    )
    return ranked[:k]


def ingest_kb() -> dict:
    """Ensure data files present; optional Chroma bootstrap for future upgrade."""
    settings = get_settings()
    chroma_path = Path(settings.chroma_path)
    chroma_path.mkdir(parents=True, exist_ok=True)
    faq_n = len(_load_faq())
    prod_n = len(_load_products())
    # Try Chroma if available — non-fatal
    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(chroma_path))
        try:
            client.delete_collection("salepilot_faq")
        except Exception:
            pass
        col = client.get_or_create_collection("salepilot_faq")
        if faq_n:
            faqs = _load_faq()
            col.add(
                ids=[f["id"] for f in faqs],
                documents=[f"{f['question']}\n{f['answer']}" for f in faqs],
                metadatas=[{"type": "faq"} for _ in faqs],
            )
        return {"faq": faq_n, "products": prod_n, "chroma": col.count()}
    except Exception as e:
        return {"faq": faq_n, "products": prod_n, "chroma": f"skipped: {e}"}
