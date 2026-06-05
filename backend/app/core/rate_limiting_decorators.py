"""
Rate limiting and throttling decorators - Prevent API abuse and ensure fair resource allocation.

Features:
- Per-user rate limiting
- Endpoint-specific limits
- Global rate limits
- Graceful degradation
- Retry-After header support
- Redis-based distributed counting

Usage:
    @rate_limit(requests_per_minute=60)
    async def create_expense(...):
        pass

    @rate_limit(requests_per_minute=20, name="payment_endpoints")
    async def make_payment(...):
        pass
"""

from functools import wraps
from typing import Callable, Optional
import logging
from datetime import datetime, timedelta, timezone
import asyncio

from fastapi import HTTPException, status, Request
from app.core.logging import get_logger

logger = get_logger(__name__)

# ============================================================================
# In-Memory Rate Limiter (Fallback when Redis unavailable)
# ============================================================================

class InMemoryRateLimiter:
    """Simple in-memory rate limiter for fallback scenarios."""
    
    def __init__(self):
        self.requests = {}  # {user_id: [(timestamp, endpoint), ...]}
        self.cleanup_interval = 60  # Cleanup every 60 seconds
        self.max_age = 3600  # Keep records for 1 hour
    
    async def is_allowed(
        self,
        user_id: str,
        endpoint: str,
        requests_per_minute: int
    ) -> tuple[bool, int]:
        """
        Check if request is allowed.
        
        Returns:
            (allowed: bool, remaining_requests: int)
        """
        try:
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=1)
            
            key = f"{user_id}:{endpoint}"
            if key not in self.requests:
                self.requests[key] = []
            
            # Remove old requests
            self.requests[key] = [
                (ts, ep) for ts, ep in self.requests[key]
                if ts > cutoff
            ]
            
            request_count = len(self.requests[key])
            
            if request_count >= requests_per_minute:
                return False, 0
            
            # Record this request
            self.requests[key].append((now, endpoint))
            remaining = requests_per_minute - request_count - 1
            
            return True, remaining
        except Exception as exc:
            logger.warning(f"In-memory rate limiter error: {exc}")
            # On error, allow request (graceful degradation)
            return True, requests_per_minute - 1


# Global in-memory fallback
_fallback_limiter = InMemoryRateLimiter()


# ============================================================================
# Rate Limiting Decorator
# ============================================================================

def rate_limit(
    requests_per_minute: int = 60,
    name: Optional[str] = None,
    enforce: bool = True
):
    """
    Decorator to enforce rate limiting on endpoints.

    Args:
        requests_per_minute: Number of requests allowed per minute per user
        name: Custom name for rate limit bucket (defaults to function name)
        enforce: Whether to enforce limits or just track (default: True)

    Raises:
        HTTPException: 429 Too Many Requests if limit exceeded

    Usage:
        @rate_limit(requests_per_minute=60)
        async def create_expense(...):
            pass

        @rate_limit(requests_per_minute=20, name="payments")
        async def make_payment(...):
            pass
    """
    def decorator(func: Callable) -> Callable:
        endpoint_name = name or func.__name__
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Extract request and current_user
                request = None
                current_user = None
                
                # Try to get Request from kwargs
                if 'request' in kwargs and isinstance(kwargs['request'], Request):
                    request = kwargs['request']
                
                # Try to get current_user from kwargs
                if 'current_user' in kwargs and hasattr(kwargs['current_user'], 'id'):
                    current_user = kwargs['current_user']
                
                # If request not found, try to extract from args
                if not request:
                    for arg in args:
                        if isinstance(arg, Request):
                            request = arg
                            break
                
                # If current_user not found, try to extract from args
                if not current_user:
                    for arg in args:
                        if hasattr(arg, 'id') and hasattr(arg, 'email'):
                            # Likely a User object
                            current_user = arg
                            break
                
                if not current_user:
                    logger.warning(f"Could not extract current_user from {endpoint_name}")
                    # Allow request if user cannot be identified (shouldn't happen in practice)
                    return await func(*args, **kwargs)
                
                user_id = str(current_user.id)
                rate_limit_key = f"rate_limit:{endpoint_name}:{user_id}"
                
                # Try to use Redis first
                redis_client = None
                if request and hasattr(request.app.state, 'redis_client'):
                    redis_client = request.app.state.redis_client
                
                # Check rate limit
                allowed = False
                remaining = 0
                
                if redis_client:
                    try:
                        # Use Redis for distributed rate limiting
                        allowed, remaining = await _check_redis_rate_limit(
                            redis_client,
                            rate_limit_key,
                            requests_per_minute
                        )
                    except Exception as exc:
                        logger.warning(f"Redis rate limiting failed: {exc}, falling back")
                        allowed, remaining = await _fallback_limiter.is_allowed(
                            user_id,
                            endpoint_name,
                            requests_per_minute
                        )
                else:
                    # Use in-memory fallback
                    allowed, remaining = await _fallback_limiter.is_allowed(
                        user_id,
                        endpoint_name,
                        requests_per_minute
                    )
                
                if not enforce:
                    # Just track, don't enforce
                    logger.debug(
                        f"Rate limit tracked: {user_id} on {endpoint_name}",
                        extra={"remaining": remaining}
                    )
                    return await func(*args, **kwargs)
                
                if not allowed:
                    # Rate limit exceeded
                    logger.warning(
                        f"Rate limit exceeded: {user_id} on {endpoint_name}",
                        extra={"limit": requests_per_minute}
                    )
                    
                    # Add rate limit headers to response
                    if request:
                        try:
                            request.scope["rate_limit_exceeded"] = True
                        except Exception:
                            pass
                    
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Rate limit exceeded. Maximum {requests_per_minute} requests per minute allowed.",
                        headers={"Retry-After": "60"}
                    )
                
                # Log rate limit info
                logger.debug(
                    f"Rate limit check passed: {user_id} on {endpoint_name}",
                    extra={"remaining": remaining}
                )
                
                # Call the actual endpoint
                response = await func(*args, **kwargs)
                
                # Add rate limit headers to response headers if possible
                if request and hasattr(request, 'scope'):
                    try:
                        request.scope["rate_limit_remaining"] = remaining
                        request.scope["rate_limit_limit"] = requests_per_minute
                    except Exception:
                        pass
                
                return response
                
            except HTTPException:
                raise
            except Exception as exc:
                logger.error(f"Rate limiting error in {endpoint_name}: {exc}")
                # On error, allow request (graceful degradation)
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# ============================================================================
# Redis Rate Limiter Helper
# ============================================================================

