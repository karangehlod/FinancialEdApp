"""
Redis-backed conversation history store for the chat service.

Stores per-conversation message lists in Redis so that conversation
state is shared across multiple Uvicorn workers and survives restarts.

Falls back to an in-memory dict when Redis is unavailable.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Optional
from datetime import datetime as _dt

from langchain_core.messages import AIMessage, HumanMessage

from app.config import settings

logger = logging.getLogger(__name__)

# Redis key prefix for chat conversations
_KEY_PREFIX = "chat:conv:"
# TTL for conversation data (24 hours)
_CONV_TTL_SECONDS = 86_400


def _serialize_messages(messages: list) -> str:
    """Serialize LangChain messages to JSON for Redis storage, including timestamps."""
    data = []
    for m in messages:
        ts = getattr(m, 'timestamp', None) or _dt.utcnow().isoformat()
        if isinstance(m, HumanMessage):
            data.append({"role": "user", "content": m.content, "ts": ts})
        elif isinstance(m, AIMessage):
            data.append({"role": "assistant", "content": m.content, "ts": ts})
    return json.dumps(data)


def _deserialize_messages(raw: str) -> list:
    """Deserialize JSON back to LangChain message objects, preserving timestamps on the message objects."""
    data = json.loads(raw)
    messages = []
    for item in data:
        ts = item.get('ts')
        if item["role"] == "user":
            m = HumanMessage(content=item["content"])
            try:
                setattr(m, 'timestamp', ts)
            except Exception:
                pass
            messages.append(m)
        elif item["role"] == "assistant":
            m = AIMessage(content=item["content"])
            try:
                setattr(m, 'timestamp', ts)
            except Exception:
                pass
            messages.append(m)
    return messages


class ConversationStore:
    """
    Abstract-ish conversation store.

    Uses Redis when a client is provided; otherwise falls back to a
    plain in-memory defaultdict (single-worker only).
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._memory: dict[str, list] = defaultdict(list)
        # in-memory mapping for user -> set of conv ids (fallback)
        self._memory_user_convs: dict[str, set] = defaultdict(set)
        if self._redis:
            logger.info("ConversationStore using Redis backend")
        else:
            logger.warning("ConversationStore using in-memory backend (single-worker only)")

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    async def get_history(self, conversation_id: str) -> list:
        """Return the message list for a conversation."""
        if self._redis:
            try:
                raw = await self._redis.get(f"{_KEY_PREFIX}{conversation_id}")
                if raw:
                    return _deserialize_messages(raw)
                return []
            except Exception as exc:
                logger.warning("Redis read failed for conv %s: %s", conversation_id, exc)
                # Fall through to in-memory
        return list(self._memory.get(conversation_id, []))

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    async def save_history(self, conversation_id: str, messages: list) -> None:
        """Persist the full message list for a conversation."""
        if self._redis:
            try:
                raw = _serialize_messages(messages)
                await self._redis.set(
                    f"{_KEY_PREFIX}{conversation_id}",
                    raw,
                    ex=_CONV_TTL_SECONDS,
                )
                # also write a small meta record with last message and timestamp
                last_content = None
                last_ts = None
                if messages:
                    last = messages[-1]
                    # LangChain messages have .content
                    last_content = getattr(last, 'content', None)
                    last_ts = getattr(last, 'timestamp', _dt.utcnow().isoformat())

                # Determine a title: prefer existing stored title, otherwise use first human message
                title = None
                try:
                    raw_meta = await self._redis.get(f"{_KEY_PREFIX}{conversation_id}:meta")
                    if raw_meta:
                        existing = json.loads(raw_meta)
                        title = existing.get('title')
                except Exception:
                    title = None

                if not title and messages:
                    # find first user message
                    first_user = next((m for m in messages if isinstance(m, HumanMessage)), None)
                    if first_user:
                        txt = getattr(first_user, 'content', '') or ''
                        title = (txt.strip()[:120]).rstrip()

                meta = {"last": last_content, "ts": last_ts, "title": title}
                await self._redis.set(f"{_KEY_PREFIX}{conversation_id}:meta", json.dumps(meta), ex=_CONV_TTL_SECONDS)
                return
            except Exception as exc:
                logger.warning("Redis write failed for conv %s: %s", conversation_id, exc)
        # Fallback to memory
        self._memory[conversation_id] = messages
        # also update in-memory meta
        mem = getattr(self, '_memory_conversation_meta', None)
        if mem is None:
            self._memory_conversation_meta = {}
            mem = self._memory_conversation_meta
        last_content = None
        last_ts = None
        if messages:
            last = messages[-1]
            last_content = getattr(last, 'content', None)
            last_ts = getattr(last, 'timestamp', _dt.utcnow().isoformat())
        # Determine title for in-memory meta as well, preferring existing
        existing_title = mem.get(conversation_id, {}).get('title') if mem.get(conversation_id) else None
        title = existing_title
        if not title and messages:
            first_user = next((m for m in messages if isinstance(m, HumanMessage)), None)
            if first_user:
                txt = getattr(first_user, 'content', '') or ''
                title = (txt.strip()[:120]).rstrip()
        mem[conversation_id] = {"last": last_content, "ts": last_ts, "title": title}

    async def get_conversation_meta(self, conversation_id: str) -> dict:
        """Return stored meta for a conversation (last message preview and timestamp)."""
        if self._redis:
            try:
                raw = await self._redis.get(f"{_KEY_PREFIX}{conversation_id}:meta")
                if raw:
                    return json.loads(raw)
                return {}
            except Exception as exc:
                logger.warning("Redis get meta failed for conv %s: %s", conversation_id, exc)
        # Fallback to memory
        mem = getattr(self, '_memory_conversation_meta', None)
        if mem is None:
            return {}
        return dict(mem.get(conversation_id, {}))

    async def set_conversation_meta(self, conversation_id: str, meta: dict) -> None:
        """Persist conversation meta (used for flags like pending_consent)."""
        if self._redis:
            try:
                await self._redis.set(f"{_KEY_PREFIX}{conversation_id}:meta", json.dumps(meta), ex=_CONV_TTL_SECONDS)
                return
            except Exception as exc:
                logger.warning("Redis set meta failed for conv %s: %s", conversation_id, exc)
        # Fallback to memory
        mem = getattr(self, '_memory_conversation_meta', None)
        if mem is None:
            self._memory_conversation_meta = {}
            mem = self._memory_conversation_meta
        mem[conversation_id] = meta

    # ------------------------------------------------------------------
    # User-scoped conversation helpers
    # ------------------------------------------------------------------
    async def add_user_conversation(self, user_id: str, conversation_id: str) -> None:
        """Record that a conversation belongs to a user."""
        key = f"chat:user:{user_id}:convs"
        if self._redis:
            try:
                await self._redis.sadd(key, conversation_id)
                # Optionally set TTL on the set to match conversation TTL
                await self._redis.expire(key, _CONV_TTL_SECONDS)
                return
            except Exception as exc:
                logger.warning("Redis SADD failed for user %s: %s", user_id, exc)
        # Fallback to memory
        self._memory_user_convs.setdefault(user_id, set()).add(conversation_id)

    async def list_user_conversations(self, user_id: str) -> list[str]:
        """Return conversation IDs belonging to a user."""
        key = f"chat:user:{user_id}:convs"
        if self._redis:
            try:
                members = await self._redis.smembers(key)
                # redis client may return bytes; convert to str
                return [m.decode() if isinstance(m, (bytes, bytearray)) else str(m) for m in members]
            except Exception as exc:
                logger.warning("Redis SMEMBERS failed for user %s: %s", user_id, exc)
        # Fallback to memory
        return list(self._memory_user_convs.get(user_id, set()))

    async def remove_user_conversation(self, user_id: str, conversation_id: str) -> None:
        """Remove conversation association for a user."""
        key = f"chat:user:{user_id}:convs"
        if self._redis:
            try:
                await self._redis.srem(key, conversation_id)
                return
            except Exception as exc:
                logger.warning("Redis SREM failed for user %s: %s", user_id, exc)
        # Fallback to memory
        if user_id in self._memory_user_convs:
            self._memory_user_convs[user_id].discard(conversation_id)

    # ------------------------------------------------------------------
    # List conversation IDs (best-effort)
    # ------------------------------------------------------------------
    async def list_conversations(self) -> list[str]:
        """Return known conversation IDs."""
        if self._redis:
            try:
                keys = []
                async for key in self._redis.scan_iter(match=f"{_KEY_PREFIX}*", count=200):
                    keys.append(key.removeprefix(_KEY_PREFIX))
                return keys
            except Exception as exc:
                logger.warning("Redis scan failed: %s", exc)
        return list(self._memory.keys())

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------
    async def delete_conversation(self, conversation_id: str) -> None:
        """Remove a conversation from the store and delete any meta."""
        if self._redis:
            try:
                await self._redis.delete(f"{_KEY_PREFIX}{conversation_id}")
                await self._redis.delete(f"{_KEY_PREFIX}{conversation_id}:meta")
            except Exception as exc:
                logger.warning("Redis delete failed for conv %s: %s", conversation_id, exc)
        self._memory.pop(conversation_id, None)
        mem = getattr(self, '_memory_conversation_meta', None)
        if mem:
            mem.pop(conversation_id, None)

    # ------------------------------------------------------------------
    # User preferences
    # ------------------------------------------------------------------
    async def set_user_pref(self, user_id: str, key: str, value) -> None:
        """Save a JSON-serialisable preference value for a user."""
        pref_key = f"chat:user:{user_id}:prefs"
        if self._redis:
            try:
                # store as a JSON object; use HSET for individual fields if available
                raw = await self._redis.get(pref_key)
                data = json.loads(raw) if raw else {}
                data[key] = value
                await self._redis.set(pref_key, json.dumps(data))
                return
            except Exception as exc:
                logger.warning("Redis set_user_pref failed for user %s: %s", user_id, exc)
        # Fallback to memory
        mem = getattr(self, '_memory_user_prefs', None)
        if mem is None:
            self._memory_user_prefs = defaultdict(dict)
            mem = self._memory_user_prefs
        mem.setdefault(user_id, {})[key] = value

    async def get_user_prefs(self, user_id: str) -> dict:
        """Return stored preferences for a user (dict)."""
        pref_key = f"chat:user:{user_id}:prefs"
        if self._redis:
            try:
                raw = await self._redis.get(pref_key)
                if raw:
                    return json.loads(raw)
                return {}
            except Exception as exc:
                logger.warning("Redis get_user_prefs failed for user %s: %s", user_id, exc)
        # Fallback to memory
        mem = getattr(self, '_memory_user_prefs', None)
        if mem is None:
            return {}
        return dict(mem.get(user_id, {}))
