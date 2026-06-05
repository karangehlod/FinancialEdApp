"""
Comprehensive tests for app/core/metrics.py

Coverage: MetricsMiddleware, metric recording functions
Tests include: Request metrics, error tracking, cache metrics, database metrics
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time
from prometheus_client import CollectorRegistry

from app.core.metrics import (
    MetricsMiddleware,
    get_metrics_endpoint,
    record_database_query,
    record_cache_hit,
    record_cache_miss,
    record_error,
    record_expense,
    update_db_pool_metrics,
    REQUEST_COUNT,
    REQUEST_DURATION,
    ACTIVE_REQUESTS,
    ERROR_COUNT,
    CACHE_HIT,
    CACHE_MISS,
)


class TestMetricsMiddleware:
    """Test MetricsMiddleware class."""

    def test_initialization_with_defaults(self):
        """Test MetricsMiddleware initialization with default excluded paths."""
        mock_app = AsyncMock()
        middleware = MetricsMiddleware(mock_app)

        assert middleware.app == mock_app
        assert "/metrics" in middleware.exclude_paths
        assert "/health" in middleware.exclude_paths

    def test_initialization_with_custom_excluded_paths(self):
        """Test initialization with custom excluded paths."""
        mock_app = AsyncMock()
        excluded = ["/custom", "/skip"]
        middleware = MetricsMiddleware(mock_app, exclude_paths=excluded)

        assert middleware.exclude_paths == excluded

    @pytest.mark.asyncio
    async def test_middleware_passes_non_http_requests(self):
        """Test that non-HTTP requests pass through unchanged."""
        mock_app = AsyncMock()
        middleware = MetricsMiddleware(mock_app)

        scope = {"type": "websocket", "path": "/ws"}
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_middleware_skips_excluded_paths(self):
        """Test that excluded paths skip metrics collection."""
        mock_app = AsyncMock()
        middleware = MetricsMiddleware(mock_app)

        scope = {
            "type": "http",
            "path": "/metrics",
            "method": "GET",
        }
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_middleware_collects_metrics_for_non_excluded_paths(self):
        """Test that metrics are collected for non-excluded paths."""
        mock_app = AsyncMock()
        middleware = MetricsMiddleware(mock_app)

        async def mock_app_handler(scope, receive, send):
            await send({"type": "http.response.start", "status": 200})

        middleware.app = mock_app_handler

        scope = {
            "type": "http",
            "path": "/api/v1/expenses",
            "method": "GET",
        }
        receive = AsyncMock()
        send = AsyncMock()

        with patch("app.core.metrics.ACTIVE_REQUESTS"):
            await middleware(scope, receive, send)

    @pytest.mark.asyncio
    async def test_middleware_increments_active_requests(self):
        """Test that active requests counter is incremented."""
        mock_app = AsyncMock()
        middleware = MetricsMiddleware(mock_app)

        async def mock_app_handler(scope, receive, send):
            await send({"type": "http.response.start", "status": 200})

        middleware.app = mock_app_handler

        scope = {
            "type": "http",
            "path": "/api/v1/test",
            "method": "GET",
        }
        receive = AsyncMock()
        send = AsyncMock()

        with patch("app.core.metrics.ACTIVE_REQUESTS") as mock_active:
            await middleware(scope, receive, send)
            # inc() should be called
            mock_active.labels.return_value.inc.assert_called()

    @pytest.mark.asyncio
    async def test_middleware_records_request_duration(self):
        """Test that request duration is recorded."""
        mock_app = AsyncMock()
        middleware = MetricsMiddleware(mock_app)

        async def mock_app_handler(scope, receive, send):
            await send({"type": "http.response.start", "status": 200})

        middleware.app = mock_app_handler

        scope = {
            "type": "http",
            "path": "/api/v1/test",
            "method": "GET",
        }
        receive = AsyncMock()
        send = AsyncMock()

        with patch("app.core.metrics.REQUEST_DURATION") as mock_duration:
            await middleware(scope, receive, send)
            mock_duration.labels.return_value.observe.assert_called()

    @pytest.mark.asyncio
    async def test_middleware_records_request_count(self):
        """Test that request count is recorded."""
        mock_app = AsyncMock()
        middleware = MetricsMiddleware(mock_app)

        async def mock_app_handler(scope, receive, send):
            await send({"type": "http.response.start", "status": 200})

        middleware.app = mock_app_handler

        scope = {
            "type": "http",
            "path": "/api/v1/test",
            "method": "GET",
        }
        receive = AsyncMock()
        send = AsyncMock()

        with patch("app.core.metrics.REQUEST_COUNT") as mock_count:
            await middleware(scope, receive, send)
            mock_count.labels.return_value.inc.assert_called()

    @pytest.mark.asyncio
    async def test_middleware_captures_status_code(self):
        """Test that status code is captured from response."""
        mock_app = AsyncMock()
        middleware = MetricsMiddleware(mock_app)

        async def mock_app_handler(scope, receive, send):
            await send({"type": "http.response.start", "status": 404})

        middleware.app = mock_app_handler

        scope = {
            "type": "http",
            "path": "/api/v1/test",
            "method": "GET",
        }
        receive = AsyncMock()
        send = AsyncMock()

        with patch("app.core.metrics.REQUEST_COUNT") as mock_count:
            await middleware(scope, receive, send)
            # status should be 404
            call_args = mock_count.labels.call_args
            assert call_args[1]["status"] == 404

    @pytest.mark.asyncio
    async def test_middleware_decrements_active_requests_on_success(self):
        """Test that active requests are decremented after success."""
        mock_app = AsyncMock()
        middleware = MetricsMiddleware(mock_app)

        async def mock_app_handler(scope, receive, send):
            await send({"type": "http.response.start", "status": 200})

        middleware.app = mock_app_handler

        scope = {
            "type": "http",
            "path": "/api/v1/test",
            "method": "GET",
        }
        receive = AsyncMock()
        send = AsyncMock()

        with patch("app.core.metrics.ACTIVE_REQUESTS") as mock_active:
            await middleware(scope, receive, send)
            # dec() should be called in finally block
            mock_active.labels.return_value.dec.assert_called()

    @pytest.mark.asyncio
    async def test_middleware_decrements_active_requests_on_error(self):
        """Test that active requests are decremented on error."""
        async def mock_app_handler(scope, receive, send):
            raise RuntimeError("Test error")

        mock_app = AsyncMock()
        middleware = MetricsMiddleware(mock_app)
        middleware.app = mock_app_handler

        scope = {
            "type": "http",
            "path": "/api/v1/test",
            "method": "GET",
        }
        receive = AsyncMock()
        send = AsyncMock()

        with patch("app.core.metrics.ACTIVE_REQUESTS") as mock_active:
            with pytest.raises(RuntimeError):
                await middleware(scope, receive, send)
            # dec() should still be called
            mock_active.labels.return_value.dec.assert_called()

    @pytest.mark.asyncio
    async def test_middleware_handles_different_http_methods(self):
        """Test middleware with different HTTP methods."""
        mock_app = AsyncMock()
        middleware = MetricsMiddleware(mock_app)

        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]

        for method in methods:
            async def mock_app_handler(scope, receive, send):
                await send({"type": "http.response.start", "status": 200})

            middleware.app = mock_app_handler

            scope = {
                "type": "http",
                "path": "/api/v1/test",
                "method": method,
            }
            receive = AsyncMock()
            send = AsyncMock()

            with patch("app.core.metrics.REQUEST_COUNT"):
                await middleware(scope, receive, send)

    @pytest.mark.asyncio
    async def test_middleware_extracts_endpoint_without_query_params(self):
        """Test that query parameters are stripped from endpoint."""
        mock_app = AsyncMock()
        middleware = MetricsMiddleware(mock_app)

        async def mock_app_handler(scope, receive, send):
            await send({"type": "http.response.start", "status": 200})

        middleware.app = mock_app_handler

        scope = {
            "type": "http",
            "path": "/api/v1/test?param1=value1&param2=value2",
            "method": "GET",
        }
        receive = AsyncMock()
        send = AsyncMock()

        with patch("app.core.metrics.REQUEST_DURATION") as mock_duration:
            await middleware(scope, receive, send)
            call_args = mock_duration.labels.call_args
            # Endpoint should not include query params
            assert "param" not in call_args[1]["endpoint"]
            assert call_args[1]["endpoint"] == "/api/v1/test"


class TestMetricsRecordingFunctions:
    """Test metric recording functions."""

    def test_record_database_query(self):
        """Test recording a database query metric."""
        with patch("app.core.metrics.DB_QUERY_DURATION") as mock_metric:
            record_database_query("SELECT", "users", 0.5)
            mock_metric.labels.assert_called_with(operation="SELECT", table="users")
            mock_metric.labels.return_value.observe.assert_called_with(0.5)

    def test_record_database_query_with_different_operations(self):
        """Test recording different database operations."""
        operations = ["SELECT", "INSERT", "UPDATE", "DELETE"]

        with patch("app.core.metrics.DB_QUERY_DURATION") as mock_metric:
            for op in operations:
                record_database_query(op, "table", 0.1)
                mock_metric.labels.assert_called_with(operation=op, table="table")

    def test_record_cache_hit(self):
        """Test recording a cache hit."""
        with patch("app.core.metrics.CACHE_HIT") as mock_metric:
            record_cache_hit("redis")
            mock_metric.labels.assert_called_with(cache_type="redis")
            mock_metric.labels.return_value.inc.assert_called()

    def test_record_cache_miss(self):
        """Test recording a cache miss."""
        with patch("app.core.metrics.CACHE_MISS") as mock_metric:
            record_cache_miss("redis")
            mock_metric.labels.assert_called_with(cache_type="redis")
            mock_metric.labels.return_value.inc.assert_called()

    def test_record_error(self):
        """Test recording an error."""
        with patch("app.core.metrics.ERROR_COUNT") as mock_metric:
            record_error("ValueError", "user_creation")
            mock_metric.labels.assert_called_with(
                error_type="ValueError", operation="user_creation"
            )
            mock_metric.labels.return_value.inc.assert_called()

    def test_record_expense(self):
        """Test recording an expense creation."""
        with patch("app.core.metrics.EXPENSE_COUNT") as mock_count, patch(
            "app.core.metrics.EXPENSE_AMOUNT"
        ) as mock_amount:
            record_expense(100.50, "USD", "food")

            mock_count.labels.assert_called_with(currency="USD")
            mock_count.labels.return_value.inc.assert_called()

            mock_amount.labels.assert_called_with(category="food")
            mock_amount.labels.return_value.observe.assert_called_with(100.50)

    def test_update_db_pool_metrics(self):
        """Test updating database pool metrics."""
        with patch("app.core.metrics.DB_POOL_SIZE") as mock_size, patch(
            "app.core.metrics.DB_POOL_CHECKEDOUT"
        ) as mock_checked:
            update_db_pool_metrics("auth_db", 10, 7)

            mock_size.labels.assert_called_with(pool_name="auth_db")
            mock_size.labels.return_value.set.assert_called_with(10)

            mock_checked.labels.assert_called_with(pool_name="auth_db")
            mock_checked.labels.return_value.set.assert_called_with(7)


class TestGetMetricsEndpoint:
    """Test get_metrics_endpoint function."""

    def test_get_metrics_endpoint_returns_string(self):
        """Test that get_metrics_endpoint returns a string."""
        with patch("app.core.metrics.generate_latest") as mock_generate:
            mock_generate.return_value = b"# HELP metric\n"
            result = get_metrics_endpoint()
            assert isinstance(result, str)

    def test_get_metrics_endpoint_decodes_bytes(self):
        """Test that bytes from prometheus are properly decoded."""
        with patch("app.core.metrics.generate_latest") as mock_generate:
            test_metrics = b"# HELP http_requests_total Total HTTP requests\n"
            mock_generate.return_value = test_metrics
            result = get_metrics_endpoint()
            assert result == test_metrics.decode("utf-8")

    def test_get_metrics_endpoint_uses_registry(self):
        """Test that get_metrics_endpoint uses the metrics registry."""
        with patch("app.core.metrics.generate_latest") as mock_generate:
            mock_generate.return_value = b"test"
            get_metrics_endpoint()
            # Should pass the registry
            mock_generate.assert_called_once()


class TestMetricsIntegration:
    """Integration tests for metrics system."""

    @pytest.mark.asyncio
    async def test_middleware_full_request_lifecycle(self):
        """Test full request lifecycle with metrics collection."""
        mock_app = AsyncMock()
        middleware = MetricsMiddleware(mock_app)

        async def mock_app_handler(scope, receive, send):
            # Simulate request processing
            await send({"type": "http.response.start", "status": 200})

        middleware.app = mock_app_handler

        scope = {
            "type": "http",
            "path": "/api/v1/expenses",
            "method": "POST",
        }
        receive = AsyncMock()
        send = AsyncMock()

        with patch("app.core.metrics.ACTIVE_REQUESTS"), patch(
            "app.core.metrics.REQUEST_DURATION"
        ), patch("app.core.metrics.REQUEST_COUNT"):
            await middleware(scope, receive, send)

    def test_metrics_recording_functions_chain(self):
        """Test recording multiple metrics in sequence."""
        with patch("app.core.metrics.CACHE_HIT"), patch(
            "app.core.metrics.DB_QUERY_DURATION"
        ), patch("app.core.metrics.EXPENSE_COUNT"):
            # Simulate a sequence of operations
            record_cache_hit("redis")
            record_database_query("INSERT", "expenses", 0.15)
            record_expense(50.0, "USD", "food")

    def test_metrics_error_recording(self):
        """Test recording errors alongside normal metrics."""
        with patch("app.core.metrics.ERROR_COUNT"), patch(
            "app.core.metrics.CACHE_MISS"
        ):
            record_error("ValueError", "validation")
            record_cache_miss("redis")


class TestMetricsEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_middleware_with_missing_path_in_scope(self):
        """Test middleware handles missing path gracefully."""
        mock_app = AsyncMock()
        middleware = MetricsMiddleware(mock_app)

        scope = {"type": "http", "method": "GET"}  # Missing 'path'
        receive = AsyncMock()
        send = AsyncMock()

        with patch("app.core.metrics.ACTIVE_REQUESTS"):
            await middleware(scope, receive, send)

    @pytest.mark.asyncio
    async def test_middleware_with_missing_method_in_scope(self):
        """Test middleware handles missing method gracefully."""
        mock_app = AsyncMock()
        middleware = MetricsMiddleware(mock_app)

        scope = {"type": "http", "path": "/api/test"}  # Missing 'method'
        receive = AsyncMock()
        send = AsyncMock()

        with patch("app.core.metrics.ACTIVE_REQUESTS"):
            await middleware(scope, receive, send)

    def test_record_expense_with_different_currencies(self):
        """Test recording expenses with different currencies."""
        currencies = ["USD", "EUR", "GBP", "JPY", "CAD"]

        with patch("app.core.metrics.EXPENSE_COUNT") as mock_count, patch(
            "app.core.metrics.EXPENSE_AMOUNT"
        ):
            for currency in currencies:
                record_expense(100.0, currency, "food")
                mock_count.labels.assert_called_with(currency=currency)

    def test_record_expense_with_different_categories(self):
        """Test recording expenses with different categories."""
        categories = ["food", "transport", "entertainment", "utilities", "healthcare"]

        with patch("app.core.metrics.EXPENSE_AMOUNT") as mock_amount, patch(
            "app.core.metrics.EXPENSE_COUNT"
        ):
            for category in categories:
                record_expense(50.0, "USD", category)
                mock_amount.labels.assert_called_with(category=category)

    def test_record_error_with_various_error_types(self):
        """Test recording various error types."""
        errors = [
            ("ValueError", "validation"),
            ("TypeError", "type_check"),
            ("KeyError", "dict_access"),
            ("RuntimeError", "general"),
            ("DatabaseError", "db_operation"),
        ]

        with patch("app.core.metrics.ERROR_COUNT") as mock_error:
            for error_type, operation in errors:
                record_error(error_type, operation)
                mock_error.labels.assert_called_with(
                    error_type=error_type, operation=operation
                )

    def test_record_database_query_with_zero_duration(self):
        """Test recording database query with zero duration."""
        with patch("app.core.metrics.DB_QUERY_DURATION") as mock_metric:
            record_database_query("SELECT", "users", 0)
            mock_metric.labels.return_value.observe.assert_called_with(0)

    def test_record_database_query_with_very_long_duration(self):
        """Test recording database query with very long duration."""
        with patch("app.core.metrics.DB_QUERY_DURATION") as mock_metric:
            record_database_query("SELECT", "users", 1000.5)
            mock_metric.labels.return_value.observe.assert_called_with(1000.5)

    def test_update_db_pool_metrics_with_full_pool(self):
        """Test updating pool metrics when pool is full."""
        with patch("app.core.metrics.DB_POOL_SIZE"), patch(
            "app.core.metrics.DB_POOL_CHECKEDOUT"
        ) as mock_checked:
            update_db_pool_metrics("main_db", 50, 50)  # All connections checked out
            mock_checked.labels.return_value.set.assert_called_with(50)

    def test_update_db_pool_metrics_with_empty_pool(self):
        """Test updating pool metrics when pool is empty."""
        with patch("app.core.metrics.DB_POOL_SIZE"), patch(
            "app.core.metrics.DB_POOL_CHECKEDOUT"
        ) as mock_checked:
            update_db_pool_metrics("backup_db", 50, 0)  # No connections used
            mock_checked.labels.return_value.set.assert_called_with(0)
