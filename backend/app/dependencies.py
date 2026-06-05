"""
Dependency injection for authentication, database, caching, and provider singletons.

Provider singletons (BcryptPasswordHasher, JWTTokenProvider) are stored on
``app.state`` during lifespan startup and retrieved here as FastAPI dependencies.
This eliminates the previous anti-pattern of constructing these objects on
every request — bcrypt with rounds=12 is intentionally expensive.
"""

import logging
import os
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security_compat import decode_token
from jose import JWTError
from app.db.session import get_auth_db, get_data_db
from app.db.models.auth import User
from app.core.provider_implementations import RedisCache
from app.core.cache_service import CacheService, NullCacheService

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Redis cache — sourced from app.state (no module-level mutable global)
# ---------------------------------------------------------------------------

def get_redis_cache(request: Request) -> Optional[RedisCache]:
    """
    Return the Redis cache instance stored on app.state.

    Resolves from ``app.state.cache`` which is set during lifespan startup.
    Returns None when Redis is unavailable (startup falls back to NullCacheService).
    """
    return getattr(request.app.state, "cache", None)


# ---------------------------------------------------------------------------
# Backward-compatibility shim (used by lifespan startup in main.py)
# ---------------------------------------------------------------------------

async def set_redis_cache(cache: Optional[RedisCache]) -> None:
    """
    No-op shim retained for backward compatibility with main.py startup.

    The cache is now stored on ``app.state`` directly; this function is kept
    so existing startup code does not need to change but no longer sets a
    module-level global.
    """
    # Nothing to do — the startup code already writes to app.state.cache.
    pass


# ---------------------------------------------------------------------------
# App-state provider dependencies  (P0-7: singletons, not per-request)
# ---------------------------------------------------------------------------

def get_password_hasher(request: Request):
    """
    Return the application-level BcryptPasswordHasher singleton.

    Stored on app.state during lifespan startup.
    """
    hasher = getattr(request.app.state, "password_hasher", None)
    if hasher is None:
        # If the app lifespan did not run (e.g. during unit tests) we allow
        # a lightweight fallback. In production this indicates a misconfiguration
        # so surface an explicit error to avoid creating expensive objects per-request.
        is_testing = bool(
            request.app.state.__dict__.get("TESTING")
            or request.app.state.__dict__.get("PYTEST_CURRENT_TEST")
            or os.environ.get("TESTING")
            or os.environ.get("PYTEST_CURRENT_TEST")
        )
        if not is_testing:
            raise RuntimeError("Password hasher singleton not initialised. Ensure application lifespan startup runs.")
        from app.core.provider_implementations import BcryptPasswordHasher
        # Use reduced rounds in test fallback for speed
        return BcryptPasswordHasher(rounds=4)
    return hasher


def get_token_provider(request: Request):
    """
    Return the application-level JWTTokenProvider singleton.

    Stored on app.state during lifespan startup.
    """
    provider = getattr(request.app.state, "token_provider", None)
    if provider is None:
        # See comment in get_password_hasher — do not silently create a full
        # token provider in production. Use a lightweight test provider when
        # running under tests.
        is_testing = bool(
            request.app.state.__dict__.get("TESTING")
            or request.app.state.__dict__.get("PYTEST_CURRENT_TEST")
            or os.environ.get("TESTING")
            or os.environ.get("PYTEST_CURRENT_TEST")
        )
        if not is_testing:
            raise RuntimeError("Token provider singleton not initialised. Ensure application lifespan startup runs.")
        from app.core.provider_implementations import JWTTokenProvider
        from app.config import settings
        return JWTTokenProvider(
            secret_key=settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
            access_token_expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            refresh_token_expire_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
        )
    return provider


def get_cache_service(request: Request) -> CacheService:
    """
    Return the application-level CacheService.

    Falls back to NullCacheService if Redis is unavailable.
    """
    # Prefer the unified `app.state.cache` attribute (set during lifespan startup).
    cache = getattr(request.app.state, "cache", None)
    if cache is not None:
        # If a raw provider (RedisCache) was stored we wrap it with CacheService
        # to expose the higher-level API expected by callers.
        if isinstance(cache, CacheService):
            return cache
        try:
            return CacheService(cache)
        except Exception:
            # Fallback to explicit cache_service attribute for backward compat
            pass
    return getattr(request.app.state, "cache_service", None) or NullCacheService()


# ---------------------------------------------------------------------------
# Current-user dependency  (token → User, with Redis token-user caching)
# ---------------------------------------------------------------------------

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_auth_db),
) -> User:
    """
    Validate the JWT Bearer token and return the authenticated User.

    Optimisation: after the first DB lookup, the user object is cached in
    Redis for the remainder of the access-token's lifetime so that subsequent
    requests on the same token do NOT hit the database.

    Raises:
        HTTP 401 — missing, expired, or invalid token
        HTTP 403 — account is inactive
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except (JWTError, Exception):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed user ID in token",
        )

    # ------------------------------------------------------------------
    # Cache-aside: try Redis before hitting the DB
    # ------------------------------------------------------------------
    from app.core.cache_service import CacheKey, CacheTTL

    cache_service: CacheService = get_cache_service(request)
    cache_key = CacheKey.token_user(user_id_str)

    cached_user_data = await cache_service.get(cache_key)
    if cached_user_data is not None:
        # Re-hydrate a lightweight user-like object from cached dict
        # We only need id, email, is_active, is_verified for route guards
        user = _build_user_from_cache(cached_user_data)
        if user is not None:
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Inactive user account",
                )
            return user

    # ------------------------------------------------------------------
    # DB lookup  (only on cache miss)
    # ------------------------------------------------------------------
    from app.repositories.user_repository import UserRepository

    user_repo = UserRepository(db)
    user = await user_repo.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    # Populate cache so the next request within TTL skips the DB
    await cache_service.set(
        cache_key,
        {
            "id": str(user.id),
            "email": user.email,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
        },
        ttl=CacheTTL.TOKEN_USER,
    )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Alias dependency that explicitly asserts the user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_user_from_cache(data: dict) -> Optional[User]:
    """
    Reconstruct a minimal User-like object from a cached dictionary.

    We create a real User SQLAlchemy instance so that type-checking and
    attribute access in route handlers work without modification.
    """
    try:
        user = User.__new__(User)
        user.id = uuid.UUID(data["id"])
        user.email = data["email"]
        user.is_active = data["is_active"]
        user.is_verified = data["is_verified"]
        user.password_hash = ""  # Not stored in cache — never needed post-auth
        return user
    except Exception as exc:
        logger.warning("Failed to reconstruct user from cache: %s", exc)
        return None
