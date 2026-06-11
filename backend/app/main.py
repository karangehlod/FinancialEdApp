"""
FastAPI application entry point — production-grade configuration.

Startup sequence (via lifespan):
  1. Validate DB + Redis connectivity
  2. Initialise singleton providers (PasswordHasher, TokenProvider)
  3. Initialise Redis client + RedisCache + CacheService
  4. Initialise RedisRateLimiter
  5. Register all middleware (rate-limit, correlation, metrics, security)
  6. Mount routers

Middleware execution order (outermost → innermost):
  CORS → HTTPS → SecurityHeaders → Correlation → Metrics → Logging → RateLimit → Router
"""

import os
import time
import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.exceptions import AppException
from app.core.error_handlers import (
    app_exception_handler,
    validation_exception_handler,
    general_exception_handler,
)
from app.core.middleware import (
    HTTPSEnforcementMiddleware,
    RateLimitMiddleware,
)
from app.core.metrics import MetricsMiddleware, get_metrics_endpoint
from app.core.etag_middleware import ETagMiddleware

# ---------------------------------------------------------------------------
# Logging — initialise before anything else
# ---------------------------------------------------------------------------
setup_logging(level=logging.INFO, json_format=True)
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Router imports
# ---------------------------------------------------------------------------
from app.api.v1.auth import router as auth_router
from app.api.v1.expenses import router as expenses_router
from app.api.v1.budgets import router as budgets_router
from app.api.v1.loans import router as loans_router
from app.api.v1.goals import router as goals_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.exports import router as exports_router
from app.api.v1.enums import router as enums_router
from app.api.v1.health import router as health_router
from app.api.v1.two_factor import router as two_factor_router    # P2-3: TOTP 2FA
from app.api.v1.websocket import router as websocket_router      # P2-4: WebSocket notifications
from app.api.v1.gdpr import router as gdpr_router                # P2-5: GDPR compliance
from app.api.v1.oauth import router as oauth_router              # P2-6: OAuth / Social Login
from app.api.v1.admin import router as admin_router              # P2-8: Admin dashboard
from app.api.v1.chat import router as chat_router                # P3-1: AI Chat

# ---------------------------------------------------------------------------
# Model imports — ensures SQLAlchemy registers all table metadata
# ---------------------------------------------------------------------------
from app.models.user import User
from app.models.budget import Budget, BudgetAlert, FinancialProfile
from app.models.expense import Expense
from app.db.models.data import Goal, RecurringExpense, IncomeSource, Notification
from app.db.models.auth import OAuthAccount  # P2-6: ensures OAuth table is registered
from app.db.session import auth_engine, data_engine, AuthBase, DataBase


