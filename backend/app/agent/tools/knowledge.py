import json

from langchain_core.tools import tool

from app.agent.tools.runtime import note_tool
from app.rag.store import POLICY_SIGNALS, search_policy


def detect_policy_type(query: str) -> str | None:
    """First policy domain whose signals appear in the query, if any.

    Keywords come from rag.store.POLICY_SIGNALS — the same source the scorer
    boosts use, so detection and boosting can never drift apart.
    """
    q = (query or "").lower()
    for tag, signals in POLICY_SIGNALS.items():
        if any(s in q for s in signals):
            return tag
    return None


@tool
async def search_knowledge(query: str) -> str:
    """Tra cứu FAQ / chính sách shop (giao hàng, đổi trả, bảo hành, giờ mở cửa, thanh toán)."""
    note_tool("search_knowledge")
    hits = await search_policy(query, policy_type=detect_policy_type(query), k=3)
    if not hits:
        return json.dumps(
            {
                "results": [],
                "fallback": (
                    "Không có thông tin này trong knowledge base hiện tại. "
                    "Cần xác nhận chính sách cửa hàng/hãng trước khi trả lời."
                ),
            },
            ensure_ascii=False,
        )
    return json.dumps({"results": hits}, ensure_ascii=False)
