"""Comprehensive tests for RefreshTokenRepository."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

from app.repositories.refresh_token_repository import RefreshTokenRepository


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def repo(mock_db):
    return RefreshTokenRepository(mock_db)


class TestCreate:
    """Test create() method."""

    @pytest.mark.asyncio
    async def test_create_auto_commit(self, repo, mock_db):
        """create() commits and refreshes when auto_commit=True."""
        user_id = uuid4()
        expires_at = datetime.now() + timedelta(days=7)

        result = await repo.create(user_id, "hash123", expires_at, "Chrome")

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_no_auto_commit(self, repo, mock_db):
        """create() flushes without committing when auto_commit=False."""
        user_id = uuid4()
        expires_at = datetime.now() + timedelta(days=7)

        result = await repo.create(user_id, "hash123", expires_at, auto_commit=False)

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_without_device_info(self, repo, mock_db):
        """create() works without device_info."""
        result = await repo.create(uuid4(), "hash123", datetime.now() + timedelta(days=7))
        mock_db.add.assert_called_once()


class TestRevoke:
    """Test revoke() method."""

    @pytest.mark.asyncio
    async def test_revoke_success(self, repo, mock_db):
        """revoke() returns True when token is found and revoked."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock()  # found
        mock_db.execute.return_value = mock_result

        result = await repo.revoke("hash123")

        assert result is True
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_not_found(self, repo, mock_db):
        """revoke() returns False when token is not found."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.revoke("nonexistent_hash")

        assert result is False

    @pytest.mark.asyncio
    async def test_revoke_with_replaced_by(self, repo, mock_db):
        """revoke() accepts replaced_by parameter."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock()
        mock_db.execute.return_value = mock_result

        replacement_id = uuid4()
        result = await repo.revoke("hash123", replaced_by=replacement_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_no_auto_commit(self, repo, mock_db):
        """revoke() doesn't commit when auto_commit=False."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock()
        mock_db.execute.return_value = mock_result

        await repo.revoke("hash123", auto_commit=False)

        mock_db.commit.assert_not_called()


class TestRotate:
    """Test rotate() method."""

    @pytest.mark.asyncio
    async def test_rotate_success(self, repo, mock_db):
        """rotate() creates new token, revokes old, and commits atomically."""
        # Mock the revoke execute result
        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock()
        mock_db.execute.return_value = mock_result

        new_record = await repo.rotate(
            old_token_hash="old_hash",
            new_user_id=uuid4(),
            new_token_hash="new_hash",
            new_expires_at=datetime.now() + timedelta(days=7),
            device_info="Firefox",
        )

        # add (create), flush (create no-commit), execute (revoke), commit, refresh
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        assert mock_db.commit.call_count >= 1
        assert mock_db.refresh.call_count >= 1


class TestGetValid:
    """Test get_valid() method."""

    @pytest.mark.asyncio
    async def test_get_valid_found(self, repo, mock_db):
        """get_valid() returns token when found and valid."""
        mock_token = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_token
        mock_db.execute.return_value = mock_result

        result = await repo.get_valid("hash123")

        assert result == mock_token

    @pytest.mark.asyncio
    async def test_get_valid_not_found(self, repo, mock_db):
        """get_valid() returns None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.get_valid("missing_hash")

        assert result is None


class TestGetByUser:
    """Test get_by_user() method."""

    @pytest.mark.asyncio
    async def test_get_by_user_returns_list(self, repo, mock_db):
        """get_by_user() returns a list of tokens."""
        tokens = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = tokens
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_user(uuid4())

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_by_user_empty(self, repo, mock_db):
        """get_by_user() returns empty list when no tokens."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_user(uuid4())

        assert result == []


class TestPurgeExpired:
    """Test purge_expired() method."""

    @pytest.mark.asyncio
    async def test_purge_expired(self, repo, mock_db):
        """purge_expired() deletes expired tokens and returns count."""
        mock_result = MagicMock()
        mock_result.rowcount = 10
        mock_db.execute.return_value = mock_result

        count = await repo.purge_expired()

        assert count == 10
        mock_db.commit.assert_called_once()
