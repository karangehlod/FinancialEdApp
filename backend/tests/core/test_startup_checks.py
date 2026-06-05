"""Tests for startup checks."""
import asyncio
import pytest
import sys
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError
from redis.exceptions import RedisError

from app.startup_checks import (
    check_database_connectivity,
    check_redis_connectivity,
    verify_database_schema,
    perform_startup_checks,
    graceful_exit
)


class TestCheckDatabaseConnectivity:
    """Test database connectivity checks."""

    @pytest.mark.asyncio
    async def test_successful_database_connection(self):
        """Test successful database connectivity check."""
        with patch('app.startup_checks.auth_engine') as mock_auth_engine, \
             patch('app.startup_checks.data_engine') as mock_data_engine:
            
            # Mock successful connections
            mock_auth_conn = AsyncMock()
            mock_data_conn = AsyncMock()
            
            mock_auth_engine.connect.return_value.__aenter__.return_value = mock_auth_conn
            mock_data_engine.connect.return_value.__aenter__.return_value = mock_data_conn
            
            result = await check_database_connectivity()
            
            assert result is True
            mock_auth_conn.execute.assert_called_once()
            mock_data_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_auth_database_connection_failure(self):
        """Test auth database connection failure."""
        with patch('app.startup_checks.auth_engine') as mock_auth_engine, \
             patch('app.startup_checks.data_engine') as mock_data_engine:
            
            # Mock auth engine failure
            mock_auth_engine.connect.side_effect = SQLAlchemyError("Connection failed")
            
            result = await check_database_connectivity()
            
            assert result is False

    @pytest.mark.asyncio
    async def test_data_database_connection_failure(self):
        """Test data database connection failure."""
        with patch('app.startup_checks.auth_engine') as mock_auth_engine, \
             patch('app.startup_checks.data_engine') as mock_data_engine:
            
            # Mock successful auth connection
            mock_auth_conn = AsyncMock()
            mock_auth_engine.connect.return_value.__aenter__.return_value = mock_auth_conn
            
            # Mock data engine failure
            mock_data_engine.connect.side_effect = SQLAlchemyError("Connection failed")
            
            result = await check_database_connectivity()
            
            assert result is False

    @pytest.mark.asyncio
    async def test_database_execute_failure(self):
        """Test database execution failure."""
        with patch('app.startup_checks.auth_engine') as mock_auth_engine, \
             patch('app.startup_checks.data_engine') as mock_data_engine:
            
            mock_auth_conn = AsyncMock()
            mock_auth_conn.execute.side_effect = SQLAlchemyError("Query failed")
            mock_auth_engine.connect.return_value.__aenter__.return_value = mock_auth_conn
            
            result = await check_database_connectivity()
            
            assert result is False


class TestCheckRedisConnectivity:
    """Test Redis connectivity checks."""

    @pytest.mark.asyncio
    async def test_successful_redis_connection(self):
        """Test successful Redis connectivity check."""
        with patch('app.startup_checks.aioredis.from_url') as mock_from_url:
            mock_client = AsyncMock()
            mock_from_url.return_value = mock_client
            
            result = await check_redis_connectivity()
            
            assert result is True
            mock_client.ping.assert_called_once()
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_connection_failure(self):
        """Test Redis connection failure."""
        with patch('app.startup_checks.aioredis.from_url') as mock_from_url:
            mock_from_url.side_effect = RedisError("Connection failed")
            
            result = await check_redis_connectivity()
            
            assert result is False

    @pytest.mark.asyncio
    async def test_redis_ping_failure(self):
        """Test Redis ping failure."""
        with patch('app.startup_checks.aioredis.from_url') as mock_from_url:
            mock_client = AsyncMock()
            mock_client.ping.side_effect = RedisError("Ping failed")
            mock_from_url.return_value = mock_client
            
            result = await check_redis_connectivity()
            
            assert result is False


class TestVerifyDatabaseSchema:
    """Test database schema verification."""

    @pytest.mark.asyncio
    async def test_successful_schema_verification(self):
        """Test successful schema verification."""
        with patch('app.startup_checks.auth_engine') as mock_auth_engine, \
             patch('app.startup_checks.data_engine') as mock_data_engine:
            
            # Mock successful table existence checks
            mock_auth_conn = AsyncMock()
            mock_data_conn = AsyncMock()
            
            # Mock result objects that return True for scalar()
            mock_result = MagicMock()
            mock_result.scalar.return_value = True
            
            mock_auth_conn.execute.return_value = mock_result
            mock_data_conn.execute.return_value = mock_result
            
            mock_auth_engine.connect.return_value.__aenter__.return_value = mock_auth_conn
            mock_data_engine.connect.return_value.__aenter__.return_value = mock_data_conn
            
            result = await verify_database_schema()
            
            assert result is True

    @pytest.mark.asyncio
    async def test_missing_auth_table(self):
        """Test missing auth table."""
        with patch('app.startup_checks.auth_engine') as mock_auth_engine, \
             patch('app.startup_checks.data_engine') as mock_data_engine:
            
            mock_auth_conn = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar.return_value = False  # Table doesn't exist
            
            mock_auth_conn.execute.return_value = mock_result
            mock_auth_engine.connect.return_value.__aenter__.return_value = mock_auth_conn
            
            result = await verify_database_schema()
            
            assert result is False

    @pytest.mark.asyncio
    async def test_missing_data_table(self):
        """Test missing data table."""
        with patch('app.startup_checks.auth_engine') as mock_auth_engine, \
             patch('app.startup_checks.data_engine') as mock_data_engine:
            
            mock_auth_conn = AsyncMock()
            mock_data_conn = AsyncMock()
            
            # Mock auth table exists
            mock_auth_result = MagicMock()
            mock_auth_result.scalar.return_value = True
            mock_auth_conn.execute.return_value = mock_auth_result
            
            # Mock data table missing
            mock_data_result = MagicMock()
            mock_data_result.scalar.return_value = False
            mock_data_conn.execute.return_value = mock_data_result
            
            mock_auth_engine.connect.return_value.__aenter__.return_value = mock_auth_conn
            mock_data_engine.connect.return_value.__aenter__.return_value = mock_data_conn
            
            result = await verify_database_schema()
            
            assert result is False

    @pytest.mark.asyncio
    async def test_schema_verification_exception(self):
        """Test schema verification with database exception."""
        with patch('app.startup_checks.auth_engine') as mock_auth_engine:
            mock_auth_engine.connect.side_effect = SQLAlchemyError("Connection failed")
            
            result = await verify_database_schema()
            
            assert result is False


