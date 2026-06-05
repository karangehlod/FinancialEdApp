"""
Comprehensive tests for app/core/rate_limiting.py

Coverage: RedisRateLimiter, RateLimitConfig, RouteRateLimit
Tests include: Rate limit enforcement, edge cases, error handling, configuration
"""

import pytest
from unittest.mock import AsyncMock, patch
from app.core.rate_limiting import (
    RedisRateLimiter,
    RateLimitConfig,
    RouteRateLimit,
    rate_limit_config,
)


# ===========================================================================
# RedisRateLimiter tests
# ===========================================================================

class TestRedisRateLimiter:
    """Test RedisRateLimiter class."""

    @pytest.fixture
    def mock_redis(self):
        return AsyncMock()

    @pytest.fixture
    def limiter(self, mock_redis):
        return RedisRateLimiter(mock_redis)

    # --- init / attributes ---

    def test_initialization(self):
        mock_redis = AsyncMock()
        limiter = RedisRateLimiter(mock_redis)
        assert limiter._redis is mock_redis
        assert limiter.KEY_PREFIX == "rate_limit"

    def test_build_key(self):
        limiter = RedisRateLimiter(AsyncMock())
        assert limiter._build_key("user:abc") == "rate_limit:user:abc"

    # --- check_and_increment ---

    @pytest.mark.asyncio
    async def test_check_and_increment_allowed(self, limiter, mock_redis):
        """Request within limit is allowed."""
        mock_script = AsyncMock(return_value=[1, 1])
        # register_script is sync in redis-py; it returns a callable script object
        mock_redis.register_script = lambda _: mock_script

        allowed, count = await limiter.check_and_increment("user:abc", 5, 60)
        assert allowed is True
        assert count == 1

    @pytest.mark.asyncio
    async def test_check_and_increment_denied(self, limiter, mock_redis):
        """Request over limit is denied."""
        mock_script = AsyncMock(return_value=[0, 5])
        mock_redis.register_script = lambda _: mock_script

        allowed, count = await limiter.check_and_increment("user:abc", 5, 60)
        assert allowed is False
        assert count == 5

    @pytest.mark.asyncio
    async def test_check_and_increment_error_fails_open(self, limiter, mock_redis):
        """Rate limiter fails open on Redis errors."""
        def bad_register(_):
            raise Exception("Redis down")
        mock_redis.register_script = bad_register
        allowed, count = await limiter.check_and_increment("user:abc", 5, 60)
        assert allowed is True
        assert count == 0

    @pytest.mark.asyncio
    async def test_lua_script_registered_once(self, limiter, mock_redis):
        """Lua script is lazily registered once."""
        mock_script = AsyncMock(return_value=[1, 1])
        call_count = 0
        def track_register(src):
            nonlocal call_count
            call_count += 1
            return mock_script
        mock_redis.register_script = track_register

        await limiter.check_and_increment("a", 5, 60)
        await limiter.check_and_increment("b", 5, 60)
        assert call_count == 1  # only registered once

    # --- get_remaining ---

    @pytest.mark.asyncio
    async def test_get_remaining(self, limiter, mock_redis):
        mock_redis.zremrangebyscore = AsyncMock()
        mock_redis.zcard = AsyncMock(return_value=3)
        assert await limiter.get_remaining("u", 5, 60) == 2

    @pytest.mark.asyncio
    async def test_get_remaining_at_zero(self, limiter, mock_redis):
        mock_redis.zremrangebyscore = AsyncMock()
        mock_redis.zcard = AsyncMock(return_value=5)
        assert await limiter.get_remaining("u", 5, 60) == 0

    @pytest.mark.asyncio
    async def test_get_remaining_clamped(self, limiter, mock_redis):
        mock_redis.zremrangebyscore = AsyncMock()
        mock_redis.zcard = AsyncMock(return_value=10)
        assert await limiter.get_remaining("u", 5, 60) == 0

    @pytest.mark.asyncio
    async def test_get_remaining_error_returns_limit(self, limiter, mock_redis):
        mock_redis.zremrangebyscore = AsyncMock(side_effect=Exception("err"))
        assert await limiter.get_remaining("u", 5, 60) == 5

    # --- reset ---

    @pytest.mark.asyncio
    async def test_reset_removes_key(self, limiter, mock_redis):
        mock_redis.delete = AsyncMock()
        assert await limiter.reset("user:abc") is True
        mock_redis.delete.assert_called_once_with("rate_limit:user:abc")

    @pytest.mark.asyncio
    async def test_reset_error_handling(self, limiter, mock_redis):
        mock_redis.delete = AsyncMock(side_effect=Exception("err"))
        assert await limiter.reset("user:abc") is False


