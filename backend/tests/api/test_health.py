"""Comprehensive tests for health check endpoints."""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.api.v1.health import HealthChecker, HealthStatus


# Test fixtures
@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def health_checker():
    """Create a fresh HealthChecker instance."""
    return HealthChecker()


class TestHealthStatus:
    """Test HealthStatus enum."""
    
    def test_health_status_healthy(self):
        """Test HEALTHY status value."""
        assert HealthStatus.HEALTHY == "healthy"
    
    def test_health_status_degraded(self):
        """Test DEGRADED status value."""
        assert HealthStatus.DEGRADED == "degraded"
    
    def test_health_status_unhealthy(self):
        """Test UNHEALTHY status value."""
        assert HealthStatus.UNHEALTHY == "unhealthy"
    
    def test_health_status_all_values(self):
        """Test all status values are unique."""
        statuses = [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
        assert len(statuses) == len(set(statuses))


class TestHealthChecker:
    """Test HealthChecker class."""
    
    def test_health_checker_init(self, health_checker):
        """Test HealthChecker initialization."""
        assert health_checker.checks == {}
        assert health_checker.dependency_checks == {}
    
    def test_register_check(self, health_checker):
        """Test registering a health check."""
        check_func = MagicMock()
        health_checker.register_check("test_check", check_func)
        assert "test_check" in health_checker.checks
        assert health_checker.checks["test_check"] == check_func
    
    def test_register_multiple_checks(self, health_checker):
        """Test registering multiple checks."""
        check1 = MagicMock()
        check2 = MagicMock()
        health_checker.register_check("check1", check1)
        health_checker.register_check("check2", check2)
        assert len(health_checker.checks) == 2
        assert health_checker.checks["check1"] == check1
        assert health_checker.checks["check2"] == check2
    
    def test_register_dependency_check(self, health_checker):
        """Test registering a dependency check."""
        check_func = MagicMock()
        health_checker.register_dependency_check("db_check", check_func)
        assert "db_check" in health_checker.dependency_checks
        assert health_checker.dependency_checks["db_check"] == check_func
    
    def test_register_multiple_dependency_checks(self, health_checker):
        """Test registering multiple dependency checks."""
        db_check = MagicMock()
        cache_check = MagicMock()
        health_checker.register_dependency_check("db", db_check)
        health_checker.register_dependency_check("cache", cache_check)
        assert len(health_checker.dependency_checks) == 2
    
    @pytest.mark.asyncio
    async def test_perform_checks_sync_function(self, health_checker):
        """Test performing sync health checks."""
        check_func = MagicMock(return_value={"status": HealthStatus.HEALTHY})
        health_checker.register_check("sync_check", check_func)
        results = await health_checker.perform_checks()
        assert "sync_check" in results
        assert results["sync_check"]["status"] == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_perform_checks_async_function(self, health_checker):
        """Test performing async health checks."""
        async def async_check():
            return {"status": HealthStatus.HEALTHY}
        
        health_checker.register_check("async_check", async_check)
        results = await health_checker.perform_checks()
        assert "async_check" in results
        assert results["async_check"]["status"] == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_perform_checks_multiple_checks(self, health_checker):
        """Test performing multiple health checks."""
        health_checker.register_check(
            "check1", 
            MagicMock(return_value={"status": HealthStatus.HEALTHY})
        )
        health_checker.register_check(
            "check2", 
            MagicMock(return_value={"status": HealthStatus.DEGRADED})
        )
        
        results = await health_checker.perform_checks()
        assert len(results) == 2
        assert results["check1"]["status"] == HealthStatus.HEALTHY
        assert results["check2"]["status"] == HealthStatus.DEGRADED
    
    @pytest.mark.asyncio
    async def test_perform_checks_exception_handling(self, health_checker):
        """Test exception handling in health checks."""
        error_func = MagicMock(side_effect=Exception("Test error"))
        health_checker.register_check("error_check", error_func)
        
        results = await health_checker.perform_checks()
        assert "error_check" in results
        assert results["error_check"]["status"] == HealthStatus.UNHEALTHY
        assert "Test error" in results["error_check"]["error"]
    
    @pytest.mark.asyncio
    async def test_perform_checks_mixed_sync_async(self, health_checker):
        """Test performing mixed sync and async checks."""
        health_checker.register_check("sync", MagicMock(return_value={"ok": True}))
        
        async def async_func():
            return {"ok": True}
        health_checker.register_check("async", async_func)
        
        results = await health_checker.perform_checks()
        assert len(results) == 2
        assert results["sync"]["ok"] is True
        assert results["async"]["ok"] is True
    
    @pytest.mark.asyncio
    async def test_perform_dependency_checks_sync_function(self, health_checker):
        """Test performing sync dependency checks."""
        check_func = MagicMock(return_value={"status": HealthStatus.HEALTHY})
        health_checker.register_dependency_check("sync_dep", check_func)
        
        results = await health_checker.perform_dependency_checks()
        assert "sync_dep" in results
        assert results["sync_dep"]["status"] == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_perform_dependency_checks_async_function(self, health_checker):
        """Test performing async dependency checks."""
        async def async_check():
            return {"status": HealthStatus.HEALTHY}
        
        health_checker.register_dependency_check("async_dep", async_check)
        results = await health_checker.perform_dependency_checks()
        assert "async_dep" in results
        assert results["async_dep"]["status"] == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_perform_dependency_checks_exception_handling(self, health_checker):
        """Test exception handling in dependency checks."""
        error_func = MagicMock(side_effect=Exception("DB connection failed"))
        health_checker.register_dependency_check("db_check", error_func)
        
        results = await health_checker.perform_dependency_checks()
        assert "db_check" in results
        assert results["db_check"]["status"] == HealthStatus.UNHEALTHY
        assert "DB connection failed" in results["db_check"]["error"]
    
    @pytest.mark.asyncio
    async def test_perform_dependency_checks_multiple(self, health_checker):
        """Test multiple dependency checks."""
        health_checker.register_dependency_check(
            "db",
            MagicMock(return_value={"status": HealthStatus.HEALTHY})
        )
        health_checker.register_dependency_check(
            "cache",
            MagicMock(return_value={"status": HealthStatus.DEGRADED})
        )
        
        results = await health_checker.perform_dependency_checks()
        assert len(results) == 2


class TestLivenessProbe:
    """Test liveness probe endpoint."""
    
    def test_liveness_probe_status_code(self, client):
        """Test liveness probe returns 200."""
        response = client.get("/health/live")
        assert response.status_code == 200
    
    def test_liveness_probe_response_structure(self, client):
        """Test liveness probe response structure."""
        response = client.get("/health/live")
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "message" in data
    
    def test_liveness_probe_status_value(self, client):
        """Test liveness probe status value."""
        response = client.get("/health/live")
        data = response.json()
        assert data["status"] == HealthStatus.HEALTHY
    
    def test_liveness_probe_message(self, client):
        """Test liveness probe message."""
        response = client.get("/health/live")
        data = response.json()
        assert "running" in data["message"].lower()
    
    def test_liveness_probe_timestamp_format(self, client):
        """Test liveness probe timestamp is ISO format."""
        response = client.get("/health/live")
        data = response.json()
        # Should not raise exception if valid ISO format
        datetime.fromisoformat(data["timestamp"])
    
    def test_liveness_probe_response_type(self, client):
        """Test liveness probe response is valid JSON."""
        response = client.get("/health/live")
        assert response.headers["content-type"] == "application/json"


class TestReadinessProbe:
    """Test readiness probe endpoint."""
    
    def test_readiness_probe_status_code(self, client):
        """Test readiness probe returns 200 or 503."""
        response = client.get("/health/ready")
        assert response.status_code in [200, 503]
    
    def test_readiness_probe_response_structure(self, client):
        """Test readiness probe response has expected structure."""
        response = client.get("/health/ready")
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
    
    def test_readiness_probe_response_type(self, client):
        """Test readiness probe response is valid JSON."""
        response = client.get("/health/ready")
        assert response.headers["content-type"] == "application/json"
    
    def test_readiness_probe_timestamp_format(self, client):
        """Test readiness probe timestamp is ISO format."""
        response = client.get("/health/ready")
        data = response.json()
        datetime.fromisoformat(data["timestamp"])
    
    def test_readiness_probe_status_values(self, client):
        """Test readiness probe returns valid status."""
        response = client.get("/health/ready")
        data = response.json()
        assert data["status"] in [
            HealthStatus.HEALTHY, 
            HealthStatus.DEGRADED, 
            HealthStatus.UNHEALTHY
        ]


class TestHealthEndpointIntegration:
    """Integration tests for health endpoints."""
    
    def test_both_probes_accessible(self, client):
        """Test both probes are accessible."""
        live = client.get("/health/live")
        ready = client.get("/health/ready")
        assert live.status_code == 200
        assert ready.status_code in [200, 503]
    
    def test_health_endpoints_no_auth_required(self, client):
        """Test health endpoints don't require authentication."""
        # Should work without any auth headers
        response = client.get("/health/live")
        assert response.status_code == 200
    
    def test_invalid_health_path(self, client):
        """Test invalid health endpoint returns 404."""
        response = client.get("/health/invalid")
        assert response.status_code == 404
    
    def test_health_endpoints_methods(self, client):
        """Test only GET method is allowed."""
        live_get = client.get("/health/live")
        live_post = client.post("/health/live")
        live_put = client.put("/health/live")
        
        assert live_get.status_code == 200
        assert live_post.status_code == 405  # Method not allowed
        assert live_put.status_code == 405
    
    def test_health_response_keys_present(self, client):
        """Test all expected keys in response."""
        response = client.get("/health/live")
        data = response.json()
        for key in ["status", "timestamp", "message"]:
            assert key in data, f"Missing key: {key}"
    
    def test_multiple_liveness_calls(self, client):
        """Test multiple liveness probe calls."""
        for _ in range(3):
            response = client.get("/health/live")
            assert response.status_code == 200
            assert response.json()["status"] == HealthStatus.HEALTHY
    
    def test_multiple_readiness_calls(self, client):
        """Test multiple readiness probe calls."""
        for _ in range(3):
            response = client.get("/health/ready")
            assert response.status_code in [200, 503]
            data = response.json()
            assert "status" in data


class TestHealthEdgeCases:
    """Edge case tests for health endpoints."""
    
    def test_health_status_enum_comparison(self):
        """Test enum value comparisons."""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"
        assert HealthStatus.HEALTHY != HealthStatus.DEGRADED
    
    @pytest.mark.asyncio
    async def test_health_checker_empty_checks(self, health_checker):
        """Test performing checks with no registered checks."""
        results = await health_checker.perform_checks()
        assert results == {}
    
    @pytest.mark.asyncio
    async def test_health_checker_empty_dependency_checks(self, health_checker):
        """Test performing dependency checks with no registered checks."""
        results = await health_checker.perform_dependency_checks()
        assert results == {}
    
    @pytest.mark.asyncio
    async def test_health_checker_duplicate_check_name_overwrites(self, health_checker):
        """Test that registering with same name overwrites."""
        check1 = MagicMock(return_value={"value": 1})
        check2 = MagicMock(return_value={"value": 2})
        
        health_checker.register_check("same_name", check1)
        health_checker.register_check("same_name", check2)
        
        results = await health_checker.perform_checks()
        assert len(results) == 1
        assert results["same_name"]["value"] == 2
    
    def test_health_checker_instance_independence(self):
        """Test multiple HealthChecker instances are independent."""
        checker1 = HealthChecker()
        checker2 = HealthChecker()
        
        checker1.register_check("check", MagicMock())
        assert "check" in checker1.checks
        assert "check" not in checker2.checks
    
    @pytest.mark.asyncio
    async def test_health_check_with_none_return(self, health_checker):
        """Test handling check that returns None."""
        check_func = MagicMock(return_value=None)
        health_checker.register_check("none_check", check_func)
        
        results = await health_checker.perform_checks()
        assert "none_check" in results
        assert results["none_check"] is None
    
    @pytest.mark.asyncio
    async def test_health_check_exception_preserves_other_checks(self, health_checker):
        """Test that exception in one check doesn't affect others."""
        health_checker.register_check("ok", MagicMock(return_value={"ok": True}))
        health_checker.register_check("error", MagicMock(side_effect=Exception("fail")))
        health_checker.register_check("ok2", MagicMock(return_value={"ok": True}))
        
        results = await health_checker.perform_checks()
        assert results["ok"]["ok"] is True
        assert results["ok2"]["ok"] is True
        assert results["error"]["status"] == HealthStatus.UNHEALTHY
