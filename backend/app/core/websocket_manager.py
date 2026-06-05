"""
WebSocket notification manager with Redis Pub/Sub backend.

Architecture:
  ┌─────────────────────────────────────────────────────────┐
  │  Client (WS)  ←──────────────  FastAPI WS Handler       │
  │                                      ↑                  │
  │                                Redis Pub/Sub             │
  │                                      ↑                  │
  │  Worker / Service  ──────→  publish(channel, message)   │
  └─────────────────────────────────────────────────────────┘

Channel naming:
  notifications:{user_id}   — per-user events
  notifications:broadcast   — system-wide announcements

Supported event types:
  budget_alert      — budget spending threshold crossed
  goal_milestone    — savings goal reached/milestone hit
  loan_reminder     — upcoming loan payment
  expense_added     — new expense recorded (by sync/import)
  system_notice     — platform-wide message
  connection_ack    — sent on WS connect to confirm auth
  ping              — heartbeat from server (client should pong)

Security:
  - JWT auth required; token passed as ?token=... query param
  - No raw WebSocket without valid token
  - User can only subscribe to their own channel
  - Rate limiting: max 2 concurrent WS connections per user
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Notification message schema
# ---------------------------------------------------------------------------

def make_notification(
    event_type: str,
    payload: Dict[str, Any],
    user_id: Optional[str] = None,
) -> str:
    """Build a JSON notification message string."""
    return json.dumps({
        "type": event_type,
        "user_id": user_id,
        "payload": payload,
    })


# ---------------------------------------------------------------------------
# Connection Manager — tracks all active WebSocket connections
# ---------------------------------------------------------------------------

class ConnectionManager:
    """
    In-memory registry of active WebSocket connections, keyed by user_id.

    For multi-pod deployments this alone is insufficient — every pod has its own
    in-memory registry.  The Redis Pub/Sub subscriber (below) bridges pods by
    publishing messages to Redis; each pod's subscriber then delivers them to
    its local sockets.
    """

    def __init__(self) -> None:
        # user_id (str) → set of WebSocket objects
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._max_per_user = 2  # prevent socket exhaustion

    async def connect(self, user_id: str, ws: WebSocket) -> bool:
        """
        Accept and register a WebSocket connection.

        Returns False if the user has too many connections (rate limit).
        """
        current = self._connections.get(user_id, set())
        if len(current) >= self._max_per_user:
            logger.warning(
                "User %s exceeded max WS connections (%d)", user_id, self._max_per_user
            )
            await ws.close(code=1008, reason="Too many connections")
            return False

        await ws.accept()
        if user_id not in self._connections:
            self._connections[user_id] = set()
        self._connections[user_id].add(ws)
        logger.info("WS connected: user=%s, total=%d", user_id, self.total_connections)
        return True

    def disconnect(self, user_id: str, ws: WebSocket) -> None:
        """Remove a connection from the registry."""
        connections = self._connections.get(user_id, set())
        connections.discard(ws)
        if not connections:
            self._connections.pop(user_id, None)
        logger.info("WS disconnected: user=%s", user_id)

    async def send_to_user(self, user_id: str, message: str) -> int:
        """
        Send a message to all WebSocket connections for a given user.

        Returns the number of connections the message was sent to.
        """
        connections = list(self._connections.get(user_id, set()))
        sent = 0
        dead: list[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_text(message)
                sent += 1
            except Exception as exc:
                logger.debug("Dead WS connection for user %s: %s", user_id, exc)
                dead.append(ws)
        # Clean up dead connections
        for ws in dead:
            self.disconnect(user_id, ws)
        return sent

    async def broadcast(self, message: str) -> int:
        """Send a message to ALL connected users."""
        total = 0
        for user_id in list(self._connections.keys()):
            total += await self.send_to_user(user_id, message)
        return total

    @property
    def total_connections(self) -> int:
        return sum(len(c) for c in self._connections.values())

    @property
    def connected_users(self) -> int:
        return len(self._connections)


# ---------------------------------------------------------------------------
# Redis Pub/Sub Subscriber — bridges messages across pods
# ---------------------------------------------------------------------------

class RedisPubSubManager:
    """
    Subscribes to Redis channels and routes messages to local WebSocket connections.

    Run as a background task via asyncio.  Each pod runs one subscriber that
    listens on all user channels.  When a worker publishes a notification, this
    subscriber receives it and calls connection_manager.send_to_user().
    """

    BROADCAST_CHANNEL = "notifications:broadcast"

    def __init__(
        self,
        connection_manager: ConnectionManager,
        redis_url: str,
    ) -> None:
        self._manager = connection_manager
        self._redis_url = redis_url
        self._running = False
        self._pubsub = None
        self._redis = None

    async def start(self) -> None:
        """Start the background Pub/Sub listener."""
        self._running = True
        asyncio.create_task(self._listen())
        logger.info("Redis Pub/Sub notification listener started")

    async def stop(self) -> None:
        """Gracefully stop the listener."""
        self._running = False
        if self._pubsub:
            try:
                await self._pubsub.unsubscribe()
                await self._pubsub.close()
            except Exception:
                pass
        if self._redis:
            try:
                await self._redis.aclose()
            except Exception:
                pass

    async def _listen(self) -> None:
        """Main listener loop — reconnects on failure."""
        from redis import asyncio as aioredis

        while self._running:
            try:
                self._redis = aioredis.from_url(
                    self._redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                self._pubsub = self._redis.pubsub()
                # Subscribe to the broadcast channel and all user channels (pattern)
                await self._pubsub.psubscribe(
                    self.BROADCAST_CHANNEL,
                    "notifications:*",
                )
                logger.info("Subscribed to Redis notification channels")

                async for raw in self._pubsub.listen():
                    if not self._running:
                        break
                    if raw["type"] not in ("message", "pmessage"):
                        continue
                    await self._route_message(raw)

            except Exception as exc:
                logger.error("Pub/Sub listener error: %s — reconnecting in 5s", exc)
                await asyncio.sleep(5)

    async def _route_message(self, raw: dict) -> None:
        """Route a raw Redis Pub/Sub message to the appropriate WebSocket(s)."""
        channel: str = raw.get("channel", "")
        data: str = raw.get("data", "")

        if not data:
            return

        if channel == self.BROADCAST_CHANNEL:
            n = await self._manager.broadcast(data)
            logger.debug("Broadcast delivered to %d connections", n)
        elif channel.startswith("notifications:"):
            user_id = channel.removeprefix("notifications:")
            n = await self._manager.send_to_user(user_id, data)
            logger.debug("Notification delivered to user %s (%d sockets)", user_id, n)


# ---------------------------------------------------------------------------
# Publishing helper — called by services / workers
# ---------------------------------------------------------------------------

async def publish_notification(
    redis_client: Any,
    user_id: str,
    event_type: str,
    payload: Dict[str, Any],
) -> None:
    """
    Publish a notification to a user's Redis channel.

    This is the primary API used by services (budget alerts, goal milestones, etc.)
    to push real-time notifications to connected clients.
    """
    if redis_client is None:
        logger.debug("Redis not available — skipping notification publish")
        return
    channel = f"notifications:{user_id}"
    message = make_notification(event_type, payload, user_id)
    try:
        await redis_client.publish(channel, message)
        logger.debug("Published %s to channel %s", event_type, channel)
    except Exception as exc:
        logger.error("Failed to publish notification: %s", exc)


async def broadcast_notification(
    redis_client: Any,
    event_type: str,
    payload: Dict[str, Any],
) -> None:
    """Broadcast a system-wide notification to all connected clients."""
    if redis_client is None:
        return
    message = make_notification(event_type, payload)
    try:
        await redis_client.publish(RedisPubSubManager.BROADCAST_CHANNEL, message)
    except Exception as exc:
        logger.error("Failed to broadcast notification: %s", exc)


# ---------------------------------------------------------------------------
# Application-level singletons
# ---------------------------------------------------------------------------

_connection_manager: Optional[ConnectionManager] = None
_pubsub_manager: Optional[RedisPubSubManager] = None


def get_connection_manager() -> ConnectionManager:
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager


def get_pubsub_manager(redis_url: Optional[str] = None) -> Optional[RedisPubSubManager]:
    global _pubsub_manager
    if _pubsub_manager is None and redis_url:
        _pubsub_manager = RedisPubSubManager(get_connection_manager(), redis_url)
    return _pubsub_manager
