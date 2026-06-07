"""Health check endpoints for liveness and readiness probes."""

from typing import Dict, Any, Optional
from enum import Enum
import logging
import inspect
from datetime import datetime

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


class HealthStatus(str, Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthChecker:
    """Manager for health check services."""
    
    def __init__(self):
        """Initialize health checker."""
        self.checks: Dict[str, callable] = {}
        self.dependency_checks: Dict[str, callable] = {}
    
    def register_check(self, name: str, check_func: callable) -> None:
        """Register a health check function."""
        self.checks[name] = check_func
    
    def register_dependency_check(self, name: str, check_func: callable) -> None:
        """Register a dependency check (database, cache, etc.)."""
        self.dependency_checks[name] = check_func
    
    async def perform_checks(self) -> Dict[str, Any]:
        """Perform all registered health checks."""
        results = {}
        
        # Perform application checks
        for name, check_func in self.checks.items():
            try:
                if inspect.iscoroutinefunction(check_func):
                    results[name] = await check_func()
                else:
                    results[name] = check_func()
            except Exception as e:
                logger.error(f"Health check '{name}' failed: {e}")
                results[name] = {"status": HealthStatus.UNHEALTHY, "error": str(e)}
        
        return results
    
    async def perform_dependency_checks(self) -> Dict[str, Any]:
        """Perform all registered dependency checks."""
        results = {}
        
        for name, check_func in self.dependency_checks.items():
            try:
                if inspect.iscoroutinefunction(check_func):
                    results[name] = await check_func()
                else:
                    results[name] = check_func()
            except Exception as e:
                logger.error(f"Dependency check '{name}' failed: {e}")
                results[name] = {"status": HealthStatus.UNHEALTHY, "error": str(e)}
        
        return results


# Global health checker instance
health_checker = HealthChecker()


@router.get("/live", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def liveness_probe():
    """
    Liveness probe endpoint.
    
    Returns: 200 if the application is running, 503 otherwise.
    This probe is used by orchestration platforms (K8s) to determine
    if the container should be restarted.
    """
    return {
        "status": HealthStatus.HEALTHY,
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Application is running"
    }


@router.get("/ready", response_model=Dict[str, Any])
async def readiness_probe():
    """
    Readiness probe endpoint.
    
    Returns: 200 if the application is ready to serve traffic, 503 otherwise.
    This probe is used by load balancers to determine if requests should be routed.
    Checks all critical dependencies.
    """
    try:
        # Perform dependency checks
        dependency_results = await health_checker.perform_dependency_checks()
        
        # Check if all dependencies are healthy
        all_healthy = all(
            dep.get("status") == HealthStatus.HEALTHY
            for dep in dependency_results.values()
        )
        
        status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        overall_status = HealthStatus.HEALTHY if all_healthy else HealthStatus.UNHEALTHY
        
        return JSONResponse(
            status_code=status_code,
            content={
                "status": overall_status,
                "timestamp": datetime.utcnow().isoformat(),
                "dependencies": dependency_results
            }
        )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": HealthStatus.UNHEALTHY,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )


@router.get("/detailed", response_model=Dict[str, Any])
async def detailed_health():
    """
    Detailed health check endpoint.
    
    Returns comprehensive health information including all checks and metrics.
    """
    try:
        checks = await health_checker.perform_checks()
        dependencies = await health_checker.perform_dependency_checks()
        
        # Determine overall status
        all_checks_healthy = all(
            check.get("status") == HealthStatus.HEALTHY
            for check in checks.values()
        )
        all_deps_healthy = all(
            dep.get("status") == HealthStatus.HEALTHY
            for dep in dependencies.values()
        )
        
        overall_status = (
            HealthStatus.HEALTHY if (all_checks_healthy and all_deps_healthy)
            else HealthStatus.DEGRADED if (all_checks_healthy or all_deps_healthy)
            else HealthStatus.UNHEALTHY
        )
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks,
            "dependencies": dependencies,
            "uptime_seconds": None  # Can be populated with actual uptime
        }
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": HealthStatus.UNHEALTHY,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )


def register_database_check(db_session) -> None:
    """Register database connectivity check."""
    async def check_database() -> Dict[str, Any]:
        try:
            # Simple health check query
            await db_session.execute("SELECT 1")
            return {"status": HealthStatus.HEALTHY, "message": "Database connected"}
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"status": HealthStatus.UNHEALTHY, "error": str(e)}
    
    health_checker.register_dependency_check("database", check_database)


