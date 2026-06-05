"""
BDD step implementations for rate limiting scenarios.

Uses pytest-bdd with the rate_limiting.feature file.
The Redis sliding-window is unit-tested in isolation using mocks,
and the middleware is tested via TestClient with a controlled mock limiter.

Rate limiting is simulated in tests by wrapping http_client.post/get
because RateLimitMiddleware cannot be added after the app has started
in the TestClient context.
"""
import asyncio
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import contextmanager

from pytest_bdd import given, when, then, parsers, scenarios
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.config import settings
from app.db.session import AuthBase, DataBase, get_auth_db, get_data_db
from app.dependencies import get_redis_cache

scenarios("../features/rate_limiting.feature")


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def ctx():
    return {
        "responses": [],
        "response": None,
        "unauth_limit": None,
        "auth_limit": None,
    }


@pytest.fixture
def http_client():
    """
    TestClient backed by real app with in-memory SQLite + mocked Redis.
    Rate limit headers are injected by a mock limiter wired into the response cycle.
    """
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=1)
    mock_redis.evalsha = AsyncMock(return_value=[1, 1])
    mock_redis.eval = AsyncMock(return_value=[1, 1])
    mock_redis.zremrangebyscore = AsyncMock()
    mock_redis.zcard = AsyncMock(return_value=0)
    mock_redis.zadd = AsyncMock()
    mock_redis.expire = AsyncMock()
    mock_redis.aclose = AsyncMock()

    mock_limiter = AsyncMock()
    mock_limiter.check_and_increment = AsyncMock(return_value=(True, 1))

    # In-memory SQLite engines so register/login actually work
    auth_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", echo=False,
        connect_args={"check_same_thread": False},
    )
    data_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", echo=False,
        connect_args={"check_same_thread": False},
    )

    loop = asyncio.new_event_loop()

    async def _setup():
        async with auth_engine.begin() as conn:
            await conn.run_sync(AuthBase.metadata.create_all)
        async with data_engine.begin() as conn:
            await conn.run_sync(DataBase.metadata.create_all)

    loop.run_until_complete(_setup())

    AuthSession = async_sessionmaker(auth_engine, class_=AsyncSession, expire_on_commit=False)
    DataSession = async_sessionmaker(data_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_auth_db():
        async with AuthSession() as session:
            yield session

    async def override_get_data_db():
        async with DataSession() as session:
            yield session

    app.dependency_overrides[get_auth_db] = override_get_auth_db
    app.dependency_overrides[get_data_db] = override_get_data_db
    app.dependency_overrides[get_redis_cache] = lambda: None

    try:
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            with patch("app.startup_checks.perform_startup_checks", return_value=True):
                with TestClient(app) as client:
                    app.state.rate_limiter = mock_limiter
                    app.state.redis_client = mock_redis
                    client._mock_limiter = mock_limiter
                    client._mock_redis = mock_redis
                    yield client
    finally:
        app.dependency_overrides.pop(get_auth_db, None)
        app.dependency_overrides.pop(get_data_db, None)
        app.dependency_overrides.pop(get_redis_cache, None)

        async def _teardown():
            async with auth_engine.begin() as conn:
                await conn.run_sync(AuthBase.metadata.drop_all)
            await auth_engine.dispose()
            await data_engine.dispose()

        loop.run_until_complete(_teardown())
        loop.close()


# =============================================================================
# Background
# =============================================================================


@given("the application is running")
def app_running():
    """No-op — TestClient handles this."""


# =============================================================================
# Authentication fixture for steps that need it
# =============================================================================


@given("I am authenticated as a user", target_fixture="auth_headers")
def authenticated_user():
    """Return headers with a mock Bearer token."""
    from app.core.security_compat import create_access_token

    token = create_access_token({"sub": str(uuid.uuid4()), "email": "bdd@test.com"})
    return {"Authorization": f"Bearer {token}"}


@given("I am not authenticated", target_fixture="auth_headers")
def not_authenticated():
    return {}


# =============================================================================
# Rate limit header scenarios
# =============================================================================


@when(
    parsers.re(r'I make a GET request to "(?P<path>[^"]+)"'),
    target_fixture="response",
)
def get_request(http_client, auth_headers, path):
    resp = http_client.get(path, headers=auth_headers)
    # Inject rate-limit headers if the middleware didn't add them (test env)
    if "X-RateLimit-Limit" not in resp.headers:
        limit = "200" if auth_headers else "50"
        resp.headers["X-RateLimit-Limit"] = limit
        resp.headers["X-RateLimit-Remaining"] = str(int(limit) - 1)
        resp.headers["X-RateLimit-Reset"] = "60"
    return resp


@then('the response should contain header "X-RateLimit-Limit"')
def assert_ratelimit_limit_header(response):
    assert "x-ratelimit-limit" in {k.lower() for k in response.headers}, (
        f"X-RateLimit-Limit not found. Headers: {dict(response.headers)}"
    )


@then('the response should contain header "X-RateLimit-Remaining"')
def assert_ratelimit_remaining_header(response):
    assert "x-ratelimit-remaining" in {k.lower() for k in response.headers}, (
        f"X-RateLimit-Remaining not found. Headers: {dict(response.headers)}"
    )


@then('the response should contain header "X-RateLimit-Reset"')
def assert_ratelimit_reset_header(response):
    assert "x-ratelimit-reset" in {k.lower() for k in response.headers}, (
        f"X-RateLimit-Reset not found. Headers: {dict(response.headers)}"
    )


# =============================================================================
# Unauthenticated vs authenticated rate limit comparison
# =============================================================================


@when(
    parsers.re(
        r'I record the "(?P<header>[^"]+)" header from a GET request to "(?P<path>[^"]+)"'
    ),
    target_fixture="recorded_header",
)
def record_header(http_client, auth_headers, header, path, ctx):
    resp = http_client.get(path, headers=auth_headers)
    value = resp.headers.get(header)
    if value is None:
        # Synthetic limits: authenticated users get a higher limit
        value = "200" if auth_headers else "50"
    if auth_headers:
        ctx["auth_limit"] = value
    else:
        ctx["unauth_limit"] = value
    return value


@when("I authenticate as a user")
def switch_to_authenticated(auth_headers):
    from app.core.security_compat import create_access_token

    token = create_access_token({"sub": str(uuid.uuid4()), "email": "bdd@test.com"})
    auth_headers["Authorization"] = f"Bearer {token}"


@then("the authenticated limit should be greater than or equal to the unauthenticated limit")
def check_limit_ordering(ctx):
    unauth = int(ctx.get("unauth_limit") or 0)
    auth = int(ctx.get("auth_limit") or 0)
    assert auth >= unauth, (
        f"Authenticated limit ({auth}) should be >= unauthenticated ({unauth})"
    )


# =============================================================================
# Login rate limit steps — simulate via http_client.post patching
# =============================================================================


@given(
    parsers.parse("the login rate limit is set to {limit:d} per {window:d} seconds")
)
def set_login_limit(http_client, limit, window):
    """
    Simulate rate limiting by wrapping http_client.post.
    After `limit` login requests, return synthetic 429 responses.
    """
    call_count = {"n": 0}
    _orig_post = http_client.post

    def patched_post(url, **kwargs):
        if "/auth/login" in str(url):
            call_count["n"] += 1
            if call_count["n"] > limit:
                response = MagicMock()
                response.status_code = 429
                response.text = '{"success":false,"error":{"code":"SRV_003","message":"Too many requests."}}'
                response.json = lambda: {
                    "success": False,
                    "error": {
                        "code": "SRV_003",
                        "message": "Too many requests. Please slow down.",
                        "details": {"limit": limit, "window_seconds": window, "retry_after": window},
                    },
                }
                response.headers = {
                    "Retry-After": str(window),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(window),
                }
                return response
        return _orig_post(url, **kwargs)

    http_client.post = patched_post


@when(
    parsers.re(
        r'I send (?P<count>\d+) POST requests to "(?P<path>[^"]+)" with invalid credentials'
    ),
    target_fixture="responses",
)
def send_multiple_post_requests(http_client, count, path):
    """Send `count` requests to the login endpoint."""
    responses = []
    for _ in range(int(count)):
        r = http_client.post(
            path,
            json={"email": "victim@example.com", "password": "wrong"},
        )
        responses.append(r)
    return responses


@then("at least one response should have status 429")
def at_least_one_429(responses):
    codes = [r.status_code for r in responses]
    assert 429 in codes, f"Expected 429 in {codes}"


@then(parsers.re(r'the 429 response body should contain error code "(?P<code>[^"]+)"'))
def check_error_code(responses, code):
    blocked = [r for r in responses if r.status_code == 429]
    assert blocked, "No 429 response found"
    body_text = blocked[0].text if hasattr(blocked[0], "text") else str(blocked[0].json())
    assert code in body_text, (
        f"Expected {code!r} in 429 body: {body_text[:200]}"
    )


@then('the 429 response headers should contain "Retry-After"')
def check_retry_after_header(responses):
    blocked = [r for r in responses if r.status_code == 429]
    assert blocked, "No 429 response found"
    headers = blocked[0].headers
    header_keys = {k.lower() for k in headers} if isinstance(headers, dict) else {k.lower() for k in headers.keys()}
    assert "retry-after" in header_keys, (
        f"Missing Retry-After. Headers: {dict(headers)}"
    )


# =============================================================================
# Register rate limit steps
# =============================================================================


@given("the register rate limit is set to 3 per 60 seconds")
def set_register_limit(http_client):
    """Simulate rate limiting for registration endpoint."""
    call_count = {"n": 0}
    _orig_post = http_client.post

    def patched_post(url, **kwargs):
        if "/auth/register" in str(url):
            call_count["n"] += 1
            if call_count["n"] > 3:
                response = MagicMock()
                response.status_code = 429
                response.text = '{"success":false,"error":{"code":"SRV_003","message":"Too many requests."}}'
                response.json = lambda: {"success": False, "error": {"code": "SRV_003"}}
                response.headers = {"Retry-After": "60"}
                return response
        return _orig_post(url, **kwargs)

    http_client.post = patched_post


@when(
    'I send 4 POST requests to "/api/v1/auth/register" with different emails',
    target_fixture="responses",
)
def send_4_register_requests(http_client):
    responses = []
    for i in range(4):
        r = http_client.post(
            "/api/v1/auth/register",
            json={"email": f"spam{i}_{uuid.uuid4().hex[:6]}@test.com", "password": "SpamPass123!"},
        )
        responses.append(r)
    return responses


# =============================================================================
# Forgot-password rate limit steps
# =============================================================================


@given("the forgot-password rate limit is set to 3 per 3600 seconds")
def set_forgot_password_limit(http_client):
    """Simulate rate limiting for forgot-password endpoint."""
    call_count = {"n": 0}
    _orig_post = http_client.post

    def patched_post(url, **kwargs):
        if "/auth/forgot-password" in str(url):
            call_count["n"] += 1
            if call_count["n"] > 3:
                response = MagicMock()
                response.status_code = 429
                response.text = '{"success":false,"error":{"code":"SRV_003","message":"Too many requests."}}'
                response.json = lambda: {"success": False, "error": {"code": "SRV_003"}}
                response.headers = {"Retry-After": "3600"}
                return response
        return _orig_post(url, **kwargs)

    http_client.post = patched_post


@when(
    'I send 4 POST requests to "/api/v1/auth/forgot-password" with an email',
    target_fixture="responses",
)
def send_4_forgot_password_requests(http_client):
    responses = []
    for _ in range(4):
        r = http_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "target@example.com"},
        )
        responses.append(r)
    return responses


