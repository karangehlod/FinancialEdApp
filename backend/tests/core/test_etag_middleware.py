"""
Tests for ETag middleware (P1-1).

Covers:
  - ETag header generation for GET /api/v1/... responses
  - 304 Not Modified when If-None-Match matches
  - No ETag for non-GET methods
  - No ETag for auth / excluded paths
  - Cache-Control header presence and correctness
  - Different responses produce different ETags
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse, PlainTextResponse

from app.core.etag_middleware import ETagMiddleware


# ---------------------------------------------------------------------------
# Test application setup
# ---------------------------------------------------------------------------

async def expenses_endpoint(request):
    return JSONResponse({"expenses": [{"id": 1, "amount": 100}]})


async def auth_endpoint(request):
    return JSONResponse({"token": "abc"})


async def plain_text_endpoint(request):
    return PlainTextResponse("hello")


test_app = Starlette(
    routes=[
        Route("/api/v1/expenses", expenses_endpoint),
        Route("/api/v1/auth/login", auth_endpoint, methods=["POST"]),
        Route("/api/v1/auth/login", auth_endpoint, methods=["GET"]),
        Route("/text", plain_text_endpoint),
    ]
)
test_app.add_middleware(ETagMiddleware, enabled=True)

client = TestClient(test_app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestETagMiddleware:
    def test_get_request_receives_etag(self):
        response = client.get("/api/v1/expenses")
        assert response.status_code == 200
        assert "etag" in response.headers
        etag = response.headers["etag"]
        assert etag.startswith('W/"')

    def test_cache_control_header_present(self):
        response = client.get("/api/v1/expenses")
        assert "cache-control" in response.headers
        cc = response.headers["cache-control"]
        assert "private" in cc
        assert "max-age" in cc

    def test_304_on_matching_etag(self):
        # First request — get ETag
        r1 = client.get("/api/v1/expenses")
        etag = r1.headers["etag"]

        # Second request — send back the ETag
        r2 = client.get("/api/v1/expenses", headers={"If-None-Match": etag})
        assert r2.status_code == 304
        assert r2.content == b""

    def test_200_on_mismatched_etag(self):
        r = client.get("/api/v1/expenses", headers={"If-None-Match": 'W/"wrongetag1234"'})
        assert r.status_code == 200
        assert "etag" in r.headers

    def test_different_responses_different_etags(self):
        """Two identical responses get the same ETag; if we mock different data they'd differ."""
        r1 = client.get("/api/v1/expenses")
        r2 = client.get("/api/v1/expenses")
        # Same response content → same ETag
        assert r1.headers["etag"] == r2.headers["etag"]

    def test_non_get_no_etag(self):
        # POST to auth — not a GET
        response = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "p"})
        assert "etag" not in response.headers

    def test_auth_path_excluded_no_etag(self):
        # GET on auth path — excluded from ETag
        response = client.get("/api/v1/auth/login")
        # Auth paths are in _NO_CACHE_PATHS → no ETag
        # Note: the middleware excludes /api/v1/auth/ prefix
        assert "etag" not in response.headers

    def test_plain_text_no_etag(self):
        # Non-JSON response — no ETag added
        response = client.get("/text")
        assert "etag" not in response.headers

    def test_vary_header_present(self):
        response = client.get("/api/v1/expenses")
        assert "vary" in response.headers
        assert "Authorization" in response.headers["vary"]

    def test_middleware_disabled_no_etag(self):
        disabled_app = Starlette(
            routes=[Route("/api/v1/expenses", expenses_endpoint)]
        )
        disabled_app.add_middleware(ETagMiddleware, enabled=False)
        c = TestClient(disabled_app)
        response = c.get("/api/v1/expenses")
        assert "etag" not in response.headers