class TestPerformStartupChecks:
    """Test complete startup check process."""

    @pytest.mark.asyncio
    async def test_successful_startup_checks_without_schema(self):
        """Test successful startup checks without schema verification."""
        with patch('app.startup_checks.check_database_connectivity') as mock_db_check, \
             patch('app.startup_checks.check_redis_connectivity') as mock_redis_check:
            
            mock_db_check.return_value = True
            mock_redis_check.return_value = True
            
            result = await perform_startup_checks(verify_schema=False)
            
            assert result is True
            mock_db_check.assert_called_once()
            mock_redis_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_startup_checks_with_schema(self):
        """Test successful startup checks with schema verification."""
        with patch('app.startup_checks.check_database_connectivity') as mock_db_check, \
             patch('app.startup_checks.check_redis_connectivity') as mock_redis_check, \
             patch('app.startup_checks.verify_database_schema') as mock_schema_check:
            
            mock_db_check.return_value = True
            mock_redis_check.return_value = True
            mock_schema_check.return_value = True
            
            result = await perform_startup_checks(verify_schema=True)
            
            assert result is True
            mock_db_check.assert_called_once()
            mock_redis_check.assert_called_once()
            mock_schema_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_check_failure(self):
        """Test startup checks with database failure."""
        with patch('app.startup_checks.check_database_connectivity') as mock_db_check, \
             patch('app.startup_checks.check_redis_connectivity') as mock_redis_check:
            
            mock_db_check.return_value = False
            mock_redis_check.return_value = True
            
            result = await perform_startup_checks()
            
            assert result is False
            mock_db_check.assert_called_once()
            # Redis check shouldn't be called if database fails
            mock_redis_check.assert_not_called()

    @pytest.mark.asyncio
    async def test_redis_check_failure(self):
        """Test startup checks with Redis failure."""
        with patch('app.startup_checks.check_database_connectivity') as mock_db_check, \
             patch('app.startup_checks.check_redis_connectivity') as mock_redis_check:
            
            mock_db_check.return_value = True
            mock_redis_check.return_value = False
            
            result = await perform_startup_checks()
            
            assert result is False
            mock_db_check.assert_called_once()
            mock_redis_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_schema_check_failure(self):
        """Test startup checks with schema verification failure."""
        with patch('app.startup_checks.check_database_connectivity') as mock_db_check, \
             patch('app.startup_checks.check_redis_connectivity') as mock_redis_check, \
             patch('app.startup_checks.verify_database_schema') as mock_schema_check:
            
            mock_db_check.return_value = True
            mock_redis_check.return_value = True
            mock_schema_check.return_value = False
            
            result = await perform_startup_checks(verify_schema=True)
            
            assert result is False
            mock_db_check.assert_called_once()
            mock_redis_check.assert_called_once()
            mock_schema_check.assert_called_once()


class TestGracefulExit:
    """Test graceful exit functionality."""

    @pytest.mark.asyncio
    async def test_graceful_exit_default_code(self):
        """Test graceful exit with default exit code."""
        with patch('app.startup_checks.sys.exit') as mock_exit:
            await graceful_exit("Test message")
            mock_exit.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_graceful_exit_custom_code(self):
        """Test graceful exit with custom exit code."""
        with patch('app.startup_checks.sys.exit') as mock_exit:
            await graceful_exit("Test message", exit_code=2)
            mock_exit.assert_called_once_with(2)


class TestMainExecution:
    """Test main execution block."""

    @pytest.mark.asyncio
    async def test_main_success(self):
        """Test main execution with successful checks."""
        with patch('app.startup_checks.perform_startup_checks') as mock_checks, \
             patch('app.startup_checks.sys.exit') as mock_exit:
            
            mock_checks.return_value = True
            
            # Import and execute the main function
            from app.startup_checks import main
            await main()
            
            mock_checks.assert_called_once_with(verify_schema=True)
            mock_exit.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_main_failure(self):
        """Test main execution with failed checks."""
        with patch('app.startup_checks.perform_startup_checks') as mock_checks, \
             patch('app.startup_checks.sys.exit') as mock_exit:
            
            mock_checks.return_value = False
            
            # Import and execute the main function
            from app.startup_checks import main
            await main()
            
            mock_checks.assert_called_once_with(verify_schema=True)
            mock_exit.assert_called_once_with(1)
