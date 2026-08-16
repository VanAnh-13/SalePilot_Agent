"""Admin authentication dependency for FastAPI.

Usage:
    from app.api.auth import require_admin_token

    @router.get("/admin-endpoint")
    async def some_route(token: None = Depends(require_admin_token)):
        ...

The admin token is read from the ``ADMIN_API_KEY`` environment variable (via
pydantic-settings).  If the variable is empty the endpoint always returns 403
so that a misconfigured deployment fails closed rather than open.
"""

import hmac

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import get_settings

_HEADER_SCHEME = APIKeyHeader(name="X-Admin-Token", auto_error=False)


async def require_admin_token(
    token: str | None = Security(_HEADER_SCHEME),
) -> None:
    """FastAPI dependency that enforces admin bearer-token authentication.

    Raises HTTP 401 when the header is missing, HTTP 403 when the token does
    not match ``ADMIN_API_KEY``, and HTTP 503 when no key is configured
    (fail-closed policy: an unconfigured deployment must not serve PII).
    """
    settings = get_settings()
    configured_key = (settings.admin_api_key or "").strip()

    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Admin API is not configured. "
                "Set ADMIN_API_KEY in the server environment."
            ),
        )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Admin-Token header is required.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Constant-time comparison to resist timing attacks.
    if not hmac.compare_digest(token, configured_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token.",
        )