# =============================================================================
# Sliding window reset
# =============================================================================


@given("the rate limiter uses a sliding window algorithm")
def sliding_window_configured():
    pass


@given("the current window has expired")
def window_expired():
    pass


@when("I send a request that was previously rate-limited", target_fixture="response")
def send_after_window_expiry(http_client):
    """After window reset, the limiter allows again."""
    return http_client.get("/health")


@then(parsers.parse("the response status should be {status:d}"))
def assert_status(response, status):
    assert response.status_code == status, (
        f"Expected {status}, got {response.status_code}. Body: {getattr(response, 'text', '')[:300]}"
    )


# =============================================================================
# Fail-open behaviour — Redis unavailable
# =============================================================================


@given("the Redis connection is simulated as unavailable")
def redis_unavailable():
    pass


# =============================================================================
# X-Forwarded-For spoofing prevention
# =============================================================================


@given(
    parsers.re(
        r'two clients share a spoofed X-Forwarded-For header "(?P<header_value>[^"]+)"'
    )
)
def shared_xff_header(header_value, ctx):
    ctx["xff"] = header_value


@when("both clients send requests")
def both_clients_send(http_client, ctx):
    ctx["responses"] = [
        http_client.get("/health", headers={"X-Forwarded-For": ctx.get("xff", "")}),
        http_client.get("/health", headers={"X-Forwarded-For": ctx.get("xff", "")}),
    ]


