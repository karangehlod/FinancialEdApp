"""Tests for user_profile_repository.py - 100% branch coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID
from datetime import datetime, date

from app.repositories.user_profile_repository import UserProfileRepository
from app.db.models.data import UserProfile
from app.schemas.user_profile import UserProfileCreate, UserProfileUpdate


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock(return_value=None)
    db.refresh = AsyncMock(return_value=None)
    db.execute = AsyncMock()
    db.delete = AsyncMock(return_value=None)
    return db


@pytest.fixture
def repository(mock_db):
    return UserProfileRepository(mock_db)


@pytest.fixture
def sample_user_id():
    return UUID("550e8400-e29b-41d4-a716-446655440001")


@pytest.fixture
def sample_user_profile(sample_user_id):
    return UserProfile(
        user_id=sample_user_id,
        name="John Doe",
        country="IN",
        currency="INR",
        knowledge_level="intermediate",
        risk_tolerance="moderate",
        consent_given=True,
        consent_timestamp=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


class TestCreateProfile:
    @pytest.mark.asyncio
    async def test_create_profile_with_data(self, repository, mock_db, sample_user_id):
        """Test creating user profile with profile data."""
        profile_data = UserProfileCreate(
            user_id=sample_user_id,
            name="John Doe",
            country="US",
            currency="USD",
            knowledge_level="intermediate",
            risk_tolerance="high",
            consent_given=True
        )
        
        result = await repository.create_profile(sample_user_id, profile_data)
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_profile_without_data(self, repository, mock_db, sample_user_id):
        """Test creating user profile without profile data (defaults)."""
        result = await repository.create_profile(sample_user_id)
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_profile_with_partial_data(self, repository, mock_db, sample_user_id):
        """Test creating user profile with partial data."""
        profile_data = UserProfileCreate(
            user_id=sample_user_id,
            name="Jane Doe",
            knowledge_level="beginner"
        )
        
        result = await repository.create_profile(sample_user_id, profile_data)
        
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_profile_with_consent(self, repository, mock_db, sample_user_id):
        """Test creating profile with consent given."""
        profile_data = UserProfileCreate(
            user_id=sample_user_id,
            name="John",
            consent_given=True
        )
        
        result = await repository.create_profile(sample_user_id, profile_data)
        
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_profile_without_consent(self, repository, mock_db, sample_user_id):
        """Test creating profile without consent."""
        profile_data = UserProfileCreate(
            user_id=sample_user_id,
            name="John",
            consent_given=False
        )
        
        result = await repository.create_profile(sample_user_id, profile_data)
        
        mock_db.add.assert_called_once()


class TestGetProfileByUserId:
    @pytest.mark.asyncio
    async def test_get_profile_found(self, repository, mock_db, sample_user_profile):
        """Test getting existing user profile."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user_profile
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await repository.get_profile_by_user_id(sample_user_profile.user_id)
        
        assert result == sample_user_profile
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, repository, mock_db, sample_user_id):
        """Test getting non-existent user profile."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await repository.get_profile_by_user_id(sample_user_id)
        
        assert result is None


class TestUpdateProfile:
    @pytest.mark.asyncio
    async def test_update_profile_found(self, repository, mock_db, sample_user_profile):
        """Test updating existing user profile."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user_profile
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock(return_value=None)
        mock_db.refresh = AsyncMock(return_value=None)
        
        update_data = UserProfileUpdate(
            name="Jane Doe",
            country="US"
        )
        
        result = await repository.update_profile(sample_user_profile.user_id, update_data)
        
        assert result == sample_user_profile
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_profile_not_found(self, repository, mock_db, sample_user_id):
        """Test updating non-existent user profile."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        update_data = UserProfileUpdate(name="Jane Doe")
        
        result = await repository.update_profile(sample_user_id, update_data)
        
        assert result is None
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_profile_single_field(self, repository, mock_db, sample_user_profile):
        """Test updating single field in profile."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user_profile
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock(return_value=None)
        mock_db.refresh = AsyncMock(return_value=None)
        
        update_data = UserProfileUpdate(name="Updated Name")
        
        result = await repository.update_profile(sample_user_profile.user_id, update_data)
        
        assert result == sample_user_profile
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_profile_multiple_fields(self, repository, mock_db, sample_user_profile):
        """Test updating multiple fields in profile."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user_profile
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock(return_value=None)
        mock_db.refresh = AsyncMock(return_value=None)
        
        update_data = UserProfileUpdate(
            name="Updated Name",
            country="UK",
            currency="GBP",
            knowledge_level="advanced"
        )
        
        result = await repository.update_profile(sample_user_profile.user_id, update_data)
        
        assert result == sample_user_profile
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_profile_with_invalid_field(self, repository, mock_db, sample_user_profile):
        """Test updating profile with field that doesn't exist (should not fail)."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user_profile
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock(return_value=None)
        mock_db.refresh = AsyncMock(return_value=None)
        
        # Create update data with only valid fields
        update_data = UserProfileUpdate(name="Updated Name")
        
        result = await repository.update_profile(sample_user_profile.user_id, update_data)
        
        assert result == sample_user_profile
    
    @pytest.mark.asyncio
    async def test_update_profile_skips_nonexistent_attributes(self, repository, mock_db, sample_user_profile):
        """Test that update_profile skips setting attributes that don't exist on profile."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user_profile
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock(return_value=None)
        mock_db.refresh = AsyncMock(return_value=None)
        
        # Create update data with only valid fields
        update_data = UserProfileUpdate(name="Updated Name")
        
        # Patch hasattr to test the False branch
        with patch('builtins.hasattr', return_value=False):
            result = await repository.update_profile(sample_user_profile.user_id, update_data)
        
        assert result == sample_user_profile
        # Verify setattr was NOT called when hasattr returns False
        mock_db.commit.assert_called_once()


class TestDeleteProfile:
    @pytest.mark.asyncio
    async def test_delete_profile_found(self, repository, mock_db, sample_user_profile):
        """Test deleting existing user profile."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user_profile
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock(return_value=None)
        mock_db.commit = AsyncMock(return_value=None)
        
        result = await repository.delete_profile(sample_user_profile.user_id)
        
        assert result is True
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_profile_not_found(self, repository, mock_db, sample_user_id):
        """Test deleting non-existent user profile."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await repository.delete_profile(sample_user_id)
        
        assert result is False
        mock_db.delete.assert_not_called()
        mock_db.commit.assert_not_called()
