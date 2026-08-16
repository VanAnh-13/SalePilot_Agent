"""Hybrid retrieval: Chroma embeddings at query time (offline fake EF)."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

_TMP = tempfile.mkdtemp(prefix="salepilot_rag_emb_")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP}/rag_emb.db"
os.environ["TRAJECTORY_ENABLED"] = "false"
os.environ["CHROMA_PATH"] = os.path.join(_TMP, "chroma")
os.environ["RAG_EMBEDDINGS_ENABLED"] = "true"

import app.rag.store as store  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.rag.store import search_policy  # noqa: E402

_FAKE_KB = [
    {
        "id": "giao-1",
        "question": "Giao hàng bao lâu?",
        "answer": "Giao hàng nội thành 1–3 ngày.",
        "topic": "giao_hang_lap_dat",
        "source": "policies/g.md",
        "policy_type": ["giao_hang"],
        "product_groups": [],
    },
    {
        "id": "bao-1",
        "question": "Bảo hành bao lâu?",
        "answer": "Bảo hành 12 tháng.",
        "topic": "bao_hanh_doi_tra",
        "source": "policies/b.md",
        "policy_type": ["bao_hanh"],
        "product_groups": [],
    },
]


class _KeywordEF:
    """Deterministic offline embedding: one-hot by first keyword found."""

    KEYS = ("giao", "bảo hành", "đổi trả")

    def name(self) -> str:
        return "fake-keyword"

    def __call__(self, input):  # noqa: A002 — chromadb protocol
        out = []
        for text in input:
            vec = [0.01, 0.01, 0.01, 0.01]
            lowered = (text or "").lower()
            for idx, key in enumerate(self.KEYS):
                if key in lowered:
                    vec[idx] = 1.01
                    break
            else:
                vec[-1] = 1.01  # unrelated texts get their own orthogonal axis
            out.append(vec)
        return out

    def embed_query(self, input):
        # chromadb 1.x passes [query] and expects a list of embeddings back.
        texts = input if isinstance(input, list) else [input]
        return self(texts)


class HybridRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import asyncio

        from app.db.session import init_db

        asyncio.run(init_db())
        get_settings.cache_clear()

    def setUp(self):
        store._faq_cache = [dict(c) for c in _FAKE_KB]
        store._chroma_state = None

    def tearDown(self):
        store.reload_kb()
        store._chroma_state = None

    def _with_fake_ef(self):
        return patch.object(store, "_embedding_function", _KeywordEF)

    def test_semantic_reranks_equal_lexical_scores(self):
        # Both chunks share the lexical token "bao" (in "bao lâu"), so pure
        # lexical cannot separate them; the embedding must rank the delivery
        # chunk first for a delivery-phrased query.
        import asyncio

        with self._with_fake_ef():
            sims = store._semantic_similarities("giao hàng mất bao lâu", _FAKE_KB)
            hits = asyncio.run(search_policy("giao hàng mất bao lâu"))
        # Semantic layer actually fired and separated the two chunks.
        self.assertGreaterEqual(sims.get("giao-1", 0.0), store.SEMANTIC_FLOOR)
        self.assertLess(sims.get("bao-1", 0.0), store.SEMANTIC_FLOOR)
        self.assertTrue(hits)
        self.assertEqual(hits[0]["id"], "giao-1")

    def test_collection_autopopulates_from_kb(self):
        with self._with_fake_ef():
            col = store._chroma_collection()
        self.assertIsNotNone(col)
        self.assertEqual(col.count(), len(_FAKE_KB))

    def test_flag_off_is_pure_lexical(self):
        os.environ["RAG_EMBEDDINGS_ENABLED"] = "false"
        get_settings.cache_clear()
        store._chroma_state = None
        try:
            with self._with_fake_ef():
                self.assertEqual(store._semantic_similarities("giao hàng", _FAKE_KB), {})
        finally:
            os.environ["RAG_EMBEDDINGS_ENABLED"] = "true"
            get_settings.cache_clear()
            store._chroma_state = None

    def test_chroma_failure_degrades_to_lexical(self):
        import asyncio

        with patch.object(store, "_chroma_collection", return_value=None):
            sims = store._semantic_similarities("giao hàng", _FAKE_KB)
            self.assertEqual(sims, {})
            hits = asyncio.run(search_policy("giao hàng mất bao lâu"))
        self.assertTrue(hits)  # lexical still returns results

    def test_below_floor_similarity_ignored(self):
        # 'khui hop' matches no fake-embedding keyword → sim < floor → the
        # hybrid score equals the lexical score.
        with self._with_fake_ef():
            sims = store._semantic_similarities("khui hộp iphone", _FAKE_KB)
        for sim in sims.values():
            self.assertLess(sim, store.SEMANTIC_FLOOR)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
