import json
import logging
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)

_DATA = Path(__file__).resolve().parents[2] / "data"
_faq_cache: list[dict] | None = None
_product_cache: list[dict] | None = None

# Hybrid retrieval weights: semantic similarity (cosine, 0..1) contributes
# SEMANTIC_WEIGHT points on top of the lexical score, but only when at or
# above SEMANTIC_FLOOR — below that the signal is noise, not paraphrase.
SEMANTIC_WEIGHT = 2.0
SEMANTIC_FLOOR = 0.55


def reload_kb() -> None:
    global _faq_cache, _product_cache, _chroma_state
    _faq_cache = None
    _product_cache = None
    _chroma_state = None


# KbDoc has no metadata columns, so the PG loader reconstructs the coarse
# policy_type tags from the existing `topic` column. Chunk-level granularity
# (e.g. a delivery doc chunk that is only about installation) is lost, but the
# scorer boosts and search_policy filters work identically on both sources.
_TOPIC_POLICY_TYPES: dict[str, list[str]] = {
    "bao_hanh_doi_tra": ["bao_hanh", "doi_tra", "hoan_tien"],
    "giao_hang_lap_dat": ["giao_hang", "lap_dat"],
    "khui_hop_apple": ["khui_hop", "kiem_tra"],
    "du_lieu_ca_nhan": ["du_lieu"],
    "dieu_khoan": ["dieu_khoan"],
    "noi_quy": ["noi_quy"],
    "phuc_vu": ["chat_luong"],
}


def _load_faq_from_pg() -> list[dict] | None:
    try:
        from sqlalchemy import select

        from app.db.sync import SyncSession
        from app.models.entities import KbDoc

        with SyncSession() as session:
            rows = session.execute(select(KbDoc)).scalars().all()
        return [
            {
                "id": r.id,
                "question": r.question,
                "answer": r.answer,
                "topic": r.topic,
                "source": r.source,
                "policy_type": _TOPIC_POLICY_TYPES.get(r.topic or "", []),
                "product_groups": [],
            }
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

# Single source of truth for policy-domain keywords: the scorer's metadata
# boost AND the retrieval pre-filter (tools/knowledge.py) both derive from
# this mapping — policy_type tag -> user-query signals (diacritic + plain).
POLICY_SIGNALS: dict[str, tuple[str, ...]] = {
    "bao_hanh": ("bảo hành", "bao hanh", "warranty"),
    "doi_tra": ("đổi trả", "doi tra", "hoàn tiền", "hoan tien", "đổi cũ"),
    "giao_hang": ("giao hàng", "giao hang", "ship", "vận chuyển", "van chuyen"),
    "lap_dat": ("lắp đặt", "lap dat", "lắp ráp"),
    "khui_hop": ("khui hộp", "khui hop", "kích hoạt apple", "kich hoat apple"),
    "hoan_tien": ("hoàn tiền", "hoan tien"),
    "chat_luong": ("chất lượng phục vụ", "chat luong phuc vu"),
    "du_lieu": ("dữ liệu cá nhân", "du lieu ca nhan"),
    "noi_quy": ("nội quy", "noi quy"),
    "dieu_khoan": ("điều khoản", "dieu khoan"),
}

# Metadata field → query signal terms → score boost
# Declared as data so new domains only add entries here (OCP).
_METADATA_BOOSTS: list[tuple[str, list[str], float]] = [
    # Policy rows derive from POLICY_SIGNALS so keywords never drift apart.
    *[("policy_type", list(signals), 1.5) for signals in POLICY_SIGNALS.values()],
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


# ---------------------------------------------------------------------------
# Semantic layer — Chroma embeddings at query time (hybrid retrieval).
# Off by default (RAG_EMBEDDINGS_ENABLED): the default embedding function
# downloads a model on first use. Every failure degrades to pure lexical.
# ---------------------------------------------------------------------------
_chroma_state: object | None = None  # None=untried, False=failed, Collection=ok
_CHROMA_COLLECTION = "salepilot_faq"


def _embedding_function():
    model = (get_settings().chroma_embedding_model or "").strip()
    if model:
        from chromadb.utils import embedding_functions

        return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model)
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

    return DefaultEmbeddingFunction()


def _chroma_collection():
    """Lazily open (and auto-populate) the FAQ collection; None when unusable."""
    global _chroma_state
    if _chroma_state is not None:
        return _chroma_state or None
    if not get_settings().rag_embeddings_enabled:
        _chroma_state = False
        return None
    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(Path(get_settings().chroma_path)))
        col = client.get_or_create_collection(
            name=_CHROMA_COLLECTION,
            embedding_function=_embedding_function(),
            metadata={"hnsw:space": "cosine"},
        )
        if col.count() == 0:
            faqs = _load_faq()
            if faqs:
                col.add(
                    ids=[f["id"] for f in faqs],
                    documents=[f"{f.get('question', '')}\n{f.get('answer', '')}" for f in faqs],
                    metadatas=[{"type": "faq"} for _ in faqs],
                )
        _chroma_state = col
        return col
    except Exception:
        logger.warning("Chroma embeddings unavailable — lexical-only retrieval", exc_info=True)
        _chroma_state = False
        return None


