from __future__ import annotations

import hashlib
import json
from typing import Optional
from datetime import datetime

from app.config import settings

# NOTE: This module provides small, opinionated helpers that expect a
# Redis-like async client available at `app.state.cache`. The client is
# expected to implement `get`, `set`, `incr`, and `expire` coroutines.

CACHE_PREFIX = getattr(settings, "APP_NAME", "app").lower()


def _canonical_query_string(query_params) -> str:
    """Return a deterministic string for query params (sorted key order)."""
    if not query_params:
        return ""
    items = sorted([(k, v) for k, v in query_params.items()])
    return "&".join(f"{k}={v}" for k, v in items)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_metadata_key(namespace: str, key: str) -> str:
    """Create a compact metadata key for a namespace and logical key."""
    # Keep keys short by hashing the logical key
    h = _hash_text(key)
    return f"{CACHE_PREFIX}:meta:{namespace}:{h}"


def compute_etag(payload: object) -> str:
    """Deterministically compute a strong ETag for a JSON-serializable payload.

    Uses sorted keys to ensure consistent ETag across semantically-equal dicts.
    """
    try:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    except Exception:
        # Fallback to string representation
        canonical = str(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def get_metadata(redis_client, namespace: str, key: str) -> Optional[dict]:
    """Retrieve metadata dict (etag, last_modified) from Redis if present.

    Returns None when no metadata is found or on errors.
    """
    if not redis_client:
        return None
    try:
        meta_key = make_metadata_key(namespace, key)
        raw = await redis_client.get(meta_key)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        return json.loads(raw)
    except Exception:
        return None


async def set_metadata(redis_client, namespace: str, key: str, etag: str, last_modified: str, ttl: Optional[int] = None) -> None:
    """Store metadata JSON blob for the provided key with an optional TTL."""
    if not redis_client:
        return
    try:
        meta_key = make_metadata_key(namespace, key)
        payload = json.dumps({"etag": etag, "last_modified": last_modified})
        await redis_client.set(meta_key, payload)
        if ttl is None:
            ttl = getattr(settings, "CACHE_TTL_EXPENSES", None) or getattr(settings, "CACHE_DEFAULT_TTL", None)
        if ttl:
            # Respect TTL to avoid unbounded metadata growth
            try:
                await redis_client.expire(meta_key, int(ttl))
            except Exception:
                pass
    except Exception:
        # Swallow errors — cache is an optimization
        return


async def bump_version(redis_client, namespace: str, key: str) -> None:
    """Atomically increment a namespace+key version used by cache-keying strategies.

    Services should call this after successful DB commit for create/update/delete
    so that cached entries become stale.
    """
    if not redis_client:
        return
    try:
        version_key = f"{CACHE_PREFIX}:version:{namespace}:{_hash_text(key)}"
        await redis_client.incr(version_key)
        # Optionally set a long TTL on versions to allow GC of stale version keys
        try:
            await redis_client.expire(version_key, 60 * 60 * 24 * 30)  # 30 days
        except Exception:
            pass
    except Exception:
        return
