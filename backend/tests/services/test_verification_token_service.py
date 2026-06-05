"""
Tests for VerificationTokenService (P1-2).

Covers:
  - Token creation (email verification + password reset)
  - Token consumption (valid, expired, already-used, wrong purpose)
  - Rate limiting enforcement
"""

import hashlib
import pytest
from datetime import timedelta
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from app.services.verification_token_service import VerificationTokenService
from app.core.exceptions import AuthenticationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _make_token_provider(token: str = "fake.token.value", payload: dict = None):
    """Return a mock TokenProvider that returns a predictable token and payload."""
    tp = MagicMock()
    tp.create_access_token = MagicMock(return_value=token)
    tp.decode_token = MagicMock(return_value=payload or {
        "sub": str(uuid4()),
        "purpose": "email_verify",
        "exp": 9999999999,
    })
    return tp


def _make_cache(stored_value: Optional[str] = "some-user-id"):
    """Return a mock CacheProvider."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=stored_value)
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    cache.increment = AsyncMock()
    return cache


# ---------------------------------------------------------------------------
# Test: create_verification_token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_verification_token_returns_token():
    user_id = uuid4()
    token = "header.payload.sig"
    tp = _make_token_provider(token=token)

    # Cache reports no existing rate-limit counter
    cache = _make_cache(stored_value=None)
    svc = VerificationTokenService(token_provider=tp, cache=cache)

    result = await svc.create_verification_token(user_id, "user@example.com")

    assert result == token
    tp.create_access_token.assert_called_once()
    # Verify the token hash was stored in Redis
    cache.set.assert_called_once()
    args = cache.set.call_args[0]
    assert args[0].startswith("email_verify:")
    assert args[1] == str(user_id)


@pytest.mark.asyncio
async def test_create_password_reset_token_returns_token():
    user_id = uuid4()
    token = "header.payload.sig2"
    tp = _make_token_provider(token=token)

    cache = _make_cache(stored_value=None)
    svc = VerificationTokenService(token_provider=tp, cache=cache)

    result = await svc.create_password_reset_token(user_id, "user@example.com")

    assert result == token
    cache.set.assert_called_once()
    args = cache.set.call_args[0]
    assert args[0].startswith("pwd_reset:")


# ---------------------------------------------------------------------------
# Test: rate limiting
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rate_limit_blocks_after_max_requests():
    user_id = uuid4()
    tp = _make_token_provider()

    # Cache reports count = 3 (at the limit)
    cache = _make_cache(stored_value="3")
    svc = VerificationTokenService(token_provider=tp, cache=cache)

    with pytest.raises(AuthenticationError, match="Too many"):
        await svc.create_verification_token(user_id, "user@example.com")


@pytest.mark.asyncio
async def test_rate_limit_allows_under_max():
    user_id = uuid4()
    tp = _make_token_provider()

    # Cache reports count = 2 (below limit of 3)
    cache = _make_cache(stored_value="2")
    svc = VerificationTokenService(token_provider=tp, cache=cache)

    # Should NOT raise
    token = await svc.create_verification_token(user_id, "user@example.com")
    assert token is not None


# ---------------------------------------------------------------------------
# Test: consume_verification_token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_consume_verification_token_valid():
    user_id = uuid4()
    token = "valid.token.here"
    payload = {"sub": str(user_id), "purpose": "email_verify", "exp": 9999999999}
    tp = _make_token_provider(token=token, payload=payload)

    # Cache has the token hash stored
    cache = _make_cache(stored_value=str(user_id))
    svc = VerificationTokenService(token_provider=tp, cache=cache)

    result = await svc.consume_verification_token(token)

    assert result == user_id
    cache.delete.assert_called_once()


@pytest.mark.asyncio
async def test_consume_verification_token_already_used():
    user_id = uuid4()
    token = "used.token.here"
    payload = {"sub": str(user_id), "purpose": "email_verify", "exp": 9999999999}
    tp = _make_token_provider(token=token, payload=payload)

    # Cache returns None (token already deleted = already consumed)
    cache = _make_cache(stored_value=None)
    svc = VerificationTokenService(token_provider=tp, cache=cache)

    with pytest.raises(AuthenticationError, match="already been used"):
        await svc.consume_verification_token(token)


@pytest.mark.asyncio
async def test_consume_verification_token_wrong_purpose():
    user_id = uuid4()
    token = "wrong.purpose.token"
    # Token has pwd_reset purpose but we're calling consume_verification_token
    payload = {"sub": str(user_id), "purpose": "pwd_reset", "exp": 9999999999}
    tp = _make_token_provider(token=token, payload=payload)

    cache = _make_cache(stored_value=str(user_id))
    svc = VerificationTokenService(token_provider=tp, cache=cache)

    with pytest.raises(AuthenticationError, match="Wrong token purpose"):
        await svc.consume_verification_token(token)


@pytest.mark.asyncio
async def test_consume_verification_token_invalid_jwt():
    user_id = uuid4()
    tp = MagicMock()
    tp.decode_token = MagicMock(side_effect=Exception("JWT decode failed"))

    cache = _make_cache()
    svc = VerificationTokenService(token_provider=tp, cache=cache)

    with pytest.raises(AuthenticationError, match="Invalid or expired token"):
        await svc.consume_verification_token("bad.token")


# ---------------------------------------------------------------------------
# Test: consume_password_reset_token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_consume_password_reset_token_valid():
    user_id = uuid4()
    token = "reset.token.here"
    payload = {"sub": str(user_id), "purpose": "pwd_reset", "exp": 9999999999}
    tp = _make_token_provider(token=token, payload=payload)

    cache = _make_cache(stored_value=str(user_id))
    svc = VerificationTokenService(token_provider=tp, cache=cache)

    result = await svc.consume_password_reset_token(token)

    assert result == user_id
    cache.delete.assert_called_once()


@pytest.mark.asyncio
async def test_consume_password_reset_token_already_used():
    user_id = uuid4()
    token = "used.reset.token"
    payload = {"sub": str(user_id), "purpose": "pwd_reset", "exp": 9999999999}
    tp = _make_token_provider(token=token, payload=payload)

    cache = _make_cache(stored_value=None)
    svc = VerificationTokenService(token_provider=tp, cache=cache)

    with pytest.raises(AuthenticationError, match="already been used"):
        await svc.consume_password_reset_token(token)
