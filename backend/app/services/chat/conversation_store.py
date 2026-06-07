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

from langchain_core.messages import AIMessage, HumanMessage

from app.config import settings

logger = logging.getLogger(__name__)

# Redis key prefix for chat conversations
_KEY_PREFIX = "chat:conv:"
# TTL for conversation data (24 hours)
_CONV_TTL_SECONDS = 86_400


def _serialize_messages(messages: list) -> str:
    """Serialize LangChain messages to JSON for Redis storage."""
    data = []
    for m in messages:
        if isinstance(m, HumanMessage):
            data.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage):
            data.append({"role": "assistant", "content": m.content})
    return json.dumps(data)


def _deserialize_messages(raw: str) -> list:
    """Deserialize JSON back to LangChain message objects."""
    data = json.loads(raw)
    messages = []
    for item in data:
        if item["role"] == "user":
            messages.append(HumanMessage(content=item["content"]))
        elif item["role"] == "assistant":
            messages.append(AIMessage(content=item["content"]))
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
                return
            except Exception as exc:
                logger.warning("Redis write failed for conv %s: %s", conversation_id, exc)
        # Fallback to memory
        self._memory[conversation_id] = messages

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
        """Remove a conversation from the store."""
        if self._redis:
            try:
                await self._redis.delete(f"{_KEY_PREFIX}{conversation_id}")
            except Exception as exc:
                logger.warning("Redis delete failed for conv %s: %s", conversation_id, exc)
        self._memory.pop(conversation_id, None)
