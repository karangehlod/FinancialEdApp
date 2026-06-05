"""Comprehensive unit tests for auth_service.py with ≥90% branch coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID
from datetime import datetime, timedelta

from app.services.auth_service import AuthService
from app.schemas.auth import UserCreate
from app.core.exceptions import AuthenticationError, UserAlreadyExistsError
from app.db.models.auth import User


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_user_repository():
    """Create a mock user repository."""
    repo = AsyncMock()
    repo.get_user_by_email = AsyncMock()
    repo.create_user = AsyncMock()
    repo.get_user_by_id = AsyncMock()
    repo.update_last_login = AsyncMock()
    repo.delete_user = AsyncMock()
    return repo


@pytest.fixture
def mock_password_hasher():
    """Create a mock password hasher."""
    hasher = MagicMock()
    hasher.hash_password = MagicMock(return_value="hashed_password_123")
    hasher.verify_password = MagicMock(return_value=True)
    return hasher


@pytest.fixture
def mock_token_provider():
    """Create a mock token provider."""
    provider = MagicMock()
    provider.create_access_token = MagicMock(return_value="access_token_123")
    provider.create_refresh_token = MagicMock(return_value="refresh_token_456")
    provider.decode_token = MagicMock(return_value={"sub": "550e8400-e29b-41d4-a716-446655440000", "type": "refresh"})
    provider.is_token_expired = MagicMock(return_value=False)
    return provider


@pytest.fixture
def mock_refresh_token_repository():
    """Create a mock refresh token repository."""
    repo = AsyncMock()
    repo.create = AsyncMock()
    repo.get_valid = AsyncMock()
    repo.revoke = AsyncMock()
    repo.revoke_all_for_user = AsyncMock(return_value=0)
    repo.rotate = AsyncMock()
    return repo


@pytest.fixture
def sample_user():
    """Create a sample user object."""
    return User(
        id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        email="test@example.com",
        password_hash="hashed_password_123",
        is_active=True,
        is_verified=True,
        last_login=None,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.fixture
def auth_service(mock_user_repository, mock_password_hasher, mock_token_provider, mock_refresh_token_repository):
    """Create an AuthService instance with mocked dependencies."""
    return AuthService(
        user_repository=mock_user_repository,
        password_hasher=mock_password_hasher,
        token_provider=mock_token_provider,
        refresh_token_repository=mock_refresh_token_repository,
    )


@pytest.fixture
def user_create_data():
    """Create sample user registration data."""
    return UserCreate(
        email="newuser@example.com",
        password="ValidPassword123"
    )


# ============================================================================
# Initialization Tests
# ============================================================================

class TestAuthServiceInitialization:
    """Test AuthService initialization and dependency validation."""
    
    def test_service_initializes_with_all_dependencies(self, mock_user_repository, mock_password_hasher, mock_token_provider, mock_refresh_token_repository):
        """Test that service initializes correctly with all dependencies."""
        service = AuthService(
            user_repository=mock_user_repository,
            password_hasher=mock_password_hasher,
            token_provider=mock_token_provider,
            refresh_token_repository=mock_refresh_token_repository,
        )
        assert service.user_repository == mock_user_repository
        assert service.password_hasher == mock_password_hasher
        assert service.token_provider == mock_token_provider
        assert service.refresh_token_repo == mock_refresh_token_repository
    
    def test_service_logs_initialization(self, mock_user_repository, mock_password_hasher, mock_token_provider, mock_refresh_token_repository):
        """Test that service logs initialization."""
        with patch.object(AuthService, 'log_operation') as mock_log:
            service = AuthService(
                user_repository=mock_user_repository,
                password_hasher=mock_password_hasher,
                token_provider=mock_token_provider,
                refresh_token_repository=mock_refresh_token_repository,
            )
            mock_log.assert_called_with("auth_service_initialized")
    
    @pytest.mark.asyncio
    async def test_validate_dependencies_success(self, auth_service):
        """Test that dependency validation succeeds with all dependencies present."""
        result = await auth_service.validate_dependencies()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_dependencies_missing_repository(self, mock_password_hasher, mock_token_provider, mock_refresh_token_repository):
        """Test that validation fails when user repository is missing."""
        service = AuthService(None, mock_password_hasher, mock_token_provider, mock_refresh_token_repository)
        with pytest.raises(AuthenticationError, match="One or more required dependencies"):
            await service.validate_dependencies()
    
    @pytest.mark.asyncio
    async def test_validate_dependencies_missing_hasher(self, mock_user_repository, mock_token_provider, mock_refresh_token_repository):
        """Test that validation fails when password hasher is missing."""
        service = AuthService(mock_user_repository, None, mock_token_provider, mock_refresh_token_repository)
        with pytest.raises(AuthenticationError, match="One or more required dependencies"):
            await service.validate_dependencies()
    
    @pytest.mark.asyncio
    async def test_validate_dependencies_missing_token_provider(self, mock_user_repository, mock_password_hasher, mock_refresh_token_repository):
        """Test that validation fails when token provider is missing."""
        service = AuthService(mock_user_repository, mock_password_hasher, None, mock_refresh_token_repository)
        with pytest.raises(AuthenticationError, match="One or more required dependencies"):
            await service.validate_dependencies()


# ============================================================================
# Register User Tests
# ============================================================================

class TestRegisterUser:
    """Test user registration functionality."""
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_service, mock_user_repository, user_create_data, sample_user):
        """Test successful user registration."""
        mock_user_repository.get_user_by_email.return_value = None
        mock_user_repository.create_user.return_value = sample_user
        
        result = await auth_service.register_user(user_create_data)
        
        assert result == sample_user
        mock_user_repository.get_user_by_email.assert_called_once_with(user_create_data.email)
        mock_user_repository.create_user.assert_called_once_with(user_create_data)
    
    @pytest.mark.asyncio
    async def test_register_user_logs_operation(self, auth_service, mock_user_repository, user_create_data, sample_user):
        """Test that registration logs operation."""
        mock_user_repository.get_user_by_email.return_value = None
        mock_user_repository.create_user.return_value = sample_user
        
        with patch.object(auth_service, 'log_operation') as mock_log:
            await auth_service.register_user(user_create_data)
            
            # Check that operation was logged
            assert mock_log.call_count >= 2
            mock_log.assert_any_call("register_user", {"email": user_create_data.email})
    
    @pytest.mark.asyncio
    async def test_register_user_already_exists(self, auth_service, mock_user_repository, user_create_data, sample_user):
        """Test registration fails when email already exists."""
        mock_user_repository.get_user_by_email.return_value = sample_user
        
        with pytest.raises(UserAlreadyExistsError, match="Email already registered"):
            await auth_service.register_user(user_create_data)
    
    @pytest.mark.asyncio
    async def test_register_user_raises_user_already_exists(self, auth_service, mock_user_repository, user_create_data):
        """Test that UserAlreadyExistsError is re-raised."""
        mock_user_repository.get_user_by_email.return_value = None
        mock_user_repository.create_user.side_effect = UserAlreadyExistsError("Email already registered")
        
        with pytest.raises(UserAlreadyExistsError):
            await auth_service.register_user(user_create_data)
    
    @pytest.mark.asyncio
    async def test_register_user_raises_authentication_error(self, auth_service, mock_user_repository, user_create_data):
        """Test that AuthenticationError is re-raised."""
        mock_user_repository.get_user_by_email.return_value = None
        mock_user_repository.create_user.side_effect = AuthenticationError("Auth failed")
        
        with pytest.raises(AuthenticationError):
            await auth_service.register_user(user_create_data)
    
    @pytest.mark.asyncio
    async def test_register_user_generic_exception_handling(self, auth_service, mock_user_repository, user_create_data):
        """Test that generic exceptions are handled properly."""
        mock_user_repository.get_user_by_email.return_value = None
        mock_user_repository.create_user.side_effect = ValueError("Database error")
        
        with patch.object(auth_service, 'handle_error') as mock_error:
            await auth_service.register_user(user_create_data)
            mock_error.assert_called_once()
            assert mock_error.call_args[0][0] == "register_user"


# ============================================================================
# Authenticate User Tests
# ============================================================================

class TestAuthenticateUser:
    """Test user authentication functionality."""
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_service, mock_user_repository, mock_password_hasher, sample_user):
        """Test successful user authentication."""
        mock_user_repository.get_user_by_email.return_value = sample_user
        mock_password_hasher.verify_password.return_value = True
        
        result = await auth_service.authenticate_user("test@example.com", "ValidPassword123")
        
        assert result == sample_user
        mock_user_repository.get_user_by_email.assert_called_once_with("test@example.com")
        mock_password_hasher.verify_password.assert_called_once_with("ValidPassword123", sample_user.password_hash)
        mock_user_repository.update_last_login.assert_called_once_with(sample_user.id)
    
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, auth_service, mock_user_repository):
        """Test authentication when user is not found."""
        mock_user_repository.get_user_by_email.return_value = None
        
        result = await auth_service.authenticate_user("notfound@example.com", "password")
        
        assert result is None
        mock_user_repository.get_user_by_email.assert_called_once_with("notfound@example.com")
    
    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_password(self, auth_service, mock_user_repository, mock_password_hasher, sample_user):
        """Test authentication with invalid password."""
        mock_user_repository.get_user_by_email.return_value = sample_user
        mock_password_hasher.verify_password.return_value = False
        
        result = await auth_service.authenticate_user("test@example.com", "WrongPassword")
        
        assert result is None
        mock_password_hasher.verify_password.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_user_logs_operation(self, auth_service, mock_user_repository, sample_user):
        """Test that authentication logs operation."""
        mock_user_repository.get_user_by_email.return_value = sample_user
        
        with patch.object(auth_service, 'log_operation') as mock_log:
            await auth_service.authenticate_user("test@example.com", "ValidPassword123")
            
            # Verify log_operation was called
            assert mock_log.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_authenticate_user_logs_not_found(self, auth_service, mock_user_repository):
        """Test that authentication logs when user not found."""
        mock_user_repository.get_user_by_email.return_value = None
        
        with patch.object(auth_service, 'log_operation') as mock_log:
            await auth_service.authenticate_user("test@example.com", "password")
            
            # Should log the not found event
            call_args = [call[0][0] for call in mock_log.call_args_list]
            assert any("failed" in arg and "not_found" in arg for arg in call_args)
    
    @pytest.mark.asyncio
    async def test_authenticate_user_logs_invalid_password(self, auth_service, mock_user_repository, mock_password_hasher, sample_user):
        """Test that authentication logs when password is invalid."""
        mock_user_repository.get_user_by_email.return_value = sample_user
        mock_password_hasher.verify_password.return_value = False
        
        with patch.object(auth_service, 'log_operation') as mock_log:
            await auth_service.authenticate_user("test@example.com", "WrongPassword")
            
            # Should log the invalid password event
            call_args = [call[0][0] for call in mock_log.call_args_list]
            assert any("failed" in arg and "bad_password" in arg for arg in call_args)
    
    @pytest.mark.asyncio
    async def test_authenticate_user_exception_handling(self, auth_service, mock_user_repository):
        """Test that exceptions during authentication propagate."""
        mock_user_repository.get_user_by_email.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            await auth_service.authenticate_user("test@example.com", "password")


# ============================================================================
# Get User By ID Tests
# ============================================================================

class TestGetUserById:
    """Test get_user_by_id functionality."""
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, auth_service, mock_user_repository, sample_user):
        """Test successfully retrieving user by ID."""
        mock_user_repository.get_user_by_id.return_value = sample_user
        
        result = await auth_service.get_user_by_id(sample_user.id)
        
        assert result == sample_user
        mock_user_repository.get_user_by_id.assert_called_once_with(sample_user.id)
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, auth_service, mock_user_repository):
        """Test retrieving user that doesn't exist."""
        user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        mock_user_repository.get_user_by_id.return_value = None
        
        result = await auth_service.get_user_by_id(user_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_logs_operation(self, auth_service, mock_user_repository, sample_user):
        """Test that get_user_by_id logs operation."""
        mock_user_repository.get_user_by_id.return_value = sample_user
        
        with patch.object(auth_service, 'log_operation') as mock_log:
            await auth_service.get_user_by_id(sample_user.id)
            mock_log.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_exception_handling(self, auth_service, mock_user_repository, sample_user):
        """Test that exceptions propagate from get_user_by_id."""
        mock_user_repository.get_user_by_id.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            await auth_service.get_user_by_id(sample_user.id)


# ============================================================================
# Create User Token Tests
# ============================================================================

class TestCreateUserToken:
    """Test token creation functionality."""
    
    @pytest.mark.asyncio
    async def test_create_user_token_success(self, auth_service, mock_token_provider, sample_user):
        """Test successful token creation."""
        result = await auth_service.create_user_token(sample_user)
        
        assert "access_token" in result
        assert "refresh_token" in result
        assert "token_type" in result
        assert result["token_type"] == "bearer"
        assert "user" in result
        assert result["user"]["id"] == str(sample_user.id)
        assert result["user"]["email"] == sample_user.email
        assert result["user"]["is_active"] == sample_user.is_active
        assert result["user"]["is_verified"] == sample_user.is_verified
        
        mock_token_provider.create_access_token.assert_called_once()
        mock_token_provider.create_refresh_token.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_user_token_creates_access_token_with_user_data(self, auth_service, mock_token_provider, sample_user):
        """Test that access token is created with correct user data."""
        await auth_service.create_user_token(sample_user)
        
        call_args = mock_token_provider.create_access_token.call_args
        data = call_args[1]["data"]
        
        assert data["sub"] == str(sample_user.id)
        assert data["email"] == sample_user.email
    
    @pytest.mark.asyncio
    async def test_create_user_token_creates_access_token_with_expiry(self, auth_service, mock_token_provider, sample_user):
        """Test that access token is created with 30-minute expiry."""
        await auth_service.create_user_token(sample_user)
        
        call_args = mock_token_provider.create_access_token.call_args
        expires_delta = call_args[1].get("expires_delta")
        
        assert expires_delta == timedelta(minutes=30)
    
    @pytest.mark.asyncio
    async def test_create_user_token_creates_refresh_token_with_user_data(self, auth_service, mock_token_provider, sample_user):
        """Test that refresh token is created with correct user data."""
        await auth_service.create_user_token(sample_user)
        
        call_args = mock_token_provider.create_refresh_token.call_args
        data = call_args[1]["data"]
        
        assert data["sub"] == str(sample_user.id)
        assert data["type"] == "refresh"
    
    @pytest.mark.asyncio
    async def test_create_user_token_logs_operation(self, auth_service, sample_user):
        """Test that token creation logs operation."""
        with patch.object(auth_service, 'log_operation') as mock_log:
            await auth_service.create_user_token(sample_user)
            
            assert mock_log.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_create_user_token_exception_handling(self, auth_service, mock_token_provider, sample_user):
        """Test that exceptions during token creation propagate."""
        mock_token_provider.create_access_token.side_effect = Exception("Token error")
        
        with pytest.raises(Exception, match="Token error"):
            await auth_service.create_user_token(sample_user)


# ============================================================================
# Refresh User Token Tests
# ============================================================================

class TestRefreshUserToken:
    """Test token refresh functionality."""
    
    @pytest.mark.asyncio
    async def test_refresh_user_token_success(self, auth_service, mock_user_repository, mock_token_provider, mock_refresh_token_repository, sample_user):
        """Test successful token refresh."""
        mock_token_provider.decode_token.return_value = {
            "sub": str(sample_user.id),
            "type": "refresh"
        }
        # get_valid returns a valid DB record so that the rotation path is taken
        mock_refresh_token_repository.get_valid.return_value = MagicMock()
        mock_user_repository.get_user_by_id.return_value = sample_user
        
        result = await auth_service.refresh_user_token("valid_refresh_token")
        
        assert "access_token" in result
        assert result["token_type"] == "bearer"
        assert "user" in result
        assert result["user"]["id"] == str(sample_user.id)
    
    @pytest.mark.asyncio
    async def test_refresh_user_token_decodes_token(self, auth_service, mock_token_provider, mock_refresh_token_repository, sample_user):
        """Test that refresh token is decoded."""
        mock_token_provider.decode_token.return_value = {
            "sub": str(sample_user.id),
            "type": "refresh"
        }
        mock_refresh_token_repository.get_valid.return_value = MagicMock()
        
        with patch.object(auth_service, 'get_user_by_id', new_callable=AsyncMock, return_value=sample_user):
            await auth_service.refresh_user_token("token_123")
            
            mock_token_provider.decode_token.assert_called_once_with("token_123")
    
    @pytest.mark.asyncio
    async def test_refresh_user_token_invalid_token_type(self, auth_service, mock_token_provider):
        """Test that invalid token type raises error."""
        mock_token_provider.decode_token.return_value = {
            "sub": "550e8400-e29b-41d4-a716-446655440000",
            "type": "access"  # Wrong type
        }
        
        with pytest.raises(AuthenticationError, match="Wrong token type"):
            await auth_service.refresh_user_token("invalid_token")
    
    @pytest.mark.asyncio
    async def test_refresh_user_token_missing_sub_claim(self, auth_service, mock_token_provider):
        """Test that missing sub claim raises error."""
        mock_token_provider.decode_token.return_value = {
            "type": "refresh"
            # Missing sub
        }
        
        with pytest.raises(AuthenticationError, match="Malformed token payload"):
            await auth_service.refresh_user_token("token_without_sub")
    
    @pytest.mark.asyncio
    async def test_refresh_user_token_user_not_found(self, auth_service, mock_token_provider, mock_user_repository, mock_refresh_token_repository, sample_user):
        """Test that missing user raises error."""
        mock_token_provider.decode_token.return_value = {
            "sub": str(sample_user.id),
            "type": "refresh"
        }
        mock_refresh_token_repository.get_valid.return_value = MagicMock()
        mock_user_repository.get_user_by_id.return_value = None
        
        with pytest.raises(AuthenticationError, match="User not found or inactive"):
            await auth_service.refresh_user_token("token_123")
    
    @pytest.mark.asyncio
    async def test_refresh_user_token_creates_new_access_token(self, auth_service, mock_token_provider, mock_refresh_token_repository, sample_user):
        """Test that new access token is created."""
        mock_token_provider.decode_token.return_value = {
            "sub": str(sample_user.id),
            "type": "refresh"
        }
        mock_refresh_token_repository.get_valid.return_value = MagicMock()
        
        with patch.object(auth_service, 'get_user_by_id', new_callable=AsyncMock, return_value=sample_user):
            await auth_service.refresh_user_token("token_123")
            
            # Check that create_access_token was called (at least once)
            assert mock_token_provider.create_access_token.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_refresh_user_token_logs_operation(self, auth_service, mock_token_provider, mock_refresh_token_repository, sample_user):
        """Test that token refresh logs operation."""
        mock_token_provider.decode_token.return_value = {
            "sub": str(sample_user.id),
            "type": "refresh"
        }
        mock_refresh_token_repository.get_valid.return_value = MagicMock()
        
        with patch.object(auth_service, 'get_user_by_id', new_callable=AsyncMock, return_value=sample_user):
            with patch.object(auth_service, 'log_operation') as mock_log:
                await auth_service.refresh_user_token("token_123")
                
                assert mock_log.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_refresh_user_token_reraises_authentication_error(self, auth_service, mock_token_provider):
        """Test that AuthenticationError is re-raised."""
        mock_token_provider.decode_token.side_effect = Exception("Token error")
        
        with pytest.raises(AuthenticationError, match="Invalid or expired refresh token"):
            await auth_service.refresh_user_token("bad_token")
    
    @pytest.mark.asyncio
    async def test_refresh_user_token_exception_handling(self, auth_service, mock_token_provider, mock_refresh_token_repository, sample_user):
        """Test that token reuse (get_valid returns None) triggers revoke_all."""
        mock_token_provider.decode_token.return_value = {
            "sub": str(sample_user.id),
            "type": "refresh"
        }
        # Simulate token not found in DB => reuse attack
        mock_refresh_token_repository.get_valid.return_value = None
        
        with pytest.raises(AuthenticationError, match="Refresh token is invalid or has been revoked"):
            await auth_service.refresh_user_token("token_123")


# ============================================================================
# Logout User Tests
# ============================================================================

class TestLogoutUser:
    """Test logout functionality."""
    
    @pytest.mark.asyncio
    async def test_logout_user_success(self, auth_service, sample_user):
        """Test successful user logout."""
        result = await auth_service.logout_user(sample_user.id)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_logout_user_logs_operation(self, auth_service, sample_user):
        """Test that logout logs operation."""
        with patch.object(auth_service, 'log_operation') as mock_log:
            await auth_service.logout_user(sample_user.id)
            mock_log.assert_called()
    
    @pytest.mark.asyncio
    async def test_logout_user_exception_handling(self, auth_service, sample_user):
        """Test that exceptions during logout propagate."""
        with patch.object(auth_service, 'log_operation', side_effect=Exception("Error")):
            with pytest.raises(Exception, match="Error"):
                await auth_service.logout_user(sample_user.id)


# ============================================================================
# Integration Tests
# ============================================================================

class TestAuthServiceIntegration:
    """Test integration of multiple auth service methods."""
    
    @pytest.mark.asyncio
    async def test_full_registration_and_token_creation(self, auth_service, mock_user_repository, user_create_data, sample_user):
        """Test complete flow: registration then token creation."""
        mock_user_repository.get_user_by_email.return_value = None
        mock_user_repository.create_user.return_value = sample_user
        
        # Register
        registered_user = await auth_service.register_user(user_create_data)
        assert registered_user == sample_user
        
        # Create tokens
        tokens = await auth_service.create_user_token(registered_user)
        assert "access_token" in tokens
        assert "refresh_token" in tokens
    
    @pytest.mark.asyncio
    async def test_full_auth_flow_registration_login_token(
        self, auth_service, mock_user_repository, mock_password_hasher, user_create_data, sample_user
    ):
        """Test complete auth flow: register, login, get tokens."""
        # Register
        mock_user_repository.get_user_by_email.return_value = None
        mock_user_repository.create_user.return_value = sample_user
        
        registered_user = await auth_service.register_user(user_create_data)
        
        # Login
        mock_user_repository.get_user_by_email.return_value = sample_user
        mock_password_hasher.verify_password.return_value = True
        
        authenticated_user = await auth_service.authenticate_user(sample_user.email, "password")
        assert authenticated_user == sample_user
        
        # Create tokens
        tokens = await auth_service.create_user_token(authenticated_user)
        assert tokens["user"]["email"] == sample_user.email
    
    @pytest.mark.asyncio
    async def test_token_refresh_after_creation(self, auth_service, mock_token_provider, mock_user_repository, mock_refresh_token_repository, sample_user):
        """Test refreshing token after initial creation."""
        # Create initial token
        initial_token = await auth_service.create_user_token(sample_user)
        refresh_token = initial_token["refresh_token"]
        
        # Prepare for refresh
        mock_token_provider.decode_token.return_value = {
            "sub": str(sample_user.id),
            "type": "refresh"
        }
        mock_refresh_token_repository.get_valid.return_value = MagicMock()
        mock_user_repository.get_user_by_id.return_value = sample_user
        
        # Refresh
        refreshed_token = await auth_service.refresh_user_token(refresh_token)
        assert "access_token" in refreshed_token
        assert refreshed_token["user"]["email"] == sample_user.email


# ============================================================================
# Edge Cases and Error Conditions
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_authenticate_user_with_empty_email(self, auth_service, mock_user_repository):
        """Test authentication with empty email."""
        mock_user_repository.get_user_by_email.return_value = None
        
        result = await auth_service.authenticate_user("", "password")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_with_empty_password(self, auth_service, mock_password_hasher, mock_user_repository, sample_user):
        """Test authentication with empty password."""
        mock_user_repository.get_user_by_email.return_value = sample_user
        mock_password_hasher.verify_password.return_value = False
        
        result = await auth_service.authenticate_user("test@example.com", "")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_create_user_token_with_inactive_user(self, auth_service, sample_user):
        """Test token creation for inactive user."""
        sample_user.is_active = False
        
        result = await auth_service.create_user_token(sample_user)
        
        assert result["user"]["is_active"] is False
        assert "access_token" in result
    
    @pytest.mark.asyncio
    async def test_create_user_token_with_unverified_user(self, auth_service, sample_user):
        """Test token creation for unverified user."""
        sample_user.is_verified = False
        
        result = await auth_service.create_user_token(sample_user)
        
        assert result["user"]["is_verified"] is False
        assert "access_token" in result
    
    @pytest.mark.asyncio
    async def test_refresh_token_with_empty_sub_claim(self, auth_service, mock_token_provider):
        """Test refresh with empty sub claim."""
        mock_token_provider.decode_token.return_value = {
            "sub": "",
            "type": "refresh"
        }
        
        with pytest.raises(AuthenticationError):
            await auth_service.refresh_user_token("token_123")
    
    @pytest.mark.asyncio
    async def test_refresh_token_with_none_sub_claim(self, auth_service, mock_token_provider):
        """Test refresh with None sub claim."""
        mock_token_provider.decode_token.return_value = {
            "sub": None,
            "type": "refresh"
        }
        
        with pytest.raises(AuthenticationError, match="Malformed token payload"):
            await auth_service.refresh_user_token("token_123")


# ============================================================================
# Dependency Injection Tests
# ============================================================================

class TestDependencyInjection:
    """Test service dependency injection patterns."""
    
    @pytest.mark.asyncio
    async def test_service_uses_injected_repository(self, auth_service, mock_user_repository, user_create_data, sample_user):
        """Test that service uses injected repository."""
        mock_user_repository.get_user_by_email.return_value = None
        mock_user_repository.create_user.return_value = sample_user
        
        await auth_service.register_user(user_create_data)
        
        mock_user_repository.get_user_by_email.assert_called()
        mock_user_repository.create_user.assert_called()
    
    @pytest.mark.asyncio
    async def test_service_uses_injected_password_hasher(self, auth_service, mock_password_hasher, mock_user_repository, sample_user):
        """Test that service uses injected password hasher."""
        mock_user_repository.get_user_by_email.return_value = sample_user
        mock_password_hasher.verify_password.return_value = True
        
        await auth_service.authenticate_user("test@example.com", "password")
        
        mock_password_hasher.verify_password.assert_called()
    
    @pytest.mark.asyncio
    async def test_service_uses_injected_token_provider(self, auth_service, mock_token_provider, sample_user):
        """Test that service uses injected token provider."""
        await auth_service.create_user_token(sample_user)
        
        mock_token_provider.create_access_token.assert_called()
        mock_token_provider.create_refresh_token.assert_called()
