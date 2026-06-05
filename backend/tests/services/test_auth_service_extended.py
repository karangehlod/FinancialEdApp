"""Additional tests for auth_service.py — covering lockout, change_password, revoke_all, and blacklist paths."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4
from datetime import datetime

from app.services.auth_service import AuthService, _sha256, _build_token_response
from app.core.exceptions import AuthenticationError
from app.db.models.auth import User


@pytest.fixture
def mock_user_repository():
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_password_hasher():
    hasher = MagicMock()
    hasher.hash_password = MagicMock(return_value="new_hashed_pass")
    hasher.verify_password = MagicMock(return_value=True)
    return hasher


@pytest.fixture
def mock_token_provider():
    provider = MagicMock()
    provider.create_access_token = MagicMock(return_value="at")
    provider.create_refresh_token = MagicMock(return_value="rt")
    provider.decode_token = MagicMock(return_value={"sub": "uid", "type": "refresh"})
    return provider


@pytest.fixture
def mock_refresh_token_repository():
    repo = AsyncMock()
    repo.create = AsyncMock()
    repo.revoke = AsyncMock()
    repo.revoke_all_for_user = AsyncMock(return_value=3)
    repo.rotate = AsyncMock()
    repo.get_valid = AsyncMock()
    return repo


@pytest.fixture
def mock_cache():
    c = AsyncMock()
    c.get = AsyncMock(return_value=None)
    c.set = AsyncMock()
    c.delete = AsyncMock()
    c.exists = AsyncMock(return_value=False)
    c.increment = AsyncMock()
    return c


@pytest.fixture
def sample_user():
    return User(
        id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        email="test@example.com",
        password_hash="hashed",
        is_active=True,
        is_verified=True,
        last_login=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def auth_service_with_cache(mock_user_repository, mock_password_hasher, mock_token_provider, mock_refresh_token_repository, mock_cache):
    return AuthService(
        user_repository=mock_user_repository,
        password_hasher=mock_password_hasher,
        token_provider=mock_token_provider,
        refresh_token_repository=mock_refresh_token_repository,
        cache=mock_cache,
    )


# ============================================================================
# Account lockout
# ============================================================================

class TestAccountLockout:

    @pytest.mark.asyncio
    async def test_locked_out_user_cannot_authenticate(self, auth_service_with_cache, mock_cache):
        """User that exceeds failed login threshold is locked out."""
        mock_cache.get.return_value = "6"  # above _FAILED_LOGIN_MAX (5)

        with pytest.raises(AuthenticationError, match="Account temporarily locked"):
            await auth_service_with_cache.authenticate_user("test@example.com", "pw")

    @pytest.mark.asyncio
    async def test_not_locked_out_when_under_threshold(self, auth_service_with_cache, mock_cache, mock_user_repository):
        """User not locked when count is below threshold."""
        mock_cache.get.return_value = "2"
        mock_user_repository.get_user_by_email.return_value = None

        result = await auth_service_with_cache.authenticate_user("test@example.com", "pw")
        assert result is None  # user not found, but not locked

    @pytest.mark.asyncio
    async def test_lockout_check_error_returns_false(self, auth_service_with_cache, mock_cache, mock_user_repository):
        """If Redis error during lockout check, default to not locked."""
        mock_cache.get.side_effect = Exception("redis error")
        mock_user_repository.get_user_by_email.return_value = None

        # Should not raise — proceeds as if not locked
        result = await auth_service_with_cache.authenticate_user("test@example.com", "pw")
        assert result is None

    @pytest.mark.asyncio
    async def test_record_failed_login_without_cache(self, mock_user_repository, mock_password_hasher, mock_token_provider, mock_refresh_token_repository):
        """Record failed login is a no-op when cache is None."""
        svc = AuthService(mock_user_repository, mock_password_hasher, mock_token_provider, mock_refresh_token_repository)
        mock_user_repository.get_user_by_email.return_value = None
        # Should not raise even without cache
        result = await svc.authenticate_user("test@example.com", "pw")
        assert result is None

    @pytest.mark.asyncio
    async def test_clear_failed_logins_on_success(self, auth_service_with_cache, mock_cache, mock_user_repository, mock_password_hasher, sample_user):
        """Successful login clears the lockout counter."""
        mock_cache.get.return_value = None  # not locked
        mock_user_repository.get_user_by_email.return_value = sample_user
        mock_password_hasher.verify_password.return_value = True

        result = await auth_service_with_cache.authenticate_user("test@example.com", "pw")
        assert result == sample_user
        mock_cache.delete.assert_called_once()


# ============================================================================
# Change password
# ============================================================================

class TestChangePassword:

    @pytest.mark.asyncio
    async def test_change_password_success(self, auth_service_with_cache, mock_user_repository, mock_password_hasher, sample_user):
        mock_user_repository.get_user_by_id.return_value = sample_user
        mock_password_hasher.verify_password.return_value = True

        result = await auth_service_with_cache.change_password(sample_user.id, "old", "new")
        assert result is True
        mock_password_hasher.hash_password.assert_called_once_with("new")
        mock_user_repository.update_password.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_user_not_found(self, auth_service_with_cache, mock_user_repository):
        mock_user_repository.get_user_by_id.return_value = None

        with pytest.raises(AuthenticationError, match="User not found"):
            await auth_service_with_cache.change_password(uuid4(), "old", "new")

    @pytest.mark.asyncio
    async def test_change_password_wrong_old_password(self, auth_service_with_cache, mock_user_repository, mock_password_hasher, sample_user):
        mock_user_repository.get_user_by_id.return_value = sample_user
        mock_password_hasher.verify_password.return_value = False

        with pytest.raises(AuthenticationError, match="Current password is incorrect"):
            await auth_service_with_cache.change_password(sample_user.id, "wrong", "new")


# ============================================================================
# Revoke all sessions
# ============================================================================

class TestRevokeAllSessions:

    @pytest.mark.asyncio
    async def test_revoke_all_sessions_returns_count(self, auth_service_with_cache, mock_refresh_token_repository, mock_cache):
        mock_refresh_token_repository.revoke_all_for_user.return_value = 3

        count = await auth_service_with_cache.revoke_all_sessions(uuid4())
        assert count == 3
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_all_sessions_without_cache(self, mock_user_repository, mock_password_hasher, mock_token_provider, mock_refresh_token_repository):
        svc = AuthService(mock_user_repository, mock_password_hasher, mock_token_provider, mock_refresh_token_repository)
        mock_refresh_token_repository.revoke_all_for_user.return_value = 2

        count = await svc.revoke_all_sessions(uuid4())
        assert count == 2


# ============================================================================
# User blacklist
# ============================================================================

class TestUserBlacklist:

    @pytest.mark.asyncio
    async def test_is_blacklisted_false(self, auth_service_with_cache, mock_cache):
        mock_cache.exists.return_value = False
        result = await auth_service_with_cache.is_user_blacklisted(uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_is_blacklisted_true(self, auth_service_with_cache, mock_cache):
        mock_cache.exists.return_value = True
        result = await auth_service_with_cache.is_user_blacklisted(uuid4())
        assert result is True

    @pytest.mark.asyncio
    async def test_is_blacklisted_no_cache(self, mock_user_repository, mock_password_hasher, mock_token_provider, mock_refresh_token_repository):
        svc = AuthService(mock_user_repository, mock_password_hasher, mock_token_provider, mock_refresh_token_repository)
        result = await svc.is_user_blacklisted(uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_is_blacklisted_error_returns_false(self, auth_service_with_cache, mock_cache):
        mock_cache.exists.side_effect = Exception("redis error")
        result = await auth_service_with_cache.is_user_blacklisted(uuid4())
        assert result is False


# ============================================================================
# Update user profile
# ============================================================================

class TestUpdateUserProfile:

    @pytest.mark.asyncio
    async def test_update_user_profile_returns_data(self, auth_service_with_cache):
        result = await auth_service_with_cache.update_user_profile(uuid4(), {"name": "John"})
        assert result == {"name": "John"}


# ============================================================================
# Module-level helpers
# ============================================================================

class TestModuleHelpers:

    def test_sha256(self):
        h = _sha256("test")
        assert isinstance(h, str) and len(h) == 64

    def test_build_token_response(self, sample_user):
        resp = _build_token_response("at", "rt", sample_user)
        assert resp["access_token"] == "at"
        assert resp["refresh_token"] == "rt"
        assert resp["token_type"] == "bearer"
        assert resp["user"]["email"] == "test@example.com"

    # Logout with refresh_token
    @pytest.mark.asyncio
    async def test_logout_with_refresh_token(self, auth_service_with_cache, mock_refresh_token_repository, mock_cache, sample_user):
        result = await auth_service_with_cache.logout_user(sample_user.id, refresh_token="my_rt")
        assert result is True
        mock_refresh_token_repository.revoke.assert_called_once()
        mock_cache.set.assert_called_once()