# ---------------------------------------------------------------------------
# Application lifespan — manages all singleton resources
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager.

    Replaces the deprecated @app.on_event("startup") / ("shutdown") pattern.
    All singletons are initialised here and stored on app.state so that
    FastAPI dependency functions can access them without module-level globals.
    """
    logger.info("=== Application startup: initialising resources ===")

    # ------------------------------------------------------------------
    # Skip heavy checks during automated testing
    # ------------------------------------------------------------------
    is_testing = bool(os.getenv("PYTEST_CURRENT_TEST") or os.getenv("TESTING"))

    if not is_testing:
        from app.startup_checks import perform_startup_checks

        checks_passed = await perform_startup_checks(verify_schema=False)
        if not checks_passed:
            logger.warning(
                "Startup checks failed; continuing so the app can still boot and expose health endpoints"
            )

    # ------------------------------------------------------------------
    # Singleton providers  (P0-7: created once, shared across all requests)
    # ------------------------------------------------------------------
    from app.core.provider_implementations import BcryptPasswordHasher, JWTTokenProvider
    app.state.password_hasher = BcryptPasswordHasher(rounds=12)
    app.state.token_provider = JWTTokenProvider(
        secret_key=settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
        access_token_expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_token_expire_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )
    logger.info("Auth providers initialised (password hasher, token provider)")

    # ------------------------------------------------------------------
    # Redis client + cache service  (P0-3)
    # ------------------------------------------------------------------
    from redis import asyncio as aioredis
    from app.core.provider_implementations import RedisCache
    from app.core.cache_service import CacheService, NullCacheService
    from app.core.rate_limiting import RedisRateLimiter

    redis_client = None
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            retry_on_timeout=True,
            max_connections=50,
        )
        await redis_client.ping()
        redis_cache = RedisCache(redis_client)
        app.state.redis_client = redis_client
        app.state.redis_cache = redis_cache
        app.state.cache_service = CacheService(redis_cache)
        app.state.rate_limiter = RedisRateLimiter(redis_client)
        logger.info("Redis initialised successfully")
    except Exception as exc:
        logger.error("Redis unavailable (%s) — cache and rate limiting disabled", exc)
        app.state.redis_client = None
        app.state.redis_cache = None
        app.state.cache_service = NullCacheService()
        app.state.rate_limiter = None

    # Expose cache to the dependencies module (backward compat)
    from app.dependencies import set_redis_cache
    await set_redis_cache(app.state.redis_cache)

    # ------------------------------------------------------------------
    # Chat service — initialise with Redis for multi-worker history
    # ------------------------------------------------------------------
    try:
        from app.services.chat.chat_service import init_chat_service
        chat_svc = init_chat_service(redis_client=app.state.redis_client)
        logger.info(
            "ChatService initialised (agent=%s, redis=%s)",
            "ready" if chat_svc.is_available else "unavailable",
            "yes" if app.state.redis_client else "no (in-memory fallback)",
        )
    except Exception as exc:
        logger.error("ChatService setup failed: %s", exc)
        # logger.warning("ChatService setup failed (non-fatal): %s", exc)

    # ------------------------------------------------------------------
    # OpenTelemetry — P1-4: distributed tracing + auto-instrumentation
    # ------------------------------------------------------------------
    try:
        from app.core.telemetry import setup_telemetry
        setup_telemetry(app)
        logger.info("OpenTelemetry tracing initialised")
    except Exception as exc:
        logger.warning("OpenTelemetry setup failed (non-fatal): %s", exc)

    # ------------------------------------------------------------------
    # Multi-currency service — P2-7
    # ------------------------------------------------------------------
    try:
        from app.services.currency_service import get_currency_service
        app.state.currency_service = get_currency_service(
            cache=app.state.redis_cache,
        )
        logger.info("Currency service initialised")
    except Exception as exc:
        logger.warning("Currency service setup failed (non-fatal): %s", exc)
        app.state.currency_service = None

    # ------------------------------------------------------------------
    # WebSocket notification pub/sub manager — P2-4
    # ------------------------------------------------------------------
    pubsub_manager = None
    if redis_client:
        try:
            from app.core.websocket_manager import get_pubsub_manager
            pubsub_manager = get_pubsub_manager(redis_url=settings.REDIS_URL)
            if pubsub_manager:
                await pubsub_manager.start()
                app.state.pubsub_manager = pubsub_manager
                logger.info("WebSocket Pub/Sub manager started")
        except Exception as exc:
            logger.warning("WebSocket Pub/Sub setup failed (non-fatal): %s", exc)

    logger.info("=== Application ready to serve requests ===")

    # ------------------------------------------------------------------
    # Yield — application serves requests here
    # ------------------------------------------------------------------
    yield

    # ------------------------------------------------------------------
    # Shutdown — graceful cleanup
    # ------------------------------------------------------------------
    logger.info("=== Application shutdown: cleaning up resources ===")

    # Stop WebSocket Pub/Sub manager
    if pubsub_manager:
        await pubsub_manager.stop()
        logger.info("WebSocket Pub/Sub manager stopped")

    if redis_client:
        await redis_client.aclose()
        logger.info("Redis connection closed")

    from app.db.session import dispose_engines
    await dispose_engines()
    logger.info("=== Shutdown complete ===")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    description=(
        "Financial Education API — Budget Management, Expense Tracking, "
        "Loan Management & Analytics. Production-grade with 1M+ user support."
    ),
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
    # Disable automatic slash redirects (307) which strip CORS headers on
    # cross-origin requests from the frontend, causing "No Access-Control-
    # Allow-Origin" errors.  Routes should accept both /path and /path/.
    redirect_slashes=False,
)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# ---------------------------------------------------------------------------
# Middleware stack  (registered in reverse order — last registered = outermost)
# ---------------------------------------------------------------------------

# 1. CORS (outermost — must come before any custom middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=[
        "X-Correlation-ID",
        "X-Response-Time",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    ],
)

# 2. HTTPS enforcement (production only)
if settings.ENVIRONMENT == "production":
    app.add_middleware(HTTPSEnforcementMiddleware, enabled=True)

# 3. ETag / conditional GET — P1-1
app.add_middleware(ETagMiddleware, enabled=True)


# ---------------------------------------------------------------------------
# HTTP middleware — executed in order they are defined (first defined = outermost)
# ---------------------------------------------------------------------------

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add comprehensive security headers to every response."""
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    # Tightened CSP: removed 'unsafe-inline' from script-src
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "  # inline styles needed for UI frameworks
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self';"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
    )
    return response


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Attach a correlation ID to every request and response."""
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    request.state.start_time = time.monotonic()

    response = await call_next(request)

    elapsed_ms = (time.monotonic() - request.state.start_time) * 1000
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"
    return response


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Collect Prometheus metrics for every request."""
    _EXCLUDE = frozenset(["/metrics", "/health", "/docs", "/redoc", "/openapi.json"])
    if any(request.url.path.startswith(p) for p in _EXCLUDE):
        return await call_next(request)

    from app.core.metrics import REQUEST_COUNT, REQUEST_DURATION, ACTIVE_REQUESTS

    endpoint = request.url.path
    method = request.method
    ACTIVE_REQUESTS.labels(method=method, endpoint=endpoint).inc()
    start = time.monotonic()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration = time.monotonic() - start
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status_code).inc()
        ACTIVE_REQUESTS.labels(method=method, endpoint=endpoint).dec()


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log all non-health requests with method, path, status, and duration."""
    _EXCLUDE = frozenset(["/health", "/metrics", "/docs", "/redoc", "/openapi.json"])
    if any(request.url.path.startswith(p) for p in _EXCLUDE):
        return await call_next(request)

    correlation_id = getattr(request.state, "correlation_id", "unknown")
    logger.info(
        "Incoming request",
        extra={
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
        },
    )
    response = await call_next(request)
    logger.info(
        "Request completed",
        extra={
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
        },
    )
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """
    Apply per-route rate limiting using the Redis sliding-window limiter.

    The rate_limiter is stored on app.state during lifespan startup.
    If Redis is unavailable, the limiter is None and requests pass through.
    """
    rate_limiter = getattr(request.app.state, "rate_limiter", None)
    if rate_limiter is None:
        # Redis unavailable — fail open
        return await call_next(request)

    # Delegate to the proper middleware class
    middleware = RateLimitMiddleware(app=None, rate_limiter=rate_limiter)
    return await middleware(request, call_next)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health_router)
app.include_router(auth_router,          prefix=settings.API_V1_PREFIX)
app.include_router(expenses_router,      prefix=settings.API_V1_PREFIX)
app.include_router(budgets_router,       prefix=settings.API_V1_PREFIX)
app.include_router(loans_router,         prefix=settings.API_V1_PREFIX)
app.include_router(goals_router,         prefix=settings.API_V1_PREFIX)
app.include_router(notifications_router, prefix=settings.API_V1_PREFIX)
app.include_router(exports_router,       prefix=settings.API_V1_PREFIX)
app.include_router(enums_router,         prefix=settings.API_V1_PREFIX)
app.include_router(two_factor_router,    prefix=settings.API_V1_PREFIX)   # P2-3
app.include_router(gdpr_router,          prefix=settings.API_V1_PREFIX)   # P2-5
app.include_router(oauth_router,         prefix=settings.API_V1_PREFIX)   # P2-6
app.include_router(admin_router,         prefix=settings.API_V1_PREFIX)   # P2-8
app.include_router(chat_router,          prefix=settings.API_V1_PREFIX)   # P3-1
# WebSocket router mounts at root level (no API version prefix)
app.include_router(websocket_router)                                       # P2-4


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------

@app.get("/", tags=["Root"])
async def root():
    """API root — returns version and available feature list."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.ENVIRONMENT != "production" else "disabled",
        "health": "/health/live",
        "readiness": "/health/ready",            "features": [
            "JWT Authentication with Refresh Tokens",
            "TOTP Two-Factor Authentication (P2-3)",
            "OAuth / Social Login — Google & Apple (P2-6)",
            "RBAC Authorization",
            "Expense Tracking & Categorisation",
            "Budget Management with Real-time Alerts",
            "Loan Management & EMI Calculation",
            "Spending Analytics & Insights",
            "Financial Goals Tracking",
            "Multi-Currency Real-Time Conversion (P2-7)",
            "Redis Sliding-Window Rate Limiting",
            "Redis Cache (Cache-Aside Pattern)",
            "WebSocket Real-time Notifications (P2-4)",
            "Prometheus Metrics & Observability",
            "Structured JSON Logging + Correlation IDs",
            "Production Connection Pooling + PgBouncer Ready (P2-9)",
            "GDPR Data Export & Account Deletion (P2-5)",
            "Admin Dashboard API (P2-8)",
            "AI-Powered Financial Advisor Chat (P3-1)",
        ],
    }


