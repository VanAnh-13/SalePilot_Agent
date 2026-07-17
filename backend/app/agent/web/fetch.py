from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

import httpx

from app.config import get_settings

MAX_BYTES = 200_000


def _blocked_host(host: str) -> bool:
    host = (host or "").lower()
    if host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        return True
    try:
        ip = ipaddress.ip_address(host)
        return bool(ip.is_private or ip.is_loopback or ip.is_link_local)
    except ValueError:
        return False


async def fetch_page_text(url: str) -> dict:
    if not get_settings().web_fetch_enabled:
        return {"ok": False, "error": "web_fetch disabled"}
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "only http/https"}
    parsed = urlparse(url)
    if _blocked_host(parsed.hostname or ""):
        return {"ok": False, "error": "private/local host blocked"}

    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "SalePilotBot/1.0"})
            raw = resp.content[:MAX_BYTES]
            text = raw.decode(resp.encoding or "utf-8", errors="replace")
            # crude HTML strip
            text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
            text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
            text = re.sub(r"(?s)<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            return {
                "ok": resp.status_code < 400,
                "status": resp.status_code,
                "url": str(resp.url),
                "text": text[:5000],
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}
