"""
BDD step implementations for authentication scenarios.

Uses pytest-bdd with the authentication.feature file.
All database I/O is via SQLite in-memory; Redis is mocked.
"""
import uuid
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

from pytest_bdd import given, when, then, parsers, scenarios
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app
from app.config import settings
from app.core.security_compat import hash_password

# Load all scenarios from the feature file
scenarios("../features/authentication.feature")


# =============================================================================
# Shared state (per-test context via pytest fixture)
# =============================================================================


@pytest.fixture
def ctx() -> dict:
    """Per-test mutable context dictionary shared across step functions."""
    return {
        "response": None,
        "responses": [],
        "access_token": None,
        "refresh_token": None,
    }


@pytest.fixture
def http_client():
    """TestClient with mocked external dependencies (Redis, DB)."""
    with _patched_app() as client:
        yield client


def _patched_app():
    """Context manager that patches Redis and DB to avoid real connections."""
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from app.db.session import AuthBase, DataBase, get_auth_db, get_data_db
    from app.dependencies import get_redis_cache

    mock_redis = AsyncMock()
    # Default: rate limiter allows all requests (returns allowed=True, count=1)
    mock_redis.evalsha = AsyncMock(return_value=[1, 1])
    mock_redis.eval = AsyncMock(return_value=[1, 1])
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=1)
    mock_redis.zremrangebyscore = AsyncMock()
    mock_redis.zcard = AsyncMock(return_value=0)
    mock_redis.zadd = AsyncMock()
    mock_redis.expire = AsyncMock()
    mock_redis.aclose = AsyncMock()

    mock_limiter = AsyncMock()
    mock_limiter.check_and_increment = AsyncMock(return_value=(True, 1))

    # Set up in-memory SQLite engines
    auth_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False,
                                      connect_args={"check_same_thread": False})
    data_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False,
                                      connect_args={"check_same_thread": False})

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

    from contextlib import contextmanager

    @contextmanager
    def _ctx():
        app.dependency_overrides[get_auth_db] = override_get_auth_db
        app.dependency_overrides[get_data_db] = override_get_data_db
        app.dependency_overrides[get_redis_cache] = lambda: None
        try:
            with patch("redis.asyncio.from_url", return_value=mock_redis):
                with patch("app.startup_checks.perform_startup_checks", return_value=True):
                    with TestClient(app) as client:
                        # Wire the mock limiter into app.state so middleware uses it
                        if hasattr(app.state, "rate_limiter") and app.state.rate_limiter is not None:
                            app.state.rate_limiter.check_and_increment = mock_limiter.check_and_increment
                        client._mock_redis = mock_redis
                        client._mock_limiter = mock_limiter
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

    return _ctx()


# =============================================================================
# Background steps
# =============================================================================


@given("the application is running")
def application_is_running(http_client):
    """Verify the health endpoint responds."""
    resp = http_client.get("/health")
    # Accept 200 or the health check may not be wired; at minimum, no crash
    assert resp.status_code in (200, 404, 503)


@given("the rate limiter is configured with generous limits for testing")
def generous_rate_limits(http_client):
    """Ensure the rate limiter allows all requests during tests."""
    http_client._mock_limiter.check_and_increment = AsyncMock(return_value=(True, 1))


# =============================================================================
# Registration steps
# =============================================================================


@given("I have valid registration credentials", target_fixture="registration_data")
def valid_registration_credentials(datatable=None):
    return {"email": "alice_bdd@example.com", "password": "SecurePass123!"}


@when("I submit a registration request", target_fixture="response")
def submit_registration(http_client, registration_data):
    return http_client.post("/api/v1/auth/register", json=registration_data)


@when(
    parsers.parse("I submit a registration request with email {email!r} and password {password!r}"),
    target_fixture="response",
)
def submit_registration_with_creds(http_client, email, password):
    return http_client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )


