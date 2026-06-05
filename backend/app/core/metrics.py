"""Prometheus metrics and observability setup."""

from prometheus_client import (
    Counter, Histogram, Gauge, CollectorRegistry, generate_latest
)
from fastapi import Request, Response
from fastapi.responses import Response as FastAPIResponse
import time
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Create a custom registry to avoid conflicts
REGISTRY = CollectorRegistry()

# Request metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=REGISTRY
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=REGISTRY,
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

REQUEST_SIZE = Histogram(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint'],
    registry=REGISTRY
)

RESPONSE_SIZE = Histogram(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint', 'status'],
    registry=REGISTRY
)

# Application metrics
ACTIVE_REQUESTS = Gauge(
    'http_requests_active',
    'Active HTTP requests',
    ['method', 'endpoint'],
    registry=REGISTRY
)

ERROR_COUNT = Counter(
    'application_errors_total',
    'Total application errors',
    ['error_type', 'operation'],
    registry=REGISTRY
)

# Database metrics
DB_QUERY_DURATION = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'table'],
    registry=REGISTRY,
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

DB_POOL_SIZE = Gauge(
    'db_pool_size',
    'Database connection pool size',
    ['pool_name'],
    registry=REGISTRY
)

DB_POOL_CHECKEDOUT = Gauge(
    'db_pool_checkedout',
    'Checked out database connections',
    ['pool_name'],
    registry=REGISTRY
)

# Cache metrics
CACHE_HIT = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type'],
    registry=REGISTRY
)

CACHE_MISS = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type'],
    registry=REGISTRY
)

CACHE_SIZE = Gauge(
    'cache_size_bytes',
    'Cache size in bytes',
    ['cache_type'],
    registry=REGISTRY
)

# Business metrics
EXPENSE_COUNT = Counter(
    'expense_created_total',
    'Total expenses created',
    ['currency'],
    registry=REGISTRY
)

EXPENSE_AMOUNT = Histogram(
    'expense_amount_dollars',
    'Expense amount in dollars',
    ['category'],
    registry=REGISTRY
)

BUDGET_COUNT = Counter(
    'budget_created_total',
    'Total budgets created',
    registry=REGISTRY
)

GOAL_COUNT = Counter(
    'goal_created_total',
    'Total goals created',
    registry=REGISTRY
)


class MetricsMiddleware:
    """Middleware to collect HTTP metrics."""
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        self.app = app
        self.exclude_paths = exclude_paths or ["/metrics", "/health", "/docs", "/redoc"]
    
    async def __call__(self, scope, receive, send):
        """Collect metrics for the request using ASGI interface."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extract path from scope
        path = scope.get("path", "")
        
        # Skip metrics for excluded paths
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            await self.app(scope, receive, send)
            return
        
        # Get endpoint name (remove query params)
        endpoint = path.split('?')[0]
        method = scope.get("method", "")
        
        # Increment active requests
        ACTIVE_REQUESTS.labels(
            method=method,
            endpoint=endpoint
        ).inc()
        
        # Measure request duration
        start_time = time.time()
        status_code = 200
        
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
            
            # Record metrics
            duration = time.time() - start_time
            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status=status_code
            ).inc()
            
        except Exception as e:
            logger.error(f"Error in metrics middleware: {e}")
            raise
        
        finally:
            # Decrement active requests
            ACTIVE_REQUESTS.labels(
                method=method,
                endpoint=endpoint
            ).dec()


def get_metrics_endpoint():
    """
    Return the Prometheus metrics in text format.
    
    This should be exposed as a /metrics endpoint.
    """
    return generate_latest(REGISTRY).decode('utf-8')


def record_database_query(operation: str, table: str, duration: float) -> None:
    """Record a database query metric."""
    DB_QUERY_DURATION.labels(
        operation=operation,
        table=table
    ).observe(duration)


def record_cache_hit(cache_type: str) -> None:
    """Record a cache hit."""
    CACHE_HIT.labels(cache_type=cache_type).inc()


def record_cache_miss(cache_type: str) -> None:
    """Record a cache miss."""
    CACHE_MISS.labels(cache_type=cache_type).inc()


def record_error(error_type: str, operation: str) -> None:
    """Record an application error."""
    ERROR_COUNT.labels(
        error_type=error_type,
        operation=operation
    ).inc()


def record_expense(amount: float, currency: str, category: str) -> None:
    """Record an expense creation metric."""
    EXPENSE_COUNT.labels(currency=currency).inc()
    EXPENSE_AMOUNT.labels(category=category).observe(amount)


def update_db_pool_metrics(pool_name: str, pool_size: int, checkedout: int) -> None:
    """Update database pool metrics."""
    DB_POOL_SIZE.labels(pool_name=pool_name).set(pool_size)
    DB_POOL_CHECKEDOUT.labels(pool_name=pool_name).set(checkedout)
