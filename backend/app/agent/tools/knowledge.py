import json

from langchain_core.tools import tool

from app.agent.tools.runtime import note_tool
from app.rag.store import search_faq


@tool
async def search_knowledge(query: str) -> str:
    """Tra cứu FAQ / chính sách shop (giao hàng, đổi trả, bảo hành, giờ mở cửa, thanh toán)."""
    note_tool("search_knowledge")
    hits = await search_faq(query, k=3)
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
