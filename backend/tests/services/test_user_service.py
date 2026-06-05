"""Unit tests for app.services.user_service module."""

import pytest
from uuid import UUID
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.user_service import UserService
from app.schemas.user_profile import UserProfileCreate, UserProfileUpdate
from app.core.exceptions import UserNotFoundError, DatabaseError
from datetime import datetime


class MockUserProfile:
    """Mock user profile for testing."""
    
    def __init__(self, user_id: UUID, name: str = "Test User"):
        self.user_id = user_id
        self.id = user_id
        self.name = name
        self.country = "US"
        self.currency = "USD"
        self.knowledge_level = "beginner"
        self.risk_tolerance = "medium"
        self.consent_given = True
        self.consent_timestamp = datetime.utcnow()
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


@pytest.fixture
def mock_repository():
    """Create a mock user profile repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def user_service(mock_repository):
    """Create a user service with mock repository."""
    return UserService(mock_repository)


@pytest.fixture
def sample_user_id():
    """Provide a sample user ID."""
    return UUID("550e8400-e29b-41d4-a716-446655440000")


@pytest.fixture
def sample_profile_data():
    """Provide sample profile creation data."""
    user_id = UUID("550e8400-e29b-41d4-a716-446655440001")
    return {
        "user_id": user_id,
        "name": "John Doe",
        "country": "US",
        "currency": "USD",
        "knowledge_level": "intermediate",
        "risk_tolerance": "high"
    }


class TestUserServiceInitialization:
    """Test UserService initialization."""
    
    def test_user_service_init(self, mock_repository):
        service = UserService(mock_repository)
        assert service.user_profile_repository == mock_repository
    
    def test_user_service_has_logger(self, user_service):
        assert user_service.logger is not None
        assert user_service._service_name == "UserService"
    
    def test_user_service_is_crud_service(self, user_service):
        from app.services.base_service import CRUDService
        assert isinstance(user_service, CRUDService)


class TestUserServiceValidateDependencies:
    """Test UserService dependency validation."""
    
    @pytest.mark.asyncio
    async def test_validate_dependencies_with_valid_repository(self, user_service):
        result = await user_service.validate_dependencies()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_dependencies_with_none_repository(self):
        service = UserService(None)
        with pytest.raises(DatabaseError):
            await service.validate_dependencies()
    
    @pytest.mark.asyncio
    async def test_validate_dependencies_raises_database_error(self):
        service = UserService(None)
        try:
            await service.validate_dependencies()
        except DatabaseError as e:
            assert "not available" in str(e)


class TestUserServiceCreate:
    """Test UserService create operation."""
    
    @pytest.mark.asyncio
    async def test_create_user_profile(self, user_service, mock_repository, sample_user_id):
        profile_data = UserProfileCreate(
            user_id=sample_user_id,
            name="John Doe",
            country="US",
            currency="USD"
        )
        mock_profile = MockUserProfile(sample_user_id)
        mock_repository.create_profile.return_value = mock_profile
        
        result = await user_service.create(profile_data)
        
        assert result is not None
        assert result.user_id == sample_user_id
        mock_repository.create_profile.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_user_profile_logs_operation(self, user_service, mock_repository, sample_user_id):
        profile_data = UserProfileCreate(
            user_id=sample_user_id,
            name="Jane Doe"
        )
        mock_profile = MockUserProfile(sample_user_id)
        mock_repository.create_profile.return_value = mock_profile
        
        with patch.object(user_service, 'log_operation') as mock_log:
            await user_service.create(profile_data)
            # Should log operation start and success
            assert mock_log.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_create_handles_repository_error(self, user_service, mock_repository, sample_user_id):
        profile_data = UserProfileCreate(
            user_id=sample_user_id,
            name="Test User"
        )
        mock_repository.create_profile.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseError):
            await user_service.create(profile_data)


class TestUserServiceRead:
    """Test UserService read operation."""
    
    @pytest.mark.asyncio
    async def test_read_user_profile(self, user_service, mock_repository, sample_user_id):
        mock_profile = MockUserProfile(sample_user_id)
        mock_repository.get_profile_by_user_id.return_value = mock_profile
        
        result = await user_service.read(sample_user_id)
        
        assert result is not None
        assert result.user_id == sample_user_id
        mock_repository.get_profile_by_user_id.assert_called_once_with(sample_user_id)
    
    @pytest.mark.asyncio
    async def test_read_user_profile_not_found(self, user_service, mock_repository, sample_user_id):
        mock_repository.get_profile_by_user_id.return_value = None
        
        result = await user_service.read(sample_user_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_read_logs_operation(self, user_service, mock_repository, sample_user_id):
        mock_profile = MockUserProfile(sample_user_id)
        mock_repository.get_profile_by_user_id.return_value = mock_profile
        
        with patch.object(user_service, 'log_operation') as mock_log:
            await user_service.read(sample_user_id)
            mock_log.assert_called()
    
    @pytest.mark.asyncio
    async def test_read_handles_error(self, user_service, mock_repository, sample_user_id):
        mock_repository.get_profile_by_user_id.side_effect = Exception("Read error")
        
        with pytest.raises(DatabaseError):
            await user_service.read(sample_user_id)


class TestUserServiceUpdate:
    """Test UserService update operation."""
    
    @pytest.mark.asyncio
    async def test_update_user_profile(self, user_service, mock_repository, sample_user_id):
        update_data = UserProfileUpdate(
            name="Updated Name",
            country="UK"
        )
        mock_profile = MockUserProfile(sample_user_id, "Updated Name")
        mock_repository.update_profile.return_value = mock_profile
        
        result = await user_service.update(sample_user_id, update_data)
        
        assert result is not None
        assert result.name == "Updated Name"
        mock_repository.update_profile.assert_called_once_with(sample_user_id, update_data)
    
    @pytest.mark.asyncio
    async def test_update_user_profile_not_found(self, user_service, mock_repository, sample_user_id):
        update_data = UserProfileUpdate(name="Updated Name")
        mock_repository.update_profile.return_value = None
        
        with pytest.raises(UserNotFoundError):
            await user_service.update(sample_user_id, update_data)
    
    @pytest.mark.asyncio
    async def test_update_logs_operation(self, user_service, mock_repository, sample_user_id):
        update_data = UserProfileUpdate(name="New Name")
        mock_profile = MockUserProfile(sample_user_id)
        mock_repository.update_profile.return_value = mock_profile
        
        with patch.object(user_service, 'log_operation') as mock_log:
            await user_service.update(sample_user_id, update_data)
            assert mock_log.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_update_reraises_user_not_found_error(self, user_service, mock_repository, sample_user_id):
        update_data = UserProfileUpdate(name="Test")
        mock_repository.update_profile.return_value = None
        
        with pytest.raises(UserNotFoundError):
            await user_service.update(sample_user_id, update_data)
    
    @pytest.mark.asyncio
    async def test_update_handles_non_user_not_found_error(self, user_service, mock_repository, sample_user_id):
        update_data = UserProfileUpdate(name="Test")
        mock_repository.update_profile.side_effect = Exception("Update error")
        
        with pytest.raises(DatabaseError):
            await user_service.update(sample_user_id, update_data)


class TestUserServiceDelete:
    """Test UserService delete operation."""
    
    @pytest.mark.asyncio
    async def test_delete_user_profile_success(self, user_service, mock_repository, sample_user_id):
        mock_repository.delete_profile.return_value = True
        
        result = await user_service.delete(sample_user_id)
        
        assert result is True
        mock_repository.delete_profile.assert_called_once_with(sample_user_id)
    
    @pytest.mark.asyncio
    async def test_delete_user_profile_not_found(self, user_service, mock_repository, sample_user_id):
        mock_repository.delete_profile.return_value = False
        
        result = await user_service.delete(sample_user_id)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_logs_operation_on_success(self, user_service, mock_repository, sample_user_id):
        mock_repository.delete_profile.return_value = True
        
        with patch.object(user_service, 'log_operation') as mock_log:
            await user_service.delete(sample_user_id)
            assert mock_log.call_count >= 2  # Log start and success
    
    @pytest.mark.asyncio
    async def test_delete_logs_operation_without_success_message(self, user_service, mock_repository, sample_user_id):
        mock_repository.delete_profile.return_value = False
        
        with patch.object(user_service, 'log_operation') as mock_log:
            await user_service.delete(sample_user_id)
            # Only logs the start operation, not the success
            assert mock_log.call_count == 1
    
    @pytest.mark.asyncio
    async def test_delete_handles_error(self, user_service, mock_repository, sample_user_id):
        mock_repository.delete_profile.side_effect = Exception("Delete error")
        
        with pytest.raises(DatabaseError):
            await user_service.delete(sample_user_id)


class TestUserServiceList:
    """Test UserService list operation."""
    
    @pytest.mark.asyncio
    async def test_list_user_profiles_default(self, user_service):
        result = await user_service.list()
        
        assert isinstance(result, list)
        assert len(result) == 0  # Default implementation returns empty list
    
    @pytest.mark.asyncio
    async def test_list_user_profiles_with_skip_limit(self, user_service):
        result = await user_service.list(skip=10, limit=20)
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_list_user_profiles_with_filters(self, user_service):
        filters = {"country": "US"}
        result = await user_service.list(filters=filters)
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_list_logs_operation(self, user_service):
        with patch.object(user_service, 'log_operation') as mock_log:
            await user_service.list(skip=5, limit=15)
            mock_log.assert_called()
    
    @pytest.mark.asyncio
    async def test_list_handles_error(self, user_service):
        with patch.object(user_service, 'log_operation') as mock_log:
            mock_log.side_effect = Exception("List error")
            
            with pytest.raises(DatabaseError):
                await user_service.list()


class TestUserServiceErrorHandling:
    """Test error handling across all operations."""
    
    @pytest.mark.asyncio
    async def test_create_generic_exception_becomes_database_error(self, user_service, mock_repository, sample_user_id):
        profile_data = UserProfileCreate(user_id=sample_user_id)
        mock_repository.create_profile.side_effect = RuntimeError("Unexpected error")
        
        with pytest.raises(DatabaseError):
            await user_service.create(profile_data)
    
    @pytest.mark.asyncio
    async def test_read_generic_exception_becomes_database_error(self, user_service, mock_repository, sample_user_id):
        mock_repository.get_profile_by_user_id.side_effect = RuntimeError("Unexpected error")
        
        with pytest.raises(DatabaseError):
            await user_service.read(sample_user_id)
    
    @pytest.mark.asyncio
    async def test_delete_generic_exception_becomes_database_error(self, user_service, mock_repository, sample_user_id):
        mock_repository.delete_profile.side_effect = RuntimeError("Unexpected error")
        
        with pytest.raises(DatabaseError):
            await user_service.delete(sample_user_id)


class TestUserServiceIntegration:
    """Test UserService integration behaviors."""
    
    @pytest.mark.asyncio
    async def test_create_and_read_workflow(self, user_service, mock_repository, sample_user_id):
        # Setup mock for create
        profile_data = UserProfileCreate(user_id=sample_user_id)
        mock_profile = MockUserProfile(sample_user_id)
        mock_repository.create_profile.return_value = mock_profile
        
        # Create
        created = await user_service.create(profile_data)
        assert created is not None
        
        # Setup mock for read
        mock_repository.get_profile_by_user_id.return_value = created
        
        # Read
        retrieved = await user_service.read(sample_user_id)
        assert retrieved.user_id == created.user_id
    
    @pytest.mark.asyncio
    async def test_create_update_read_workflow(self, user_service, mock_repository, sample_user_id):
        # Create
        profile_data = UserProfileCreate(user_id=sample_user_id)
        mock_profile = MockUserProfile(sample_user_id)
        mock_repository.create_profile.return_value = mock_profile
        await user_service.create(profile_data)
        
        # Update
        update_data = UserProfileUpdate(name="Updated")
        updated_profile = MockUserProfile(sample_user_id, "Updated")
        mock_repository.update_profile.return_value = updated_profile
        updated = await user_service.update(sample_user_id, update_data)
        assert updated.name == "Updated"
        
        # Read
        mock_repository.get_profile_by_user_id.return_value = updated
        retrieved = await user_service.read(sample_user_id)
        assert retrieved.name == "Updated"