# ---------------------------------------------------------------------------
# Metrics endpoint — restricted to internal network + optional Basic auth
# ---------------------------------------------------------------------------

@app.get("/metrics", tags=["Observability"], include_in_schema=False)
async def metrics(request: Request):
    """
    Prometheus metrics scrape endpoint.

    Protection layers (applied in order):
      1. IP allowlist — only internal/private IPs in production.
      2. Optional HTTP Basic auth — if METRICS_USERNAME / METRICS_PASSWORD
         are set in config, require credentials on every scrape.

    In Kubernetes, additionally protect this via a NetworkPolicy that only
    allows traffic from the Prometheus namespace.
    """
    if settings.ENVIRONMENT == "production":
        from app.core.middleware import _extract_client_ip
        client_ip = _extract_client_ip(request)
        allowed_prefixes = ("10.", "172.", "127.", "::1", "fd")
        if not any(client_ip.startswith(p) for p in allowed_prefixes):
            from fastapi.responses import JSONResponse
            from fastapi import status as http_status
            return JSONResponse(
                status_code=http_status.HTTP_403_FORBIDDEN,
                content={"detail": "Metrics endpoint restricted to internal network"},
            )

    # Optional HTTP Basic auth (set METRICS_USERNAME + METRICS_PASSWORD in env)
    metrics_user = getattr(settings, "METRICS_USERNAME", "")
    metrics_pass = getattr(settings, "METRICS_PASSWORD", "")
    if metrics_user and metrics_pass:
        import base64
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Basic "):
            return Response(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="metrics"'},
                content=b"Unauthorized",
            )
        try:
            decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
            req_user, req_pass = decoded.split(":", 1)
        except Exception:
            req_user, req_pass = "", ""
        if req_user != metrics_user or req_pass != metrics_pass:
            return Response(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="metrics"'},
                content=b"Unauthorized",
            )

    metrics_output = get_metrics_endpoint()
    return Response(content=metrics_output, media_type="text/plain")


@app.get("/health", tags=["Health"], include_in_schema=False)
async def health_check():
    """Simple liveness check — returns 200 if the process is running."""
    return {"status": "healthy", "version": settings.APP_VERSION}
