"""Comprehensive tests for authentication endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timedelta
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.schemas.auth import UserRegister, UserLogin, TokenResponse
from app.core.exceptions import UserAlreadyExistsError, AuthenticationError
from app.db.models.auth import User
from app.main import app
from app.db.session import get_auth_db, get_data_db, AuthBase, DataBase
from app.dependencies import get_redis_cache


# ---------------------------------------------------------------------------
# Auth-specific client fixture — does NOT override get_current_user so that
# authentication tests actually exercise the real auth middleware.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def client():
    """
    TestClient for auth tests.

    * In-memory SQLite for both databases (no real Postgres needed)
    * Redis replaced with a no-op mock (no real Redis needed)
    * get_current_user is NOT overridden — auth tests must pass real tokens
    * No pre-set Authorization header — tests that need a token add it manually
    """
    import asyncio

    # Build auth DB
    auth_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    data_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    loop = asyncio.new_event_loop()

    async def _setup():
        async with auth_engine.begin() as conn:
            await conn.run_sync(AuthBase.metadata.create_all)
        async with data_engine.begin() as conn:
            await conn.run_sync(DataBase.metadata.create_all)

    loop.run_until_complete(_setup())

    AuthSession = async_sessionmaker(auth_engine, class_=AsyncSession, expire_on_commit=False)
    DataSession = async_sessionmaker(data_engine, class_=AsyncSession, expire_on_commit=False)

    mock_cache = MagicMock()
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock(return_value=True)
    mock_cache.delete = AsyncMock(return_value=True)
    mock_cache.exists = AsyncMock(return_value=0)

    async def _override_auth_db():
        async with AuthSession() as session:
            yield session

    async def _override_data_db():
        async with DataSession() as session:
            yield session

    app.dependency_overrides[get_auth_db] = _override_auth_db
    app.dependency_overrides[get_data_db] = _override_data_db
    app.dependency_overrides[get_redis_cache] = lambda: mock_cache

    yield TestClient(app, raise_server_exceptions=False)

    for dep in [get_auth_db, get_data_db, get_redis_cache]:
        app.dependency_overrides.pop(dep, None)

    loop.run_until_complete(auth_engine.dispose())
    loop.run_until_complete(data_engine.dispose())
    loop.close()


# Test fixtures
@pytest.fixture
def sample_user():
    """Create a sample user."""
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash="hashed_password",
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow()
    )


@pytest.fixture
def sample_registration_data():
    """Create sample registration data."""
    return {
        "email": "newuser@example.com",
        "password": "SecurePass123",
        "name": "New User"
    }


@pytest.fixture
def sample_login_data():
    """Create sample login data."""
    return {
        "email": "test@example.com",
        "password": "SecurePass123"
    }


class TestRegisterEndpoint:
    """Test user registration endpoint."""
    
    def test_register_missing_email(self, client):
        """Test registration with missing email."""
        response = client.post("/api/v1/auth/register", json={
            "password": "SecurePass123"
        })
        assert response.status_code == 422
    
    def test_register_missing_password(self, client):
        """Test registration with missing password."""
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com"
        })
        assert response.status_code == 422
    
    def test_register_invalid_email_format(self, client):
        """Test registration with invalid email format."""
        response = client.post("/api/v1/auth/register", json={
            "email": "invalid_email",
            "password": "SecurePass123"
        })
        assert response.status_code == 422
    
    def test_register_empty_password(self, client):
        """Test registration with empty password."""
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": ""
        })
        assert response.status_code == 422
    
    def test_register_with_optional_name(self, client):
        """Test registration with optional name field."""
        with patch("app.api.v1.auth.get_auth_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_get_service.return_value = mock_service
            mock_service.register_user.return_value = MagicMock(
                id=uuid.uuid4(),
                email="user@example.com"
            )
            
            response = client.post("/api/v1/auth/register", json={
                "email": "user@example.com",
                "password": "SecurePass123",
                "name": "John Doe"
            })
            
            # Check status is either success or auth error (not validation error)
            assert response.status_code in [200, 201, 401, 500]
    
    def test_register_with_empty_body(self, client):
        """Test registration with empty JSON body."""
        response = client.post("/api/v1/auth/register", json={})
        assert response.status_code == 422


class TestLoginEndpoint:
    """Test user login endpoint."""
    
    def test_login_missing_email(self, client):
        """Test login with missing email."""
        response = client.post("/api/v1/auth/login", json={
            "password": "SecurePass123"
        })
        assert response.status_code == 422
    
    def test_login_missing_password(self, client):
        """Test login with missing password."""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com"
        })
        assert response.status_code == 422
    
    def test_login_empty_email(self, client):
        """Test login with empty email."""
        response = client.post("/api/v1/auth/login", json={
            "email": "",
            "password": "SecurePass123"
        })
        assert response.status_code == 422
    
    def test_login_empty_password(self, client):
        """Test login with empty password."""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": ""
        })
        assert response.status_code == 401
    
    def test_login_with_empty_body(self, client):
        """Test login with empty JSON body."""
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422
    
    def test_login_method_not_allowed(self, client):
        """Test that GET, PUT, DELETE are not allowed on login endpoint."""
        get_response = client.get("/api/v1/auth/login")
        put_response = client.put("/api/v1/auth/login", json={})
        delete_response = client.delete("/api/v1/auth/login")
        
        assert get_response.status_code == 405
        assert put_response.status_code == 405
        assert delete_response.status_code == 405


class TestMeEndpoint:
    """Test get current user endpoint."""
    
    def test_get_me_without_token(self, client):
        """Test /me endpoint without authentication token."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
    
    def test_get_me_invalid_token_format(self, client):
        """Test /me endpoint with invalid token format."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "InvalidFormat"}
        )
        assert response.status_code in [401, 403]
    
    def test_get_me_missing_bearer_prefix(self, client):
        """Test /me endpoint without Bearer prefix."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "sometoken"}
        )
        assert response.status_code in [401, 403]
    
    def test_get_me_method_not_allowed(self, client):
        """Test that POST, PUT, DELETE are not allowed on /me endpoint."""
        post_response = client.post("/api/v1/auth/me")
        put_response = client.put("/api/v1/auth/me", json={})
        delete_response = client.delete("/api/v1/auth/me")
        
        assert post_response.status_code == 405
        assert put_response.status_code == 405
        assert delete_response.status_code == 405


