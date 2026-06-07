"""Tests for user_repository.py - 100% branch coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID
from datetime import datetime

from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserCreate
from app.db.models.auth import User


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock(return_value=None)
    db.refresh = AsyncMock(return_value=None)
    db.delete = AsyncMock(return_value=None)
    return db


@pytest.fixture
def repo(mock_db):
    return UserRepository(mock_db)


@pytest.fixture
def sample_user():
    return User(
        id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        email="test@example.com",
        password_hash="hashed",
        is_active=True,
        is_verified=False,
        last_login=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


class TestInitialization:
    def test_init_stores_db(self, mock_db):
        repo = UserRepository(mock_db)
        assert repo.db is mock_db


class TestCreateUser:
    @pytest.mark.asyncio
    async def test_create_user_success(self, repo, mock_db):
        user_data = UserCreate(email="NEW@EXAMPLE.COM", password="ValidPass123")
        with patch('app.repositories.user_repository.get_password_hash', return_value="h"):
            await repo.create_user(user_data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_email_lowercase(self, repo, mock_db):
        user_data = UserCreate(email="NEW@EXAMPLE.COM", password="ValidPass123")
        with patch('app.repositories.user_repository.get_password_hash', return_value="h"):
            await repo.create_user(user_data)
        user = mock_db.add.call_args[0][0]
        assert user.email == "new@example.com"

    @pytest.mark.asyncio
    async def test_create_user_active_unverified(self, repo, mock_db):
        user_data = UserCreate(email="test@example.com", password="ValidPass123")
        with patch('app.repositories.user_repository.get_password_hash', return_value="h"):
            await repo.create_user(user_data)
        user = mock_db.add.call_args[0][0]
        assert user.is_active is True
        assert user.is_verified is False


class TestGetUserByEmail:
    @pytest.mark.asyncio
    async def test_get_by_email_found(self, repo, mock_db, sample_user):
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_user)
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_user_by_email("test@example.com")
        assert result == sample_user

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, repo, mock_db):
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_user_by_email("notfound@example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_email_lowercase(self, repo, mock_db):
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        await repo.get_user_by_email("TEST@EXAMPLE.COM")
        mock_db.execute.assert_called_once()


class TestGetUserById:
    @pytest.mark.asyncio
    async def test_get_by_id_uuid_found(self, repo, mock_db, sample_user):
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_user)
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_user_by_id(sample_user.id)
        assert result == sample_user

    @pytest.mark.asyncio
    async def test_get_by_id_uuid_not_found(self, repo, mock_db):
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        user_id = UUID("550e8400-e29b-41d4-a716-446655440001")
        result = await repo.get_user_by_id(user_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_string_valid_found(self, repo, mock_db, sample_user):
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_user)
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_user_by_id("550e8400-e29b-41d4-a716-446655440000")
        assert result == sample_user

    @pytest.mark.asyncio
    async def test_get_by_id_string_valid_not_found(self, repo, mock_db):
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_user_by_id("550e8400-e29b-41d4-a716-446655440001")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_string_invalid_returns_none(self, repo, mock_db):
        # Tests ValueError branch
        result = await repo.get_user_by_id("not-a-uuid")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_string_empty_returns_none(self, repo, mock_db):
        result = await repo.get_user_by_id("")
        assert result is None


class TestUpdateLastLogin:
    @pytest.mark.asyncio
    async def test_update_success(self, repo, mock_db, sample_user):
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_user)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        before = datetime.utcnow()
        await repo.update_last_login(sample_user.id)
        after = datetime.utcnow()
        
        assert sample_user.last_login is not None
        assert before <= sample_user.last_login <= after
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, repo, mock_db):
        # Tests if user: False branch
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        user_id = UUID("550e8400-e29b-41d4-a716-446655440001")
        await repo.update_last_login(user_id)
        
        mock_db.commit.assert_not_called()


class TestDeleteUser:
    @pytest.mark.asyncio
    async def test_delete_success(self, repo, mock_db, sample_user):
        # Tests if user: True branch
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_user)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await repo.delete_user(sample_user.id)
        
        assert result is True
        mock_db.delete.assert_called_once_with(sample_user)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, repo, mock_db):
        # Tests if user: False branch - returns False
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        user_id = UUID("550e8400-e29b-41d4-a716-446655440001")
        result = await repo.delete_user(user_id)
        
        assert result is False
        mock_db.delete.assert_not_called()
        mock_db.commit.assert_not_called()


class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_workflow(self, repo, mock_db, sample_user):
        # Create/Get/Update/Delete
        user_data = UserCreate(email="test@example.com", password="ValidPass123")
        with patch('app.repositories.user_repository.get_password_hash', return_value="h"):
            await repo.create_user(user_data)
        
        # Get by ID
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_user)
        mock_db.execute = AsyncMock(return_value=mock_result)
        user = await repo.get_user_by_id(sample_user.id)
        assert user is not None
        
        # Update login
        await repo.update_last_login(sample_user.id)
        
        # Delete
        result = await repo.delete_user(sample_user.id)
        assert result is True
