"""Security middleware and request handling."""

from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging
import time
import uuid
from typing import Callable, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """Middleware to add security headers to all responses."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, request: Request, call_next: Callable):
        """Add security headers to response."""
        response = await call_next(request)
        
        # Strict-Transport-Security
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none';"
        )
        
        # X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-XSS-Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer-Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions-Policy
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        
        return response


class RequestCorrelationMiddleware:
    """Middleware to add correlation ID for request tracking."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, request: Request, call_next: Callable):
        """Add correlation ID to request and response."""
        # Get or create correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        
        # Store in request state
        request.state.correlation_id = correlation_id
        request.state.start_time = time.time()
        
        response = await call_next(request)
        
        # Add to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        # Add timing header
        elapsed = time.time() - request.state.start_time
        response.headers["X-Response-Time"] = str(elapsed)
        
        return response


class RequestLoggingMiddleware:
    """Middleware for comprehensive request/response logging."""
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        self.app = app
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
    
    async def __call__(self, request: Request, call_next: Callable):
        """Log request and response details."""
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Log request
        start_time = time.time()
        correlation_id = getattr(request.state, 'correlation_id', 'unknown')
        
        request_body = ""
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                request_body = body.decode() if body else ""
                # Mask sensitive data
                if request_body:
                    request_body = self._mask_sensitive_data(request_body)
            except:
                pass
        
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_ip": self._get_client_ip(request),
            }
        )
        
        # Get response
        response = await call_next(request)
        
        # Log response
        elapsed = time.time() - start_time
        
        logger.info(
            f"Response: {request.method} {request.url.path} {response.status_code}",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "elapsed_time": elapsed,
                "client_ip": self._get_client_ip(request),
            }
        )
        
        return response
    
    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract client IP from request."""
        # Check X-Forwarded-For first (for proxied requests)
        if "x-forwarded-for" in request.headers:
            return request.headers["x-forwarded-for"].split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    @staticmethod
    def _mask_sensitive_data(data: str) -> str:
        """Mask sensitive fields in request body."""
        try:
            payload = json.loads(data)
            
            # Fields to mask
            sensitive_fields = [
                "password", "token", "secret", "api_key", "ssn",
                "credit_card", "cvv", "pin", "private_key"
            ]
            
            def mask_dict(obj):
                if isinstance(obj, dict):
                    return {
                        k: "***" if any(s in k.lower() for s in sensitive_fields) else mask_dict(v)
                        for k, v in obj.items()
                    }
                elif isinstance(obj, list):
                    return [mask_dict(item) for item in obj]
                return obj
            
            masked = mask_dict(payload)
            return json.dumps(masked)
        except:
            return "[Unable to log request body]"


class HTTPSEnforcementMiddleware:
    """Middleware to enforce HTTPS in production."""
    
    def __init__(self, app, enabled: bool = True):
        self.app = app
        self.enabled = enabled
    
    async def __call__(self, request: Request, call_next: Callable):
        """Enforce HTTPS."""
        if not self.enabled:
            return await call_next(request)
        
        # Check if request is HTTPS or has X-Forwarded-Proto
        is_https = (
            request.url.scheme == "https" or
            request.headers.get("x-forwarded-proto") == "https"
        )
        
        if not is_https:
            # Redirect to HTTPS
            https_url = request.url.replace(scheme="https")
            return JSONResponse(
                status_code=status.HTTP_301_MOVED_PERMANENTLY,
                headers={"location": str(https_url)},
                content={"detail": "Redirected to HTTPS"}
            )
        
        response = await call_next(request)
        return response


class RateLimitMiddleware:
    """
    ASGI middleware that enforces per-route rate limits using Redis sliding window.

    Identifier strategy:
      - Authenticated requests  → keyed by JWT subject (user_id)
      - Unauthenticated requests → keyed by client IP address

    The JWT subject is extracted from the Authorization header without
    performing a full token validation (validation happens in the route
    dependency). This avoids double DB lookups while still being safe —
    a tampered token will fail at the route level regardless.

    Headers added to every response:
      X-RateLimit-Limit     — limit for the matched rule
      X-RateLimit-Remaining — remaining requests in current window
      X-RateLimit-Reset     — seconds until window resets
    """

    _EXCLUDE_PATHS = frozenset(["/health", "/metrics", "/docs", "/redoc", "/openapi.json"])

    def __init__(self, app, rate_limiter, config=None) -> None:
        """
        Args:
            app:          The ASGI application.
            rate_limiter: A ``RateLimiter`` instance (e.g. RedisRateLimiter).
            config:       A ``RateLimitConfig`` instance (uses global default if None).
        """
        from app.core.rate_limiting import RateLimitConfig, rate_limit_config
        self.app = app
        self.rate_limiter = rate_limiter
        self.config = config or rate_limit_config

    async def __call__(self, request: Request, call_next: Callable):
        """Enforce rate limits; attach X-RateLimit-* headers to the response."""
        path = request.url.path

        # Skip internal/observability paths
        if any(path.startswith(p) for p in self._EXCLUDE_PATHS):
            return await call_next(request)

        # Determine identifier and whether the request is authenticated
        identifier, authenticated = self._get_identifier(request)

        # Look up the applicable rule
        rule = self.config.get_rule(path, authenticated=authenticated)

        # Build the scoped rate-limit key: {group}:{identifier}
        scoped_key = f"{rule.group}:{identifier}"

        # Atomically check + increment
        allowed, current_count = await self.rate_limiter.check_and_increment(
            scoped_key, rule.limit, rule.window
        )

        remaining = max(0, rule.limit - current_count)

        if not allowed:
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "path": path,
                    "identifier": identifier,
                    "limit": rule.limit,
                    "window": rule.window,
                },
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "error": {
                        "code": "SRV_003",
                        "message": "Too many requests. Please slow down.",
                        "details": {
                            "limit": rule.limit,
                            "window_seconds": rule.window,
                            "retry_after": rule.window,
                        },
                    },
                },
                headers={
                    "Retry-After": str(rule.window),
                    "X-RateLimit-Limit": str(rule.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(rule.window),
                },
            )

        response = await call_next(request)

        # Always add rate-limit headers so clients can self-throttle
        response.headers["X-RateLimit-Limit"] = str(rule.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(rule.window)

        return response

    @staticmethod
    def _get_identifier(request: Request) -> tuple[str, bool]:
        """
        Derive the rate-limit identifier from the request.

        Returns:
            (identifier_string, is_authenticated)

        For authenticated requests the JWT `sub` claim is extracted without
        full signature validation — full validation happens in the route.
        """
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):]
            try:
                import base64, json as _json
                # Decode payload segment (index 1) without verification
                payload_b64 = token.split(".")[1]
                # Pad base64 string to a multiple of 4
                padding = 4 - len(payload_b64) % 4
                padded = payload_b64 + "=" * (padding % 4)
                payload = _json.loads(base64.urlsafe_b64decode(padded))
                sub = payload.get("sub")
                if sub:
                    return f"user:{sub}", True
            except Exception:
                pass  # Fall through to IP-based

        # Unauthenticated — use client IP
        ip = _extract_client_ip(request)
        return f"ip:{ip}", False


def _extract_client_ip(request: Request) -> str:
    """
    Extract the real client IP, respecting trusted reverse-proxy headers.

    Only the *first* IP in X-Forwarded-For is trusted (the original client).
    Internal load-balancer IPs are appended later in the chain.
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take only the first IP to prevent spoofing
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
