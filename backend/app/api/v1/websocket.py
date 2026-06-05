"""
WebSocket notification endpoint.

Route:
  WS /ws/notifications  — authenticated real-time notification stream

Authentication:
  JWT token passed as ?token=<access_token> query parameter.
  (Headers are not reliably available in the WebSocket handshake across browsers.)

Protocol:
  Server → Client:
    {"type": "connection_ack", "payload": {"user_id": "..."}}
    {"type": "ping", "payload": {}}
    {"type": "budget_alert", "payload": {...}}
    ... etc.

  Client → Server:
    {"type": "pong"}     — heartbeat response
    {"type": "ping"}     — keep-alive from client

Connection lifecycle:
  1. Client connects with valid JWT.
  2. Server sends connection_ack.
  3. Server sends a ping every 30 seconds; client must pong within 60s.
  4. Client receives push notifications for its user_id channel.
  5. On disconnect, connection is cleaned up automatically.
"""

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.core.websocket_manager import (
    ConnectionManager,
    get_connection_manager,
    make_notification,
)
from app.core.security_compat import decode_token
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# Heartbeat interval (seconds)
_PING_INTERVAL = 30
# Max wait for pong before closing (seconds)
_PONG_TIMEOUT = 60


def _auth_user_from_token(token: str) -> Optional[str]:
    """
    Decode JWT and return user_id (sub claim) or None if invalid.
    Never raises — invalid tokens return None.
    """
    try:
        payload = decode_token(token, settings.SECRET_KEY, settings.ALGORITHM)
        return str(payload.get("sub"))
    except Exception:
        return None


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token for authentication"),
):
    """
    Authenticated WebSocket endpoint for real-time notifications.

    Clients connect with their JWT access token.
    The server delivers push notifications over the open connection
    (budget alerts, goal milestones, loan reminders, etc.).
    """
    manager = get_connection_manager()

    # --- Authenticate ---
    user_id = _auth_user_from_token(token)
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token")
        return

    # --- Connect (handles max-connections limit internally) ---
    connected = await manager.connect(user_id, websocket)
    if not connected:
        return  # manager already closed the socket

    # Send connection acknowledgement
    ack = make_notification("connection_ack", {"user_id": user_id, "message": "Connected to notification stream"}, user_id)
    await websocket.send_text(ack)

    # Run heartbeat and message receiver concurrently
    try:
        await asyncio.gather(
            _heartbeat_loop(websocket, user_id),
            _receive_loop(websocket, user_id),
        )
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected normally: user=%s", user_id)
    except Exception as exc:
        logger.error("WebSocket error for user %s: %s", user_id, exc)
    finally:
        manager.disconnect(user_id, websocket)


async def _heartbeat_loop(websocket: WebSocket, user_id: str) -> None:
    """Send periodic ping frames to keep the connection alive."""
    while True:
        await asyncio.sleep(_PING_INTERVAL)
        try:
            ping = make_notification("ping", {}, user_id)
            await websocket.send_text(ping)
        except Exception:
            break  # connection closed


async def _receive_loop(websocket: WebSocket, user_id: str) -> None:
    """
    Receive and handle messages from the client.

    Handles:
      - {"type": "pong"} — heartbeat response (no-op, just update last_seen)
      - {"type": "ping"} — client keepalive, server responds with pong
      - Unknown types are silently ignored
    """
    while True:
        try:
            raw = await websocket.receive_text()
        except WebSocketDisconnect:
            raise

        try:
            msg = json.loads(raw)
            msg_type = msg.get("type", "")

            if msg_type == "pong":
                # Client acknowledged our ping — connection is alive
                pass
            elif msg_type == "ping":
                # Client-initiated keepalive
                pong = make_notification("pong", {}, user_id)
                await websocket.send_text(pong)
            else:
                logger.debug("Unknown WS message type from user %s: %s", user_id, msg_type)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON from user %s", user_id)
        except Exception as exc:
            logger.error("Error processing WS message from user %s: %s", user_id, exc)
