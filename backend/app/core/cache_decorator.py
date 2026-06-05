"""
Lightweight async cache decorator for service methods.

Usage:

@cache_response(ttl=CacheTTL.EXPENSE_LIST, key_func=expense_list_key, serializer=serialize_expenses)
async def get_user_expenses(...):
    ...

The decorator expects the decorated function to be an instance method where `self` has
an attribute `_cache` implementing the CacheService interface. If `_cache` is None
(or is a NullCacheService), the original function is called directly.

The `key_func` receives the same arguments as the wrapped function (including `self`) and
must return a string cache key.

The `serializer`, if provided, is a callable that accepts the function result and
returns a JSON-serialisable representation that will be stored in Redis. The raw
result is returned to the caller (the service code receives original SQLAlchemy
models, etc.).
"""
from __future__ import annotations

import asyncio
import functools
import hashlib
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional

from app.core.cache import compute_etag
from app.core.cache_service import CacheKey, CacheTTL

KeyFunc = Callable[..., str]
Serializer = Optional[Callable[[Any], Any]]


def cache_response(ttl: int, key_func: KeyFunc, serializer: Optional[Callable[[Any], Any]] = None, deserializer: Optional[Callable[[Any], Any]] = None, serializer_attr: Optional[str] = None, deserializer_attr: Optional[str] = None, namespace: Optional[str] = None):
    """Decorator factory for caching service method responses.

    New: `namespace` identifies metadata namespace (e.g. 'expenses', 'budgets', 'goals').
    When set, the decorator will write ETag/Last-Modified metadata via the
    service's CacheService (if present) after successfully setting the cache.
    """

    def _resolve_callable(instance, cb, attr_name):
        if cb:
            return cb
        if attr_name:
            return getattr(instance, attr_name)
        return None

    def decorator(func: Callable[..., Awaitable[Any]]):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Expect instance method: self is args[0]
            if not args:
                result = func(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    return await result
                return result

            self = args[0]
            cache_service = getattr(self, "_cache", None)

            # Resolve serializer/deserializer for this instance
            ser = _resolve_callable(self, serializer, serializer_attr)
            deser = _resolve_callable(self, deserializer, deserializer_attr)

            # If no cache service present, run original function and return raw result
            if cache_service is None:
                result = func(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result
                return result

            try:
                key = key_func(*args, **kwargs)
            except Exception:
                # If key generation fails, fall back to direct call
                result = func(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result
                return result

            # Try cache get
            try:
                cached = await cache_service.get(key)
            except Exception:
                cached = None

            if cached is not None:
                # Reconstruct original return value using deserializer if provided
                try:
                    if deser:
                        return deser(cached)
                    return cached
                except Exception:
                    # If deserialization fails, fall back to loader
                    pass

            # Cache miss — call the original function to get the real object
            result = func(*args, **kwargs)
            if asyncio.iscoroutine(result):
                result = await result

            # Store serialized copy if serializer available
            try:
                to_store = ser(result) if ser else result
                await cache_service.set(key, to_store, ttl=ttl)

                # Write metadata (ETag / Last-Modified) when namespace provided
                if namespace:
                    try:
                        etag = compute_etag(to_store)
                        last_modified = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
                        # Use cache_service.set_metadata if available
                        set_meta = getattr(cache_service, 'set_metadata', None)
                        if callable(set_meta):
                            await set_meta(namespace, key, etag, last_modified, ttl=ttl)
                    except Exception:
                        pass
            except Exception:
                # Non-fatal cache set failure
                pass

            return result

        return wrapper

    return decorator


# ---------------------- Key helper factories ----------------------

# These helpers now return canonical, request-like logical keys so middleware
# and cached metadata align. They intentionally accept the same arguments as
# the decorated service methods so they can be used as `key_func`.


def expense_list_key(self, user_id, skip=0, limit=50, filters=None, **kwargs) -> str:
    page = (skip // limit) if limit else 0
    filters_hash = CacheKey.hash_filters(filters or {})
    # canonical path-like key
    return f"/api/v1/expenses?user_id={user_id}&page={page}&limit={limit}&filters={filters_hash}"


def budget_list_key(self, user_id, start_date=None, end_date=None, **kwargs) -> str:
    month = (start_date or __import__('datetime').date.today()).strftime("%Y-%m")
    return f"/api/v1/budgets?user_id={user_id}&month={month}"


def goal_list_key(self, user_id, status=None, goal_type=None, **kwargs) -> str:
    qs = []
    if status:
        qs.append(f"status={status}")
    if goal_type:
        qs.append(f"goal_type={goal_type}")
    q = "&".join(qs)
    return f"/api/v1/goals?user_id={user_id}" + (f"&{q}" if q else "")
