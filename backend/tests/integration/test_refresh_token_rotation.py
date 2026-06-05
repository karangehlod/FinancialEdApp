import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4
from datetime import datetime, timedelta, timezone

from app.services.auth_service import AuthService, _sha256
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.db.models.auth import RefreshToken


@pytest.mark.asyncio
async def test_refresh_token_rotation_and_reuse_detection(monkeypatch):
    """Simulate using the same refresh token twice: first valid, second should trigger revoke_all_for_user."""

    # Create mocks for dependencies
    mock_user_repo = AsyncMock()
    user_id = uuid4()
    mock_user = AsyncMock()
    mock_user.id = user_id
    mock_user.email = 'test@example.com'
    mock_user.is_active = True
    mock_user_repo.get_user_by_id.return_value = mock_user

    mock_password_hasher = MagicMock()
    mock_token_provider = MagicMock()

    # token provider returns the same refresh token string
    initial_refresh = 'initial_refresh_token'
    rotated_refresh = 'rotated_refresh_token'
    mock_token_provider.create_access_token.return_value = 'access'
    # First call to create_refresh_token (during rotation) returns rotated_refresh
    mock_token_provider.create_refresh_token.return_value = rotated_refresh
    # decode_token must return a payload with type=refresh and a valid sub
    mock_token_provider.decode_token.return_value = {
        "sub": str(user_id),
        "type": "refresh",
    }

    # Mock refresh token repo methods
    class DummyDB:
        pass

    # First call: get_valid returns a record
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    valid_record = RefreshToken(id=uuid4(), user_id=user_id, token_hash=_sha256(initial_refresh), expires_at=now + timedelta(days=7), is_revoked=False)

    async def fake_get_valid(token_hash):
        # On first call return valid_record, on second call return None (simulating reuse detection)
        if fake_get_valid.called:
            return None
        fake_get_valid.called = True
        return valid_record
    fake_get_valid.called = False

    revoke_all_called = False

    async def fake_revoke_all(user_id_arg):
        nonlocal revoke_all_called
        revoke_all_called = True
        return 3

    class MockRefreshRepo:
        async def get_valid(self, token_hash):
            return await fake_get_valid(token_hash)
        async def rotate(self, old_token_hash, new_user_id, new_token_hash, new_expires_at, device_info=None):
            return RefreshToken(id=uuid4(), user_id=new_user_id, token_hash=new_token_hash, expires_at=new_expires_at)
        async def revoke_all_for_user(self, user_id_arg):
            return await fake_revoke_all(user_id_arg)

    mock_refresh_repo = MockRefreshRepo()

    # Create service with mocked dependencies
    svc = AuthService(
        user_repository=mock_user_repo,
        password_hasher=mock_password_hasher,
        token_provider=mock_token_provider,
        refresh_token_repository=mock_refresh_repo,
        cache=None,
    )

    # First refresh should succeed
    tokens = await svc.refresh_user_token(initial_refresh)
    assert tokens["refresh_token"] == rotated_refresh

    # Second refresh with same token should trigger revoke_all_for_user and raise
    with pytest.raises(Exception):
        await svc.refresh_user_token(initial_refresh)

    assert revoke_all_called is True