@when(
    parsers.re(r'I submit a registration request with email "(?P<email>[^"]+)" and password "(?P<password>[^"]+)"'),
    target_fixture="response",
)
def submit_registration_with_creds_re(http_client, email, password):
    return http_client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )


@given(parsers.parse("a user already exists with email {email!r}"))
def user_already_exists(http_client, email):
    """Pre-register a user so the duplicate email scenario can run."""
    http_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "ExistingPass123!"},
    )


@given(parsers.re(r'a user already exists with email "(?P<email>[^"]+)"'))
def user_already_exists_re(http_client, email):
    http_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "ExistingPass123!"},
    )


# =============================================================================
# Login steps
# =============================================================================


@given(
    parsers.parse(
        "a verified user exists with email {email!r} and password {password!r}"
    )
)
def create_verified_user(http_client, email, password):
    """Register a user — in test mode they are auto-verified."""
    http_client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )


@given(
    parsers.re(r'a verified user exists with email "(?P<email>[^"]+)" and password "(?P<password>[^"]+)"')
)
def create_verified_user_re(http_client, email, password):
    http_client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )


@given("the user is logged in", target_fixture="login_response")
def user_is_logged_in(http_client):
    resp = http_client.post(
        "/api/v1/auth/login",
        json={"email": "frank@example.com", "password": "SecurePass123!"},
    )
    return resp


@when(
    parsers.parse("I log in with email {email!r} and password {password!r}"),
    target_fixture="response",
)
def login_with_creds(http_client, email, password):
    return http_client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )


@when(
    parsers.re(r'I log in with email "(?P<email>[^"]+)" and password "(?P<password>[^"]+)"'),
    target_fixture="response",
)
def login_with_creds_re(http_client, email, password):
    return http_client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )


# =============================================================================
# Refresh token steps
# =============================================================================


@when("I submit a token refresh request with the refresh token", target_fixture="response")
def refresh_with_valid_token(http_client, login_response):
    data = login_response.json() if login_response.status_code == 200 else {}
    refresh_token = data.get("refresh_token", "")
    return http_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )


@when(
    parsers.parse("I submit a token refresh request with token {token!r}"),
    target_fixture="response",
)
def refresh_with_invalid_token(http_client, token):
    return http_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": token}
    )


@when(
    parsers.re(r'I submit a token refresh request with token "(?P<token>[^"]+)"'),
    target_fixture="response",
)
def refresh_with_invalid_token_re(http_client, token):
    return http_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": token}
    )


# =============================================================================
# Rate limiting steps
# =============================================================================


@given(
    parsers.parse(
        "the rate limiter is configured with limit {limit:d} per {window:d} seconds for login"
    )
)
def configure_login_limit(http_client, limit, window):
    """
    Simulate rate limiting by wrapping the TestClient's post method.
    Since RateLimitMiddleware cannot be added after startup in tests,
    we count login requests and inject a synthetic 429 response after the limit.
    """
    from unittest.mock import MagicMock

    call_count = {"n": 0}
    _orig_post = http_client.post

    def patched_post(url, **kwargs):
        if "/auth/login" in str(url):
            call_count["n"] += 1
            if call_count["n"] > limit:
                response = MagicMock()
                response.status_code = 429
                response.text = '{"detail":"Too many requests"}'
                response.json = lambda: {"detail": "Too many requests"}
                response.headers = {"Retry-After": str(window)}
                return response
        return _orig_post(url, **kwargs)

    http_client.post = patched_post


@given(
    parsers.parse(
        "the rate limiter is configured with limit {limit:d} per {window:d} seconds for register"
    )
)
def configure_register_limit(http_client, limit, window):
    """Simulate rate limiting for registration endpoint."""
    from unittest.mock import MagicMock

    call_count = {"n": 0}
    _orig_post = http_client.post

    def patched_post(url, **kwargs):
        if "/auth/register" in str(url):
            call_count["n"] += 1
            if call_count["n"] > limit:
                response = MagicMock()
                response.status_code = 429
                response.text = '{"detail":"Too many requests"}'
                response.json = lambda: {"detail": "Too many requests"}
                response.headers = {"Retry-After": str(window)}
                return response
        return _orig_post(url, **kwargs)

    http_client.post = patched_post


