"""
AuthLock — encapsulates account lockout logic using a CacheProvider (RedisCache).

Provides a testable, single-responsibility class to manage failed-login counters
and temporary locks using a sliding window TTL.
"""
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Defaults — align with AuthService constants
DEFAULT_FAILED_LOGIN_WINDOW = 60 * 15  # 15 minutes
DEFAULT_FAILED_LOGIN_MAX = 5


class AuthLock:
    def __init__(self, cache_provider, window: int = DEFAULT_FAILED_LOGIN_WINDOW, max_attempts: int = DEFAULT_FAILED_LOGIN_MAX):
        """Initialize with a CacheProvider-like object (must implement get/increment/delete/exists).

        Args:
            cache_provider: object with async methods get, increment, delete, exists
            window: TTL for the sliding window in seconds
            max_attempts: number of failed attempts to trigger a lock
        """
        self.cache = cache_provider
        self.window = window
        self.max_attempts = max_attempts

    def _key(self, email: str) -> str:
        return f"lockout:{email}"

    async def is_locked(self, email: str) -> bool:
        """Return True if the account identified by email is currently locked."""
        if not self.cache:
            return False
        try:
            value = await self.cache.get(self._key(email))
            if not value:
                return False
            try:
                return int(value) >= self.max_attempts
            except Exception:
                # Non-integer value — treat as locked if present
                return True
        except Exception as exc:
            logger.debug("AuthLock.is_locked: cache error for %s: %s", email, exc)
            return False

    async def record_failed_login(self, email: str) -> int:
        """Increment the failed-login counter and return the new count.

        TTL is set on first increment to create a sliding window.
        """
        if not self.cache:
            return 0
        try:
            count = await self.cache.increment(self._key(email), ttl=self.window)
            return int(count or 0)
        except Exception as exc:
            logger.debug("AuthLock.record_failed_login: cache error for %s: %s", email, exc)
            return 0

    async def clear_failed_logins(self, email: str) -> bool:
        """Clear the failed-login counter for the user (on successful auth)."""
        if not self.cache:
            return True
        try:
            return bool(await self.cache.delete(self._key(email)))
        except Exception as exc:
            logger.debug("AuthLock.clear_failed_logins: cache error for %s: %s", email, exc)
            return False
