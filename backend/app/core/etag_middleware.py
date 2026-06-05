"""
ETag / Conditional Request middleware — P1-1.

Behaviour:
  - For GET responses with 2xx status and JSON content, computes a weak ETag
    (SHA-256 of the response body, truncated to 16 hex chars).
  - Returns 304 Not Modified when the client's If-None-Match header matches.
  - Adds Cache-Control headers with user-scoped, private directives.
  - Never caches auth, sensitive, or non-GET responses.

This middleware complements Redis cache-aside caching:
  - Redis removes DB round-trips entirely for repeated identical requests.
  - ETags remove network round-trips when the response hasn't changed.
"""

import hashlib
import time
from typing import Callable

from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


# Paths that must never be cached
_NO_CACHE_PATHS = frozenset([
    "/api/v1/auth/",
    "/metrics",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
])

# TTL configuration per path prefix (seconds)
_CACHE_TTL: list[tuple[str, int]] = [
    ("/api/v1/expenses/analytics",  600),   # 10 min — aggregate analytics
    ("/api/v1/goals",               300),   # 5 min  — goals list
    ("/api/v1/budgets/analytics",   600),   # 10 min — budget analytics
    ("/api/v1/budgets",             300),   # 5 min  — budget list
    ("/api/v1/expenses",            120),   # 2 min  — expense list
    ("/api/v1/notifications",        60),   # 1 min  — notifications
    ("/api/v1/loans",               300),   # 5 min  — loans
]


def _get_ttl(path: str) -> int:
    """Return the TTL for a given path prefix, or 0 (no-cache)."""
    for prefix, ttl in _CACHE_TTL:
        if path.startswith(prefix):
            return ttl
    return 0


class ETagMiddleware(BaseHTTPMiddleware):
    """
    Adds ETag + Cache-Control headers for GET responses.

    Works **alongside** Redis caching — ETags reduce downstream network traffic
    while Redis eliminates DB load. Both layers are complementary.
    """

    def __init__(self, app: ASGIApp, enabled: bool = True) -> None:
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only process GET / HEAD requests
        if not self.enabled or request.method not in ("GET", "HEAD"):
            return await call_next(request)

        path = request.url.path

        # Never cache auth or internal endpoints
        if any(path.startswith(p) for p in _NO_CACHE_PATHS):
            return await call_next(request)

        ttl = _get_ttl(path)
        if ttl <= 0:
            return await call_next(request)

        response = await call_next(request)

        # Only add ETags to successful JSON responses
        if response.status_code not in range(200, 300):
            return response

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        # Consume body to compute ETag
        body_chunks: list[bytes] = []
        async for chunk in response.body_iterator:  # type: ignore[attr-defined]
            body_chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode())
        body = b"".join(body_chunks)

        # Compute weak ETag (W/"<16-hex>")
        digest = hashlib.sha256(body).hexdigest()[:16]
        etag = f'W/"{digest}"'

        # Check conditional request
        client_etag = request.headers.get("if-none-match", "")
        if client_etag and client_etag == etag:
            return Response(
                status_code=304,
                headers={
                    "ETag": etag,
                    "Cache-Control": f"private, max-age={ttl}",
                    "Vary": "Authorization",
                },
            )

        # Return full response with ETag headers
        new_response = Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=content_type,
        )
        new_response.headers["ETag"] = etag
        new_response.headers["Cache-Control"] = f"private, max-age={ttl}, must-revalidate"
        new_response.headers["Vary"] = "Authorization"
        new_response.headers["Last-Modified"] = _http_date()
        return new_response


def _http_date() -> str:
    """Return current time in HTTP-date format (RFC 7231)."""
    return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