async def _check_redis_rate_limit(
    redis_client,
    rate_limit_key: str,
    requests_per_minute: int
) -> tuple[bool, int]:
    """
    Check rate limit using Redis (atomic operation).
    
    Returns:
        (allowed: bool, remaining_requests: int)
    """
    try:
        # Increment counter atomically
        current = await redis_client.incr(rate_limit_key)
        
        # Set expiration on first request
        if current == 1:
            await redis_client.expire(rate_limit_key, 60)
        
        if current > requests_per_minute:
            return False, 0
        
        remaining = requests_per_minute - current
        return True, remaining
        
    except Exception as exc:
        logger.warning(f"Redis rate limit check failed: {exc}")
        raise


# ============================================================================
# Rate Limit Header Middleware
# ============================================================================

async def add_rate_limit_headers(request: Request, call_next):
    """
    Middleware to add rate limit headers to responses.
    
    This should be added to middleware stack in main.py:
        app.middleware("http")(add_rate_limit_headers)
    """
    response = await call_next(request)
    
    try:
        # Add rate limit headers if set by rate_limit decorator
        if hasattr(request.scope, '__dict__'):
            scope_dict = request.scope.__dict__
            
            if "rate_limit_exceeded" in scope_dict and scope_dict["rate_limit_exceeded"]:
                response.headers["X-RateLimit-Exceeded"] = "true"
            
            if "rate_limit_remaining" in scope_dict:
                response.headers["X-RateLimit-Remaining"] = str(
                    scope_dict.get("rate_limit_remaining", 0)
                )
            
            if "rate_limit_limit" in scope_dict:
                response.headers["X-RateLimit-Limit"] = str(
                    scope_dict.get("rate_limit_limit", 0)
                )
    except Exception:
        pass
    
    return response


# ============================================================================
# Common Rate Limit Presets
# ============================================================================

# Rate limit presets for common scenarios
RATE_LIMITS = {
    # CRUD Operations (most restrictive)
    "create": 60,
    "update": 60,
    "delete": 60,
    
    # High-impact operations (very restrictive)
    "payment": 20,
    "transfer": 20,
    "export": 10,
    "bulk_operation": 5,
    
    # Read operations (permissive)
    "read": 300,
    "list": 300,
    "search": 300,
    "analytics": 60,
    
    # Authentication (restrictive)
    "login": 10,
    "register": 5,
    "password_reset": 3,
    "mfa": 10,
}


def apply_preset_limit(operation_type: str):
    """
    Apply a preset rate limit based on operation type.
    
    Usage:
        @apply_preset_limit("payment")
        async def make_payment(...):
            pass
    """
    if operation_type not in RATE_LIMITS:
        raise ValueError(f"Unknown operation type: {operation_type}")
    
    requests_per_minute = RATE_LIMITS[operation_type]
    
    def decorator(func: Callable) -> Callable:
        return rate_limit(requests_per_minute=requests_per_minute, name=operation_type)(func)
    
    return decorator
