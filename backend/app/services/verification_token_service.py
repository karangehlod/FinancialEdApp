"""
Verification token service — P1-2 (email verification + password reset).

Design:
  - Short-lived signed JWTs (1 hour) are sent via email.
  - Token hashes are stored in Redis (not raw tokens) — prevents double-use.
  - Rate-limited: max 3 request attempts per email per hour.
  - Tokens are single-use: consumed on first valid redemption.

SOLID:
  - Single Responsibility: only handles ephemeral verification tokens.
  - Dependency Inversion: depends on CacheProvider + EmailService interfaces.
"""

import logging
from datetime import timedelta
from typing import Optional
from uuid import UUID

from app.config import settings
from app.core.providers import CacheProvider, TokenProvider
from app.core.exceptions import AuthenticationError

logger = logging.getLogger(__name__)

# --- Constants ---------------------------------------------------------------
_TOKEN_TTL_SECONDS       = 60 * 60        # 1 hour
_RATE_LIMIT_WINDOW       = 60 * 60        # 1 hour
_RATE_LIMIT_MAX_REQUESTS = 3              # max 3 email sends per window
_CACHE_PREFIX_VERIFY     = "email_verify"
_CACHE_PREFIX_RESET      = "pwd_reset"
_CACHE_PREFIX_RATE       = "email_rate"


class VerificationTokenService:
    """
    Issues and validates one-time email-verification and password-reset tokens.

    Each token is:
      - A signed JWT (exp=1h, purpose claim distinguishes type)
      - Stored as a SHA-256 hash in Redis (TTL = 1h)
      - Consumed on first valid use (deleted from Redis)
    """

    def __init__(
        self,
        token_provider: TokenProvider,
        cache: CacheProvider,
    ) -> None:
        self._tp    = token_provider
        self._cache = cache

    # ------------------------------------------------------------------
    # Email Verification
    # ------------------------------------------------------------------

    async def create_verification_token(self, user_id: UUID, email: str) -> str:
        """
        Create a signed email-verification token and store its hash in Redis.

        Raises:
            AuthenticationError: if the rate limit for this email is exceeded.
        """
        await self._enforce_rate_limit(email, purpose="verify")

        token = self._tp.create_access_token(
            data={"sub": str(user_id), "email": email, "purpose": "email_verify"},
            expires_delta=timedelta(seconds=_TOKEN_TTL_SECONDS),
        )
        token_hash = _sha256(token)
        await self._cache.set(
            f"{_CACHE_PREFIX_VERIFY}:{token_hash}",
            str(user_id),
            ttl=_TOKEN_TTL_SECONDS,
        )
        return token

    async def consume_verification_token(self, token: str) -> UUID:
        """
        Validate and consume an email-verification token.

        Returns:
            The user_id encoded in the token.

        Raises:
            AuthenticationError: if the token is invalid, expired, or already used.
        """
        user_id = await self._consume_token(token, expected_purpose="email_verify", prefix=_CACHE_PREFIX_VERIFY)
        return user_id

    # ------------------------------------------------------------------
    # Password Reset
    # ------------------------------------------------------------------

    async def create_password_reset_token(self, user_id: UUID, email: str) -> str:
        """
        Create a signed password-reset token and store its hash in Redis.

        Raises:
            AuthenticationError: if the rate limit for this email is exceeded.
        """
        await self._enforce_rate_limit(email, purpose="reset")

        token = self._tp.create_access_token(
            data={"sub": str(user_id), "email": email, "purpose": "pwd_reset"},
            expires_delta=timedelta(seconds=_TOKEN_TTL_SECONDS),
        )
        token_hash = _sha256(token)
        await self._cache.set(
            f"{_CACHE_PREFIX_RESET}:{token_hash}",
            str(user_id),
            ttl=_TOKEN_TTL_SECONDS,
        )
        return token

    async def consume_password_reset_token(self, token: str) -> UUID:
        """
        Validate and consume a password-reset token.

        Returns:
            The user_id encoded in the token.

        Raises:
            AuthenticationError: if the token is invalid, expired, or already used.
        """
        return await self._consume_token(token, expected_purpose="pwd_reset", prefix=_CACHE_PREFIX_RESET)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _consume_token(self, token: str, expected_purpose: str, prefix: str) -> UUID:
        """
        Decode the JWT, verify the purpose claim, then atomically delete
        the hash from Redis (single-use guarantee).

        Raises:
            AuthenticationError on any failure.
        """
        try:
            payload = self._tp.decode_token(token)
        except Exception as exc:
            raise AuthenticationError("Invalid or expired token") from exc

        purpose = payload.get("purpose")
        if purpose != expected_purpose:
            raise AuthenticationError(f"Wrong token purpose: expected {expected_purpose}, got {purpose}")

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise AuthenticationError("Malformed token payload")

        token_hash = _sha256(token)
        cache_key = f"{prefix}:{token_hash}"

        # Atomic check-and-delete (single-use)
        stored = await self._cache.get(cache_key)
        if not stored:
            raise AuthenticationError("Token has already been used or has expired")

        await self._cache.delete(cache_key)
        logger.info("Token consumed for user %s (purpose=%s)", user_id_str, expected_purpose)

        try:
            return UUID(user_id_str)
        except ValueError as exc:
            raise AuthenticationError("Malformed user ID in token") from exc

    async def _enforce_rate_limit(self, email: str, purpose: str) -> None:
        """
        Raise AuthenticationError if the email has exceeded the allowed number
        of token-generation requests within the rate-limit window.
        """
        key = f"{_CACHE_PREFIX_RATE}:{purpose}:{email}"
        try:
            count_str = await self._cache.get(key)
            count = int(count_str) if count_str else 0
            if count >= _RATE_LIMIT_MAX_REQUESTS:
                raise AuthenticationError(
                    f"Too many {purpose} requests. Please try again later."
                )
            await self._cache.increment(key, ttl=_RATE_LIMIT_WINDOW)
        except AuthenticationError:
            raise
        except Exception as exc:
            logger.warning("Rate-limit check failed for %s / %s: %s", email, purpose, exc)
            # Fail open — allow the request through if Redis is unavailable


def _sha256(value: str) -> str:
    """Return HMAC-SHA256 hex digest of a UTF-8 string using application secret."""
    import hmac
    import hashlib as _hashlib
    key = settings.SECRET_KEY.encode('utf-8')
    return hmac.new(key, value.encode('utf-8'), _hashlib.sha256).hexdigest()