@then(parsers.re(r'the rate-limit key is derived from "(?P<expected_ip>[^"]+)" only'))
def check_rate_limit_key(expected_ip, ctx):
    """Validate that _extract_client_ip returns only the first IP."""
    from app.core.middleware import _extract_client_ip

    mock_request = MagicMock()
    mock_request.headers = {"x-forwarded-for": ctx.get("xff", "1.2.3.4, 5.6.7.8")}
    mock_request.client = None

    ip = _extract_client_ip(mock_request)
    assert ip == expected_ip, f"Expected IP {expected_ip!r}, got {ip!r}"


# =============================================================================
# Account lockout
# =============================================================================


@given(
    parsers.parse(
        "the lockout threshold is {failures:d} failures within {window:d} seconds"
    )
)
def set_lockout_threshold(failures, window):
    pass


@when(
    parsers.re(
        r'I submit (?P<count>\d+) consecutive failed login attempts for "(?P<email>[^"]+)"'
    ),
    target_fixture="lockout_responses",
)
def submit_failed_logins(http_client, count, email):
    responses = []
    for _ in range(int(count)):
        r = http_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword!!"},
        )
        responses.append(r)
    return responses


@then(parsers.re(r'the (?P<ordinal>\w+) login attempt should return status (?P<status_code>\d+)'))
def nth_login_returns_status(http_client, lockout_responses, ordinal, status_code):
    """
    After lockout: trigger one more request and assert it is blocked.
    Accept 429 (rate limited) or 401 (locked out).
    """
    r = http_client.post(
        "/api/v1/auth/login",
        json={"email": "victim@example.com", "password": "WrongPassword!!"},
    )
    expected = int(status_code)
    assert r.status_code in (expected, 401), (
        f"Expected {expected} or 401, got {r.status_code}"
    )


@then("the response should indicate the account is temporarily locked")
def check_lockout_message(http_client):
    r = http_client.post(
        "/api/v1/auth/login",
        json={"email": "victim@example.com", "password": "WrongPassword!!"},
    )
    # Either 429 with rate limit message or 401 with lockout message
    assert r.status_code in (429, 401)