# ===========================================================================
# RateLimitConfig tests
# ===========================================================================

class TestRateLimitConfig:
    """Test RateLimitConfig class."""

    def test_has_default_rules(self):
        config = RateLimitConfig()
        assert "default_authenticated" in config.rules
        assert "default_unauthenticated" in config.rules

    def test_auth_rules_exist(self):
        config = RateLimitConfig()
        assert "/api/v1/auth/login" in config.rules
        assert "/api/v1/auth/register" in config.rules

    def test_get_rule_exact_match(self):
        config = RateLimitConfig()
        rule = config.get_rule("/api/v1/auth/login")
        assert isinstance(rule, RouteRateLimit)
        assert rule.limit > 0
        assert rule.window > 0

    def test_get_rule_prefix_match(self):
        config = RateLimitConfig()
        rule = config.get_rule("/api/v1/exports/some-endpoint")
        assert rule.group == "exports"

    def test_get_rule_default_authenticated(self):
        config = RateLimitConfig()
        rule = config.get_rule("/some/unknown/path", authenticated=True)
        assert rule.group == "api"

    def test_get_rule_default_unauthenticated(self):
        config = RateLimitConfig()
        rule = config.get_rule("/some/unknown/path", authenticated=False)
        assert rule.group == "public"

    def test_auth_endpoints_restricted(self):
        config = RateLimitConfig()
        login_rule = config.get_rule("/api/v1/auth/login")
        register_rule = config.get_rule("/api/v1/auth/register")
        default_rule = config.get_rule("/unknown", authenticated=True)
        # Auth endpoints should be more restricted than the default
        assert login_rule.limit <= default_rule.limit
        assert register_rule.limit <= default_rule.limit

    def test_export_endpoints_restricted(self):
        config = RateLimitConfig()
        export_rule = config.get_rule("/api/v1/exports")
        default_rule = config.get_rule("/unknown", authenticated=True)
        assert export_rule.limit <= default_rule.limit


# ===========================================================================
# RouteRateLimit tests
# ===========================================================================

class TestRouteRateLimit:

    def test_creation(self):
        rule = RouteRateLimit(limit=10, window=60, group="test")
        assert rule.limit == 10
        assert rule.window == 60
        assert rule.group == "test"

    def test_default_group(self):
        rule = RouteRateLimit(limit=10, window=60)
        assert rule.group == ""


# ===========================================================================
# Global singleton tests
# ===========================================================================

class TestGlobalRateLimitConfig:

    def test_exists(self):
        assert rate_limit_config is not None
        assert isinstance(rate_limit_config, RateLimitConfig)

    def test_has_rules(self):
        assert len(rate_limit_config.rules) > 0

    def test_can_get_rule(self):
        rule = rate_limit_config.get_rule("/api/v1/auth/login")
        assert rule.limit > 0
        assert rule.window > 0


# ===========================================================================
# Edge cases
# ===========================================================================

class TestRateLimitingEdgeCases:

    @pytest.mark.asyncio
    async def test_zero_limit_denied(self):
        """Lua script should deny when limit=0."""
        mock_redis = AsyncMock()
        limiter = RedisRateLimiter(mock_redis)
        mock_script = AsyncMock(return_value=[0, 0])
        mock_redis.register_script = lambda _: mock_script
        allowed, _ = await limiter.check_and_increment("x", 0, 60)
        assert allowed is False

    @pytest.mark.asyncio
    async def test_very_large_limit(self):
        mock_redis = AsyncMock()
        limiter = RedisRateLimiter(mock_redis)
        mock_script = AsyncMock(return_value=[1, 1])
        mock_redis.register_script = lambda _: mock_script
        allowed, _ = await limiter.check_and_increment("x", 999999999, 60)
        assert allowed is True

    def test_build_key_special_chars(self):
        limiter = RedisRateLimiter(AsyncMock())
        assert limiter._build_key("user@example.com") == "rate_limit:user@example.com"

    def test_multiple_configs_independent(self):
        c1 = RateLimitConfig()
        c2 = RateLimitConfig()
        c1.rules["__test__"] = RouteRateLimit(limit=1, window=1, group="test")
        assert "__test__" not in c2.rules
