"""
security_compat.py — Test-only security helper shim.

PURPOSE
-------
This module exists exclusively to support test fixtures that cannot use
FastAPI's dependency-injection mechanism (e.g., pytest conftest factories that
create JWT tokens or hashed passwords without a running application).

PRODUCTION CODE MUST NOT import from this module.
All production password and token operations go through:
  - app.core.provider_implementations.BcryptPasswordHasher  (via app.state)
  - app.core.provider_implementations.JWTTokenProvider      (via app.state)

HOW TO USE IN TESTS
-------------------
    from app.core.security_compat import hash_password_test, create_access_token_test

    # hash a password in a fixture
    hashed = hash_password_test("plaintext")

    # create a valid JWT for use in test requests
    token = create_access_token_test({"sub": str(user.id)})
"""

from datetime import timedelta
from typing import Optional

from app.config import settings
from app.core.provider_implementations import BcryptPasswordHasher, JWTTokenProvider

# ---------------------------------------------------------------------------
# Shared low-cost instances for tests  (rounds=4 keeps bcrypt fast in CI)
# ---------------------------------------------------------------------------
_TEST_HASHER = BcryptPasswordHasher(rounds=4)
_TEST_TOKEN_PROVIDER = JWTTokenProvider(
    secret_key=settings.SECRET_KEY,
    algorithm=settings.ALGORITHM,
    access_token_expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    refresh_token_expire_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt (fast, test-only rounds=4).

    Aliased as ``hash_password`` to allow drop-in replacement of the old
    ``app.core.security.hash_password`` in test files.
    """
    return _TEST_HASHER.hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return _TEST_HASHER.verify_password(plain_password, hashed_password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token for test fixtures.

    Aliased as ``create_access_token`` to allow drop-in replacement of the old
    ``app.core.security.create_access_token`` in test files.
    """
    return _TEST_TOKEN_PROVIDER.create_access_token(data, expires_delta)


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token for test fixtures."""
    return _TEST_TOKEN_PROVIDER.create_refresh_token(data)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token.

    Aliased as ``decode_token`` to allow drop-in replacement of the old
    ``app.core.security.decode_token`` in test files and in the two
    production callsites being migrated:
      - app.dependencies (decode_token for HTTP Bearer validation)
      - app.api.v1.websocket (decode_token for WS auth)

    Raises HTTPException(401) on any invalid/expired/malformed token so that
    callers (tests and production code alike) get a consistent exception type.
    """
    from fastapi import HTTPException, status
    from jose import JWTError

    try:
        return _TEST_TOKEN_PROVIDER.decode_token(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
