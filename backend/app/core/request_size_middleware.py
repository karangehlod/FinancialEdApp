from starlette.types import ASGIApp, Receive, Scope, Send
from fastapi import Request, HTTPException, status
import logging

logger = logging.getLogger(__name__)

MAX_REQUEST_BODY = 1024 * 1024  # 1 MiB default; configurable via env


class RequestSizeLimitMiddleware:
    """Middleware to limit request body size to prevent large payload attacks.

    Reads the body in chunks from the receive channel and raises 413 if the
    accumulated size exceeds the configured maximum.
    """

    def __init__(self, app: ASGIApp, max_body: int = None):
        self.app = app
        self.max_body = int(max_body or MAX_REQUEST_BODY)

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def limited_receive():
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"") or b""
                more = message.get("more_body", False)
                if len(body) > self.max_body:
                    logger.warning("Request body too large: %d bytes", len(body))
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Request body too large")
                if not more:
                    return message
                # If more_body, accumulate until threshold
                chunks = [body]
                size = len(body)
                while more:
                    message = await receive()
                    chunk = message.get("body", b"") or b""
                    more = message.get("more_body", False)
                    size += len(chunk)
                    if size > self.max_body:
                        logger.warning("Request body too large during streaming: %d bytes", size)
                        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Request body too large")
                    chunks.append(chunk)
                # Reconstruct a single message for downstream app
                full = b"".join(chunks)
                return {"type": "http.request", "body": full, "more_body": False}
            return message

        await self.app(scope, limited_receive, send)
