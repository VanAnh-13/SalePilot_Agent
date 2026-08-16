from __future__ import annotations

import ipaddress
import re
import socket
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import get_settings

MAX_BYTES = 200_000
# Maximum number of redirects we follow manually (httpx follows automatically;
# we replicate each hop's destination check in _safe_get below).
_MAX_REDIRECTS = 5

# Cloud metadata endpoints that should never be reachable regardless of how
# DNS resolves them.  These are checked against both hostnames and IPs.
_BLOCKED_HOSTNAMES = frozenset(
    {
        "metadata.google.internal",
        "metadata.gcp.internal",
        "169.254.169.254",
        "fd00:ec2::254",  # AWS IPv6 IMDS
    }
)


def _blocked_host(host: str) -> bool:
    """Return True if the host string resolves to or IS a private/local address."""
    host = (host or "").lower().rstrip(".")
    if not host:
        return True
    if host in _BLOCKED_HOSTNAMES:
        return True
    # Literal loopback / wildcard checks (fast path before DNS).
    if host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        return True
    # If it parses as a literal IP, check immediately — no DNS needed.
    try:
        ip = ipaddress.ip_address(host)
        return bool(
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_unspecified
            or str(ip) in _BLOCKED_HOSTNAMES
        )
    except ValueError:
        pass
    # For hostnames: resolve all A/AAAA records and reject if ANY is private.
    try:
        infos = socket.getaddrinfo(host, None)
        for _family, _type, _proto, _canon, sockaddr in infos:
            resolved_ip = str(sockaddr[0])
            if _blocked_host(resolved_ip):  # recurse with the literal IP string
                return True
    except (socket.gaierror, OSError):
        # If DNS fails, fail closed.
        return True
    return False


# KNOWN LIMITATION — DNS rebinding TOCTOU (audit 2026-08-01):
# _blocked_host resolves DNS and checks all A/AAAA records before the request.
# However, httpx.AsyncClient performs its own DNS resolution at connect time.
# A DNS rebinding attack can return a public IP for our check, then switch to a
# private IP (e.g. 169.254.169.254) before httpx connects.  The default
# web_fetch_enabled=False mitigates this by disabling the feature entirely.
# A more robust fix would use a custom httpx transport that pins the resolved
# IP from our check, but that is not implemented.  If web_fetch is enabled in
# production, consider adding egress firewall rules blocking RFC1918/link-local.


async def fetch_page_text(url: str) -> dict[str, Any]:
    if not get_settings().web_fetch_enabled:
        return {"ok": False, "error": "web_fetch disabled"}
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "only http/https"}
    parsed = urlparse(url)
    if _blocked_host(parsed.hostname or ""):
        return {"ok": False, "error": "private/local host blocked"}

    return await _safe_get(url)

async def _safe_get(url: str, *, _hops: int = 0) -> dict[str, Any]:
    """Fetch url without blindly following redirects to private hosts."""
    if _hops > _MAX_REDIRECTS:
        return {"ok": False, "error": "too many redirects"}

    try:
        async with httpx.AsyncClient(
            timeout=12.0,
            # Do NOT follow redirects automatically — we re-check each hop.
            follow_redirects=False,
        ) as client:
            resp = await client.get(url, headers={"User-Agent": "SalePilotBot/1.0"})

            # Handle redirects manually so we can validate each destination.
            if resp.is_redirect:
                location = resp.headers.get("location", "")
                if not location:
                    return {"ok": False, "error": "redirect with no Location header"}
                # Resolve relative redirects.
                next_url = str(resp.next_request.url) if resp.next_request else location
                parsed = urlparse(next_url)
                if _blocked_host(parsed.hostname or ""):
                    return {"ok": False, "error": f"redirect to private host blocked: {next_url}"}
                return await _safe_get(next_url, _hops=_hops + 1)

            raw = resp.content[:MAX_BYTES]
            text = raw.decode(resp.encoding or "utf-8", errors="replace")
            # Crude HTML strip.
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