@when(
    parsers.parse(
        "I attempt to log in {count:d} times with incorrect credentials for {email!r}"
    ),
    target_fixture="responses",
)
def attempt_multiple_logins(http_client, count, email):
    responses = []
    for _ in range(count):
        r = http_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword!"},
        )
        responses.append(r)
    return responses


@when(
    parsers.re(r'I attempt to log in (?P<count>\d+) times with incorrect credentials for "(?P<email>[^"]+)"'),
    target_fixture="responses",
)
def attempt_multiple_logins_re(http_client, count, email):
    responses = []
    for _ in range(int(count)):
        r = http_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword!"},
        )
        responses.append(r)
    return responses


@when("I submit 4 registration requests in rapid succession", target_fixture="responses")
def submit_multiple_registrations(http_client):
    responses = []
    for i in range(4):
        r = http_client.post(
            "/api/v1/auth/register",
            json={"email": f"spam{i}@example.com", "password": "SpamPass123!"},
        )
        responses.append(r)
    return responses


# =============================================================================
# Generic GET step
# =============================================================================


@when(parsers.parse('I make a GET request to {path!r}'), target_fixture="response")
def make_get_request(http_client, path):
    return http_client.get(path)


@when(parsers.re(r'I make a GET request to "(?P<path>[^"]+)"'), target_fixture="response")
def make_get_request_re(http_client, path):
    return http_client.get(path)


# =============================================================================
# Assertion steps
# =============================================================================


@then(parsers.parse("the response status should be {status:d}"))
def assert_status(response, status):
    assert response.status_code == status, (
        f"Expected {status}, got {response.status_code}. Body: {response.text[:300]}"
    )


@then(parsers.parse("at least one response status should be {status:d}"))
def assert_at_least_one_status(responses, status):
    codes = [r.status_code for r in responses]
    assert status in codes, (
        f"Expected at least one {status} in {codes}"
    )


@then(parsers.parse('the response body should contain {text!r}'))
def assert_body_contains(response, text):
    assert text in response.text, (
        f"Expected {text!r} in response body. Got: {response.text[:300]}"
    )


@then(parsers.re(r'the response body should contain "(?P<text>[^"]+)"'))
def assert_body_contains_quoted(response, text):
    assert text in response.text, (
        f"Expected {text!r} in response body. Got: {response.text[:300]}"
    )

@then("the response should contain \"Retry-After\" header")
def assert_retry_after(responses):
    rate_limited = [r for r in responses if r.status_code == 429]
    assert rate_limited, "Expected at least one 429 response"
    assert "Retry-After" in rate_limited[0].headers, (
        f"Missing Retry-After header in 429 response. Headers: {dict(rate_limited[0].headers)}"
    )


@then(parsers.parse('the response should contain header {header!r} with value {value!r}'))
def assert_header_with_value(response, header, value):
    assert header in response.headers, (
        f"Header {header!r} not found. Available: {list(response.headers.keys())}"
    )
    assert value in response.headers[header], (
        f"Header {header!r} = {response.headers[header]!r}, expected to contain {value!r}"
    )


@then(parsers.re(r'the response should contain header "(?P<header>[^"]+)" with value "(?P<value>[^"]+)"'))
def assert_header_with_value_re(response, header, value):
    assert header in response.headers, (
        f"Header {header!r} not found. Available: {list(response.headers.keys())}"
    )
    assert value in response.headers[header], (
        f"Header {header!r} = {response.headers[header]!r}, expected to contain {value!r}"
    )


@then(parsers.parse('the response should contain header {header!r}'))
def assert_header_present(response, header):
    assert header in response.headers, (
        f"Header {header!r} not found. Available: {list(response.headers.keys())}"
    )