def _semantic_similarities(query: str, candidates: list[dict]) -> dict[str, float]:
    """id -> cosine similarity for the query against the candidates, or {}."""
    col = _chroma_collection()
    if col is None or not candidates:
        return {}
    try:
        n = min(max(len(candidates), 10), 50)
        res = col.query(query_texts=[query], n_results=n, include=["distances"])
        ids = (res.get("ids") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        # cosine space: distance = 1 - similarity
        return {i: max(0.0, 1.0 - d) for i, d in zip(ids, dists)}
    except Exception:
        logger.warning("semantic query failed — lexical-only for this call", exc_info=True)
        return {}


def _hybrid_score(query: str, chunk: dict, semantic: dict[str, float]) -> float:
    lexical = _scorer.score(query, chunk)
    sim = semantic.get(chunk.get("id") or "", 0.0)
    if sim < SEMANTIC_FLOOR:
        return lexical
    return lexical + SEMANTIC_WEIGHT * sim


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
    semantic = _semantic_similarities(query, candidates)
    scored = [(f, _hybrid_score(query, f, semantic)) for f in candidates]
    ranked = sorted(scored, key=lambda x: -x[1])
    hits = [(f, s) for f, s in ranked if s > 0]
    return [
        {"id": f.get("id"), "question": f.get("question"), "answer": f.get("answer")}
        for f, _ in hits[:k]
    ]


def ingest_kb() -> dict:
    """Bootstrap the Chroma FAQ collection (cosine space, shared embedding
    function with query-time retrieval). Non-fatal when Chroma is unusable."""
    global _chroma_state
    settings = get_settings()
    chroma_path = Path(settings.chroma_path)
    chroma_path.mkdir(parents=True, exist_ok=True)
    faq_n = len(_load_faq())
    prod_n = len(_load_products())
    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(chroma_path))
        try:
            client.delete_collection(_CHROMA_COLLECTION)
        except Exception:
            pass
        col = client.get_or_create_collection(
            name=_CHROMA_COLLECTION,
            embedding_function=_embedding_function(),
            metadata={"hnsw:space": "cosine"},
        )
        if faq_n:
            faqs = _load_faq()
            col.add(
                ids=[f["id"] for f in faqs],
                documents=[f"{f['question']}\n{f['answer']}" for f in faqs],
                metadatas=[{"type": "faq"} for _ in faqs],
            )
        _chroma_state = None  # force re-open with the fresh collection
        return {"faq": faq_n, "products": prod_n, "chroma": col.count()}
    except Exception as e:
        return {"faq": faq_n, "products": prod_n, "chroma": f"skipped: {e}"}