def register_cache_check(cache_provider) -> None:
    """Register cache connectivity check."""
    async def check_cache() -> Dict[str, Any]:
        try:
            # Test cache operations
            test_key = "health_check_test"
            await cache_provider.set(test_key, "ok", ttl=10)
            value = await cache_provider.get(test_key)
            if value == "ok":
                await cache_provider.delete(test_key)
                return {"status": HealthStatus.HEALTHY, "message": "Cache connected"}
            else:
                return {"status": HealthStatus.UNHEALTHY, "error": "Cache test failed"}
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {"status": HealthStatus.UNHEALTHY, "error": str(e)}
    
    health_checker.register_dependency_check("cache", check_cache)


@router.get("/db/auth", response_model=Dict[str, Any])
async def auth_db_health():
    """
    Check auth database health and connectivity.
    
    Tests connection to the authentication database (auth_db).
    """
    try:
        from app.db.session import auth_engine
        from sqlalchemy import text
        
        async with auth_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            
        return {
            "status": HealthStatus.HEALTHY,
            "timestamp": datetime.utcnow().isoformat(),
            "database": "auth_db",
            "message": "Auth database is healthy and accessible"
        }
    except Exception as e:
        logger.error(f"Auth database health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": HealthStatus.UNHEALTHY,
                "timestamp": datetime.utcnow().isoformat(),
                "database": "auth_db",
                "error": str(e)
            }
        )


@router.get("/db/data", response_model=Dict[str, Any])
async def data_db_health():
    """
    Check data database health and connectivity.
    
    Tests connection to the data database (financial_ed_db).
    """
    try:
        from app.db.session import data_engine
        from sqlalchemy import text
        
        async with data_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            
        return {
            "status": HealthStatus.HEALTHY,
            "timestamp": datetime.utcnow().isoformat(),
            "database": "financial_ed_db",
            "message": "Data database is healthy and accessible"
        }
    except Exception as e:
        logger.error(f"Data database health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": HealthStatus.UNHEALTHY,
                "timestamp": datetime.utcnow().isoformat(),
                "database": "financial_ed_db",
                "error": str(e)
            }
        )


@router.get("/db", response_model=Dict[str, Any])
async def databases_health():
    """
    Check both databases health and connectivity.
    
    Tests connections to both auth_db and financial_ed_db.
    """
    from app.db.session import auth_engine, data_engine
    from sqlalchemy import text
    
    auth_db_status = HealthStatus.UNHEALTHY
    auth_db_error = None
    
    data_db_status = HealthStatus.UNHEALTHY
    data_db_error = None
    
    # Check auth database
    try:
        async with auth_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        auth_db_status = HealthStatus.HEALTHY
    except Exception as e:
        logger.error(f"Auth database health check failed: {e}")
        auth_db_error = str(e)
    
    # Check data database
    try:
        async with data_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        data_db_status = HealthStatus.HEALTHY
    except Exception as e:
        logger.error(f"Data database health check failed: {e}")
        data_db_error = str(e)
    
    all_healthy = auth_db_status == HealthStatus.HEALTHY and data_db_status == HealthStatus.HEALTHY
    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": HealthStatus.HEALTHY if all_healthy else HealthStatus.UNHEALTHY,
            "timestamp": datetime.utcnow().isoformat(),
            "databases": {
                "auth_db": {
                    "status": auth_db_status,
                    "error": auth_db_error
                },
                "financial_ed_db": {
                    "status": data_db_status,
                    "error": data_db_error
                }
            },
            "message": "All databases healthy" if all_healthy else "Some databases are unhealthy"
        }
    )