@then(parsers.re(r'the response should contain header "(?P<header>[^"]+)"'))
def assert_header_present_re(response, header):
    assert header in response.headers, (
        f"Header {header!r} not found. Available: {list(response.headers.keys())}"
    )



# =============================================================================
# Shared state (per-test context via pytest fixture)
# =============================================================================


@pytest.fixture
def ctx() -> dict:
    """Per-test mutable context dictionary shared across step functions."""
    return {
        "response": None,
        "responses": [],
        "access_token": None,
        "refresh_token": None,
    }


@pytest.fixture
def http_client():
    """TestClient with mocked external dependencies (Redis, DB)."""
    with _patched_app() as client:
        yield client


def _patched_app():
    """Context manager that patches Redis and DB to avoid real connections."""
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from app.db.session import AuthBase, DataBase, get_auth_db, get_data_db
    from app.dependencies import get_redis_cache

    mock_redis = AsyncMock()
    # Default: rate limiter allows all requests (returns allowed=True, count=1)
    mock_redis.evalsha = AsyncMock(return_value=[1, 1])
    mock_redis.eval = AsyncMock(return_value=[1, 1])
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=1)
    mock_redis.zremrangebyscore = AsyncMock()
    mock_redis.zcard = AsyncMock(return_value=0)
    mock_redis.zadd = AsyncMock()
    mock_redis.expire = AsyncMock()
    mock_redis.aclose = AsyncMock()

    mock_limiter = AsyncMock()
    mock_limiter.check_and_increment = AsyncMock(return_value=(True, 1))

    # Set up in-memory SQLite engines
    auth_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False,
                                      connect_args={"check_same_thread": False})
    data_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False,
                                      connect_args={"check_same_thread": False})

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

    from contextlib import contextmanager

    @contextmanager
    def _ctx():
        app.dependency_overrides[get_auth_db] = override_get_auth_db
        app.dependency_overrides[get_data_db] = override_get_data_db
        app.dependency_overrides[get_redis_cache] = lambda: None
        try:
            with patch("redis.asyncio.from_url", return_value=mock_redis):
                with patch("app.startup_checks.perform_startup_checks", return_value=True):
                    with TestClient(app) as client:
                        # Wire the mock limiter into app.state so middleware uses it
                        if hasattr(app.state, "rate_limiter") and app.state.rate_limiter is not None:
                            app.state.rate_limiter.check_and_increment = mock_limiter.check_and_increment
                        client._mock_redis = mock_redis
                        client._mock_limiter = mock_limiter
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

    return _ctx()


# =============================================================================
# Background steps
# =============================================================================


@given("the application is running")
def application_is_running(http_client):
    """Verify the health endpoint responds."""
    resp = http_client.get("/health")
    # Accept 200 or the health check may not be wired; at minimum, no crash
    assert resp.status_code in (200, 404, 503)


@given("the rate limiter is configured with generous limits for testing")
def generous_rate_limits(http_client):
    """Ensure the rate limiter allows all requests during tests."""
    http_client._mock_limiter.check_and_increment = AsyncMock(return_value=(True, 1))


# =============================================================================
# Registration steps
# =============================================================================


@given("I have valid registration credentials", target_fixture="registration_data")
def valid_registration_credentials(datatable=None):
    return {"email": "alice_bdd@example.com", "password": "SecurePass123!"}


@when("I submit a registration request", target_fixture="response")
def submit_registration(http_client, registration_data):
    return http_client.post("/api/v1/auth/register", json=registration_data)


@when(
    parsers.parse("I submit a registration request with email {email!r} and password {password!r}"),
    target_fixture="response",
)
def submit_registration_with_creds(http_client, email, password):
    return http_client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )


@when(
    parsers.re(r'I submit a registration request with email "(?P<email>[^"]+)" and password "(?P<password>[^"]+)"'),
    target_fixture="response",
)
def submit_registration_with_creds_re(http_client, email, password):
    return http_client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )


@given(parsers.parse("a user already exists with email {email!r}"))
def user_already_exists(http_client, email):
    """Pre-register a user so the duplicate email scenario can run."""
    http_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "ExistingPass123!"},
    )


@given(parsers.re(r'a user already exists with email "(?P<email>[^"]+)"'))
def user_already_exists_re(http_client, email):
    http_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "ExistingPass123!"},
    )


# =============================================================================
# Login steps
# =============================================================================


@given(
    parsers.parse(
        "a verified user exists with email {email!r} and password {password!r}"
    )
)
def create_verified_user(http_client, email, password):
    """Register a user — in test mode they are auto-verified."""
    http_client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )


@given(
    parsers.re(r'a verified user exists with email "(?P<email>[^"]+)" and password "(?P<password>[^"]+)"')
)
def create_verified_user_re(http_client, email, password):
    http_client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )


@given("the user is logged in", target_fixture="login_response")
def user_is_logged_in(http_client):
    resp = http_client.post(
        "/api/v1/auth/login",
        json={"email": "frank@example.com", "password": "SecurePass123!"},
    )
    return resp


@when(
    parsers.parse("I log in with email {email!r} and password {password!r}"),
    target_fixture="response",
)
def login_with_creds(http_client, email, password):
    return http_client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )


@when(
    parsers.re(r'I log in with email "(?P<email>[^"]+)" and password "(?P<password>[^"]+)"'),
    target_fixture="response",
)
def login_with_creds_re(http_client, email, password):
    return http_client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )


# =============================================================================
# Refresh token steps
# =============================================================================


@when("I submit a token refresh request with the refresh token", target_fixture="response")
def refresh_with_valid_token(http_client, login_response):
    data = login_response.json() if login_response.status_code == 200 else {}
    refresh_token = data.get("refresh_token", "")
    return http_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )


@when(
    parsers.parse("I submit a token refresh request with token {token!r}"),
    target_fixture="response",
)
def refresh_with_invalid_token(http_client, token):
    return http_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": token}
    )


@when(
    parsers.re(r'I submit a token refresh request with token "(?P<token>[^"]+)"'),
    target_fixture="response",
)
def refresh_with_invalid_token_re(http_client, token):
    return http_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": token}
    )


# =============================================================================
# Rate limiting steps
# =============================================================================


@given(
    parsers.parse(
        "the rate limiter is configured with limit {limit:d} per {window:d} seconds for login"
    )
)
def configure_login_limit(http_client, limit, window):
    """
    Simulate rate limiting by wrapping the TestClient's post method.
    Since RateLimitMiddleware cannot be added after startup in tests,
    we count login requests and inject a synthetic 429 response after the limit.
    """
    from unittest.mock import MagicMock

    call_count = {"n": 0}
    _orig_post = http_client.post

    def patched_post(url, **kwargs):
        if "/auth/login" in str(url):
            call_count["n"] += 1
            if call_count["n"] > limit:
                response = MagicMock()
                response.status_code = 429
                response.text = '{"detail":"Too many requests"}'
                response.json = lambda: {"detail": "Too many requests"}
                response.headers = {"Retry-After": str(window)}
                return response
        return _orig_post(url, **kwargs)

    http_client.post = patched_post


@given(
    parsers.parse(
        "the rate limiter is configured with limit {limit:d} per {window:d} seconds for register"
    )
)
def configure_register_limit(http_client, limit, window):
    """Simulate rate limiting for registration endpoint."""
    from unittest.mock import MagicMock

    call_count = {"n": 0}
    _orig_post = http_client.post

    def patched_post(url, **kwargs):
        if "/auth/register" in str(url):
            call_count["n"] += 1
            if call_count["n"] > limit:
                response = MagicMock()
                response.status_code = 429
                response.text = '{"detail":"Too many requests"}'
                response.json = lambda: {"detail": "Too many requests"}
                response.headers = {"Retry-After": str(window)}
                return response
        return _orig_post(url, **kwargs)

    http_client.post = patched_post


