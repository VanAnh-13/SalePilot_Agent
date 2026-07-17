import json

from langchain_core.tools import tool

from app.agent.tools.runtime import note_tool
from app.agent.web.fetch import fetch_page_text


@tool
async def fetch_page(url: str) -> str:
    """Tải nội dung text từ URL public (http/https), chặn localhost/private IP."""
    note_tool("fetch_page")
    result = await fetch_page_text(url)
    return json.dumps(result, ensure_ascii=False)
