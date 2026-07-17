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


def _load_faq() -> list[dict]:
    global _faq_cache
    if _faq_cache is None:
        path = _DATA / "faq.json"
        _faq_cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    return _faq_cache


def _load_products() -> list[dict]:
    global _product_cache
    if _product_cache is None:
        path = _DATA / "products.json"
        _product_cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    return _product_cache


def _score(query: str, text: str) -> float:
    q = query.lower().strip()
    t = text.lower()
    if not q:
        return 0.0
    score = 0.0
    for token in q.replace("?", " ").split():
        if len(token) < 2:
            continue
        if token in t:
            score += 1.0
    if q in t:
        score += 2.0
    return score


async def search_faq(query: str, k: int = 3) -> list[dict]:
    """Simple lexical retrieval — works offline without Chroma/embeddings."""
    faqs = _load_faq()
    ranked = sorted(
        faqs,
        key=lambda f: _score(query, f.get("question", "") + " " + f.get("answer", "")),
        reverse=True,
    )
    hits = [f for f in ranked if _score(query, f.get("question", "") + " " + f.get("answer", "")) > 0]
    return [
        {"id": h.get("id"), "question": h.get("question"), "answer": h.get("answer")}
        for h in hits[:k]
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