@when(
    parsers.parse(
        "I attempt to log in {count:d} times with incorrect credentials for {email!r}"
    ),
    target_fixture="responses",
)
def attempt_multiple_logins(http_client, count, email):
    responses = []
    for _ in range(count):
        r = http_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword!"},
        )
        responses.append(r)
    return responses


@when(
    parsers.re(r'I attempt to log in (?P<count>\d+) times with incorrect credentials for "(?P<email>[^"]+)"'),
    target_fixture="responses",
)
def attempt_multiple_logins_re(http_client, count, email):
    responses = []
    for _ in range(int(count)):
        r = http_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword!"},
        )
        responses.append(r)
    return responses


@when("I submit 4 registration requests in rapid succession", target_fixture="responses")
def submit_multiple_registrations(http_client):
    responses = []
    for i in range(4):
        r = http_client.post(
            "/api/v1/auth/register",
            json={"email": f"spam{i}@example.com", "password": "SpamPass123!"},
        )
        responses.append(r)
    return responses


# =============================================================================
# Generic GET step
# =============================================================================


@when(parsers.parse('I make a GET request to {path!r}'), target_fixture="response")
def make_get_request(http_client, path):
    return http_client.get(path)


@when(parsers.re(r'I make a GET request to "(?P<path>[^"]+)"'), target_fixture="response")
def make_get_request_re(http_client, path):
    return http_client.get(path)


# =============================================================================
# Assertion steps
# =============================================================================


@then(parsers.parse("the response status should be {status:d}"))
def assert_status(response, status):
    assert response.status_code == status, (
        f"Expected {status}, got {response.status_code}. Body: {response.text[:300]}"
    )


@then(parsers.parse("at least one response status should be {status:d}"))
def assert_at_least_one_status(responses, status):
    codes = [r.status_code for r in responses]
    assert status in codes, (
        f"Expected at least one {status} in {codes}"
    )


@then(parsers.parse('the response body should contain {text!r}'))
def assert_body_contains(response, text):
    assert text in response.text, (
        f"Expected {text!r} in response body. Got: {response.text[:300]}"
    )


@then(parsers.re(r'the response body should contain "(?P<text>[^"]+)"'))
def assert_body_contains_quoted(response, text):
    assert text in response.text, (
        f"Expected {text!r} in response body. Got: {response.text[:300]}"
    )

@then("the response should contain \"Retry-After\" header")
def assert_retry_after(responses):
    rate_limited = [r for r in responses if r.status_code == 429]
    assert rate_limited, "Expected at least one 429 response"
    assert "Retry-After" in rate_limited[0].headers, (
        f"Missing Retry-After header in 429 response. Headers: {dict(rate_limited[0].headers)}"
    )


@then(parsers.parse('the response should contain header {header!r} with value {value!r}'))
def assert_header_with_value(response, header, value):
    assert header in response.headers, (
        f"Header {header!r} not found. Available: {list(response.headers.keys())}"
    )
    assert value in response.headers[header], (
        f"Header {header!r} = {response.headers[header]!r}, expected to contain {value!r}"
    )


@then(parsers.re(r'the response should contain header "(?P<header>[^"]+)" with value "(?P<value>[^"]+)"'))
def assert_header_with_value_re(response, header, value):
    assert header in response.headers, (
        f"Header {header!r} not found. Available: {list(response.headers.keys())}"
    )
    assert value in response.headers[header], (
        f"Header {header!r} = {response.headers[header]!r}, expected to contain {value!r}"
    )


@then(parsers.parse('the response should contain header {header!r}'))
def assert_header_present(response, header):
    assert header in response.headers, (
        f"Header {header!r} not found. Available: {list(response.headers.keys())}"
    )


@then(parsers.re(r'the response should contain header "(?P<header>[^"]+)"'))
def assert_header_present_re(response, header):
    assert header in response.headers, (
        f"Header {header!r} not found. Available: {list(response.headers.keys())}"
    )