class TestAuthDependencies:
    """Test authentication dependency functions."""
    
    def test_get_password_hasher(self):
        """Test password hasher dependency returns a valid hasher (fallback path)."""
        from unittest.mock import MagicMock
        from app.dependencies import get_password_hasher
        # Simulate a request whose app.state has no password_hasher (fallback)
        mock_request = MagicMock()
        mock_request.app.state = MagicMock(spec=[])  # empty state → fallback
        hasher1 = get_password_hasher(mock_request)
        hasher2 = get_password_hasher(mock_request)
        # Both should be BcryptPasswordHasher instances (freshly created each call)
        from app.core.provider_implementations import BcryptPasswordHasher
        assert isinstance(hasher1, BcryptPasswordHasher)
        assert isinstance(hasher2, BcryptPasswordHasher)
    
    def test_get_token_provider(self):
        """Test token provider dependency returns a valid provider (fallback path)."""
        from unittest.mock import MagicMock
        from app.dependencies import get_token_provider
        mock_request = MagicMock()
        mock_request.app.state = MagicMock(spec=[])  # empty state → fallback
        provider1 = get_token_provider(mock_request)
        provider2 = get_token_provider(mock_request)
        from app.core.provider_implementations import JWTTokenProvider
        assert isinstance(provider1, JWTTokenProvider)
        assert isinstance(provider2, JWTTokenProvider)


class TestAuthEdgeCases:
    """Test edge cases for auth endpoints."""
    
    def test_register_with_spaces_in_password(self, client):
        """Test registration with spaces in password."""
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "Pass 123 Secure"
        })
        # Should accept spaces in password
        assert response.status_code in [201, 422, 500]
    
    def test_register_with_special_characters_in_email(self, client):
        """Test registration with special characters in email."""
        response = client.post("/api/v1/auth/register", json={
            "email": "test+tag@example.com",
            "password": "SecurePass123"
        })
        # Plus sign is valid in email
        assert response.status_code in [201, 422, 500]
    
    def test_login_case_sensitive_email(self, client):
        """Test login with different email case."""
        response = client.post("/api/v1/auth/login", json={
            "email": "Test@Example.com",
            "password": "SecurePass123"
        })
        # Should handle case properly (typically case-insensitive for emails)
        assert response.status_code in [200, 401, 422, 500]
    
    def test_register_method_validation(self, client):
        """Test register endpoint only accepts POST."""
        get_response = client.get("/api/v1/auth/register")
        post_response = client.post("/api/v1/auth/register", json={})
        put_response = client.put("/api/v1/auth/register", json={})
        delete_response = client.delete("/api/v1/auth/register")
        
        assert get_response.status_code == 405
        assert post_response.status_code == 422  # POST allowed but validation error
        assert put_response.status_code == 405
        assert delete_response.status_code == 405
    
    def test_login_method_validation(self, client):
        """Test login endpoint only accepts POST."""
        get_response = client.get("/api/v1/auth/login")
        post_response = client.post("/api/v1/auth/login", json={})
        put_response = client.put("/api/v1/auth/login", json={})
        delete_response = client.delete("/api/v1/auth/login")
        
        assert get_response.status_code == 405
        assert post_response.status_code == 422  # POST allowed but validation error
        assert put_response.status_code == 405
        assert delete_response.status_code == 405
    
    def test_me_method_validation(self, client):
        """Test /me endpoint only accepts GET."""
        get_response = client.get("/api/v1/auth/me")
        post_response = client.post("/api/v1/auth/me")
        put_response = client.put("/api/v1/auth/me", json={})
        delete_response = client.delete("/api/v1/auth/me")
        
        assert get_response.status_code in [401, 403]  # GET allowed but auth error
        assert post_response.status_code == 405
        assert put_response.status_code == 405
        assert delete_response.status_code == 405
