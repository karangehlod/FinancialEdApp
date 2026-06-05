"""
Comprehensive health checks for all system dependencies.

Checks:
- Database connectivity (auth and data)
- Redis/cache connectivity
- External service availability
- Memory and disk usage
- Service status
- Database pool statistics
"""

import logging
import psutil
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from sqlalchemy import text

logger = logging.getLogger(__name__)


class HealthCheckStatus:
    """Health check status enumeration and utilities."""
    
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    
    @staticmethod
    def from_boolean(success: bool, raise_on_failure: bool = False) -> str:
        """Convert boolean to health status."""
        if success:
            return HealthCheckStatus.HEALTHY
        status = HealthCheckStatus.UNHEALTHY
        if raise_on_failure:
            raise Exception(f"Health check failed: {status}")
        return status


async def check_auth_database(auth_db_engine) -> Dict[str, Any]:
    """Check authentication database connectivity and pool status."""
    try:
        async with auth_db_engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            await result.close()

        pool_status = _get_pool_stats(auth_db_engine)
        return {
            "status": HealthCheckStatus.HEALTHY,
            "service": "auth_database",
            "message": "Auth database is healthy",
            "pool": pool_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error(f"Auth database health check failed: {exc}")
        return {
            "status": HealthCheckStatus.UNHEALTHY,
            "service": "auth_database",
            "message": f"Auth database is unhealthy: {str(exc)}",
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


async def check_data_database(data_db_engine) -> Dict[str, Any]:
    """Check data database connectivity and pool status."""
    try:
        async with data_db_engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            await result.close()

        pool_status = _get_pool_stats(data_db_engine)
        return {
            "status": HealthCheckStatus.HEALTHY,
            "service": "data_database",
            "message": "Data database is healthy",
            "pool": pool_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error(f"Data database health check failed: {exc}")
        return {
            "status": HealthCheckStatus.UNHEALTHY,
            "service": "data_database",
            "message": f"Data database is unhealthy: {str(exc)}",
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def _get_pool_stats(engine) -> Dict[str, Any]:
    """
    Extract connection pool statistics from an SQLAlchemy engine.

    Works with QueuePool (sync/async). Returns an empty dict if the pool
    doesn't expose the expected attributes (e.g. NullPool in tests).
    """
    try:
        pool = engine.pool
        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalidated() if hasattr(pool, "invalidated") else None,
        }
    except Exception:
        return {}


async def check_redis_cache(redis_client) -> Dict[str, Any]:
    """Check Redis cache connectivity."""
    if redis_client is None:
        return {
            "status": HealthCheckStatus.DEGRADED,
            "service": "redis_cache",
            "message": "Redis cache is not available (optional service)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    try:
        # Execute ping to verify connectivity
        pong = await redis_client.ping()
        
        if pong:
            return {
                "status": HealthCheckStatus.HEALTHY,
                "service": "redis_cache",
                "message": "Redis cache is healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        else:
            raise Exception("Ping returned False")
    
    except Exception as exc:
        logger.error(f"Redis cache health check failed: {exc}")
        return {
            "status": HealthCheckStatus.DEGRADED,
            "service": "redis_cache",
            "message": f"Redis cache is unavailable: {str(exc)}",
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def check_memory() -> Dict[str, Any]:
    """Check system memory usage."""
    try:
        memory = psutil.virtual_memory()
        percent_used = memory.percent
        
        # Determine status based on memory usage
        if percent_used > 90:
            status = HealthCheckStatus.UNHEALTHY
            message = "Memory usage critical (>90%)"
        elif percent_used > 75:
            status = HealthCheckStatus.DEGRADED
            message = "Memory usage high (>75%)"
        else:
            status = HealthCheckStatus.HEALTHY
            message = "Memory usage is healthy"
        
        return {
            "status": status,
            "service": "system_memory",
            "message": message,
            "percent_used": percent_used,
            "available_mb": memory.available // (1024 * 1024),
            "total_mb": memory.total // (1024 * 1024),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error(f"Memory check failed: {exc}")
        return {
            "status": HealthCheckStatus.UNKNOWN,
            "service": "system_memory",
            "message": f"Could not check memory: {str(exc)}",
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def check_disk() -> Dict[str, Any]:
    """Check system disk usage."""
    try:
        disk = psutil.disk_usage("/")
        percent_used = disk.percent
        
        # Determine status based on disk usage
        if percent_used > 95:
            status = HealthCheckStatus.UNHEALTHY
            message = "Disk usage critical (>95%)"
        elif percent_used > 80:
            status = HealthCheckStatus.DEGRADED
            message = "Disk usage high (>80%)"
        else:
            status = HealthCheckStatus.HEALTHY
            message = "Disk usage is healthy"
        
        return {
            "status": status,
            "service": "system_disk",
            "message": message,
            "percent_used": percent_used,
            "free_gb": disk.free // (1024 * 1024 * 1024),
            "total_gb": disk.total // (1024 * 1024 * 1024),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error(f"Disk check failed: {exc}")
        return {
            "status": HealthCheckStatus.UNKNOWN,
            "service": "system_disk",
            "message": f"Could not check disk: {str(exc)}",
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


async def check_overall_health(
    auth_db_engine,
    data_db_engine,
    redis_client: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Perform comprehensive health check of all system dependencies.
    
    Args:
        auth_db_engine: Authentication database engine
        data_db_engine: Data database engine
        redis_client: Optional Redis client
    
    Returns:
        Overall health status with details of all checks
    """
    checks = {}
    
    # Check databases
    checks["auth_database"] = await check_auth_database(auth_db_engine)
    checks["data_database"] = await check_data_database(data_db_engine)
    
    # Check cache
    checks["redis_cache"] = await check_redis_cache(redis_client)
    
    # Check system resources
    checks["memory"] = check_memory()
    checks["disk"] = check_disk()
    
    # Determine overall status
    unhealthy_count = sum(1 for check in checks.values() if check["status"] == HealthCheckStatus.UNHEALTHY)
    degraded_count = sum(1 for check in checks.values() if check["status"] == HealthCheckStatus.DEGRADED)
    
    if unhealthy_count > 0:
        overall_status = HealthCheckStatus.UNHEALTHY
        message = f"{unhealthy_count} critical service(s) down"
    elif degraded_count > 1:
        overall_status = HealthCheckStatus.UNHEALTHY
        message = f"{degraded_count} service(s) degraded"
    elif degraded_count > 0:
        overall_status = HealthCheckStatus.DEGRADED
        message = f"{degraded_count} service(s) degraded"
    else:
        overall_status = HealthCheckStatus.HEALTHY
        message = "All systems operational"
    
    return {
        "status": overall_status,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "summary": {
            "total_checks": len(checks),
            "healthy": sum(1 for c in checks.values() if c["status"] == HealthCheckStatus.HEALTHY),
            "degraded": degraded_count,
            "unhealthy": unhealthy_count,
        }
    }
