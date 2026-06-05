"""Unit tests for app.schemas.auth module."""

import pytest
from datetime import datetime
from uuid import UUID
from pydantic import ValidationError
from app.schemas.auth import (
    UserRegister,
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    TokenResponse,
    UserUpdate,
    PasswordChange,
)


class TestUserRegister:
    """Test UserRegister schema."""
    
    def test_user_register_valid(self):
        data = {
            "email": "user@example.com",
            "password": "SecurePass123",
            "full_name": "John Doe"
        }
        user = UserRegister(**data)
        assert user.email == "user@example.com"
        assert user.password == "SecurePass123"
        assert user.full_name == "John Doe"
    
    def test_user_register_without_full_name(self):
        data = {
            "email": "user@example.com",
            "password": "SecurePass123"
        }
        user = UserRegister(**data)
        assert user.full_name is None
    
    def test_user_register_password_too_short(self):
        data = {
            "email": "user@example.com",
            "password": "Short1",  # Less than 8 chars
            "full_name": "John Doe"
        }
        with pytest.raises(ValidationError):
            UserRegister(**data)
    
    def test_user_register_password_exactly_8_chars(self):
        data = {
            "email": "user@example.com",
            "password": "Pass1234",  # Exactly 8 chars
            "full_name": "John Doe"
        }
        user = UserRegister(**data)
        assert len(user.password) == 8
    
    def test_user_register_password_100_chars(self):
        data = {
            "email": "user@example.com",
            "password": "P" * 100,  # 100 chars
            "full_name": "John Doe"
        }
        user = UserRegister(**data)
        assert len(user.password) == 100
    
    def test_user_register_password_exceeds_max(self):
        data = {
            "email": "user@example.com",
            "password": "P" * 101,  # Exceeds 100 chars
            "full_name": "John Doe"
        }
        with pytest.raises(ValidationError):
            UserRegister(**data)
    
    def test_user_register_invalid_email(self):
        data = {
            "email": "not-an-email",
            "password": "SecurePass123",
            "full_name": "John Doe"
        }
        with pytest.raises(ValidationError):
            UserRegister(**data)
    
    def test_user_register_missing_email(self):
        data = {
            "password": "SecurePass123",
            "full_name": "John Doe"
        }
        with pytest.raises(ValidationError):
            UserRegister(**data)
    
    def test_user_register_missing_password(self):
        data = {
            "email": "user@example.com",
            "full_name": "John Doe"
        }
        with pytest.raises(ValidationError):
            UserRegister(**data)


class TestUserCreate:
    """Test UserCreate schema."""
    
    def test_user_create_valid(self):
        data = {
            "email": "newuser@example.com",
            "password": "NewPass123",
            "full_name": "Jane Doe"
        }
        user = UserCreate(**data)
        assert user.email == "newuser@example.com"
        assert user.password == "NewPass123"
        assert user.full_name == "Jane Doe"
    
    def test_user_create_is_alias_for_user_register(self):
        # UserCreate should behave identically to UserRegister
        data = {
            "email": "user@example.com",
            "password": "SecurePass123",
            "full_name": "John Doe"
        }
        user_register = UserRegister(**data)
        user_create = UserCreate(**data)
        
        assert user_register.email == user_create.email
        assert user_register.password == user_create.password
        assert user_register.full_name == user_create.full_name


class TestUserLogin:
    """Test UserLogin schema."""
    
    def test_user_login_valid(self):
        data = {
            "email": "user@example.com",
            "password": "SecurePass123"
        }
        login = UserLogin(**data)
        assert login.email == "user@example.com"
        assert login.password == "SecurePass123"
    
    def test_user_login_invalid_email(self):
        data = {
            "email": "invalid-email",
            "password": "SecurePass123"
        }
        with pytest.raises(ValidationError):
            UserLogin(**data)
    
    def test_user_login_missing_email(self):
        data = {"password": "SecurePass123"}
        with pytest.raises(ValidationError):
            UserLogin(**data)
    
    def test_user_login_missing_password(self):
        data = {"email": "user@example.com"}
        with pytest.raises(ValidationError):
            UserLogin(**data)


class TestUserResponse:
    """Test UserResponse schema."""
    
    def test_user_response_valid(self):
        user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        now = datetime.utcnow()
        data = {
            "id": user_id,
            "email": "user@example.com",
            "is_active": True,
            "is_verified": True,
            "created_at": now
        }
        response = UserResponse(**data)
        assert response.id == user_id
        assert response.email == "user@example.com"
        assert response.is_active is True
        assert response.is_verified is True
    
    def test_user_response_from_attributes(self):
        # Test Config.from_attributes = True
        class MockUser:
            id = UUID("550e8400-e29b-41d4-a716-446655440000")
            email = "mock@example.com"
            is_active = True
            is_verified = False
            created_at = datetime.utcnow()
        
        response = UserResponse.model_validate(MockUser())
        assert response.email == "mock@example.com"
    
    def test_user_response_missing_id(self):
        data = {
            "email": "user@example.com",
            "is_active": True,
            "is_verified": True,
            "created_at": datetime.utcnow()
        }
        with pytest.raises(ValidationError):
            UserResponse(**data)


class TestToken:
    """Test Token schema."""
    
    def test_token_valid(self):
        data = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer"
        }
        token = Token(**data)
        assert token.access_token == data["access_token"]
        assert token.token_type == "bearer"
    
    def test_token_default_type(self):
        data = {"access_token": "token123"}
        token = Token(**data)
        assert token.token_type == "bearer"
    
    def test_token_custom_type(self):
        data = {
            "access_token": "token123",
            "token_type": "Bearer"
        }
        token = Token(**data)
        assert token.token_type == "Bearer"
    
    def test_token_missing_access_token(self):
        data = {"token_type": "bearer"}
        with pytest.raises(ValidationError):
            Token(**data)


class TestTokenResponse:
    """Test TokenResponse schema."""
    
    def test_token_response_valid(self):
        data = {
            "access_token": "token123",
            "refresh_token": "refresh_abc",
            "token_type": "bearer",
            "user": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "is_active": True
            }
        }
        response = TokenResponse(**data)
        assert response.access_token == "token123"
        assert response.refresh_token == "refresh_abc"
        assert response.token_type == "bearer"
        assert response.user["email"] == "user@example.com"
    
    def test_token_response_with_complex_user_dict(self):
        data = {
            "access_token": "token456",
            "refresh_token": "refresh_def",
            "token_type": "bearer",
            "user": {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "email": "another@example.com",
                "is_active": True,
                "is_verified": True,
                "roles": ["user", "admin"],
                "created_at": "2025-01-16T00:00:00"
            }
        }
        response = TokenResponse(**data)
        assert response.user["roles"] == ["user", "admin"]
    
    def test_token_response_missing_user(self):
        data = {
            "access_token": "token789",
            "token_type": "bearer"
        }
        with pytest.raises(ValidationError):
            TokenResponse(**data)


class TestUserUpdate:
    """Test UserUpdate schema."""
    
    def test_user_update_all_fields(self):
        data = {
            "email": "newemail@example.com",
            "is_active": False,
            "is_verified": True
        }
        update = UserUpdate(**data)
        assert update.email == "newemail@example.com"
        assert update.is_active is False
        assert update.is_verified is True
    
    def test_user_update_partial(self):
        data = {"email": "newemail@example.com"}
        update = UserUpdate(**data)
        assert update.email == "newemail@example.com"
        assert update.is_active is None
        assert update.is_verified is None
    
    def test_user_update_empty(self):
        data = {}
        update = UserUpdate(**data)
        assert update.email is None
        assert update.is_active is None
        assert update.is_verified is None
    
    def test_user_update_invalid_email(self):
        data = {"email": "not-an-email"}
        with pytest.raises(ValidationError):
            UserUpdate(**data)
    
    def test_user_update_is_active_only(self):
        data = {"is_active": False}
        update = UserUpdate(**data)
        assert update.is_active is False
        assert update.email is None
    
    def test_user_update_is_verified_only(self):
        data = {"is_verified": True}
        update = UserUpdate(**data)
        assert update.is_verified is True
        assert update.email is None


class TestPasswordChange:
    """Test PasswordChange schema."""
    
    def test_password_change_valid(self):
        data = {
            "current_password": "OldPass123",
            "new_password": "NewPass456"
        }
        change = PasswordChange(**data)
        assert change.current_password == "OldPass123"
        assert change.new_password == "NewPass456"
    
    def test_password_change_current_password_required(self):
        data = {"new_password": "NewPass456"}
        with pytest.raises(ValidationError):
            PasswordChange(**data)
    
    def test_password_change_new_password_required(self):
        data = {"current_password": "OldPass123"}
        with pytest.raises(ValidationError):
            PasswordChange(**data)
    
    def test_password_change_new_password_too_short(self):
        data = {
            "current_password": "OldPass123",
            "new_password": "Short1"  # Less than 8 chars
        }
        with pytest.raises(ValidationError):
            PasswordChange(**data)
    
    def test_password_change_new_password_exactly_8_chars(self):
        data = {
            "current_password": "OldPass123",
            "new_password": "Pass1234"  # Exactly 8 chars
        }
        change = PasswordChange(**data)
        assert len(change.new_password) == 8
    
    def test_password_change_new_password_exceeds_max(self):
        data = {
            "current_password": "OldPass123",
            "new_password": "P" * 101  # Exceeds 100 chars
        }
        with pytest.raises(ValidationError):
            PasswordChange(**data)
    
    def test_password_change_same_passwords(self):
        # Schema allows same passwords (business logic should validate)
        data = {
            "current_password": "SamePass123",
            "new_password": "SamePass123"
        }
        change = PasswordChange(**data)
        assert change.current_password == change.new_password


class TestSchemaFieldConstraints:
    """Test schema field constraints and validation."""
    
    def test_email_case_sensitivity(self):
        # Pydantic EmailStr normalizes email domain to lowercase
        login1 = UserLogin(email="User@Example.Com", password="Pass123456")
        login2 = UserLogin(email="user@example.com", password="Pass123456")
        # Both normalize to lowercase domain
        assert login1.email == "User@example.com"
        assert login2.email == "user@example.com"
    
    def test_password_special_characters(self):
        data = {
            "email": "user@example.com",
            "password": "P@$$w0rd!#%&*123"
        }
        register = UserRegister(**data)
        assert "@" in register.password
        assert "$" in register.password
        assert "!" in register.password
    
    def test_full_name_optional_nullable(self):
        data = {
            "email": "user@example.com",
            "password": "SecurePass123",
            "full_name": None
        }
        register = UserRegister(**data)
        assert register.full_name is None
    
    def test_uuid_validation(self):
        valid_uuid = UUID("550e8400-e29b-41d4-a716-446655440000")
        data = {
            "id": valid_uuid,
            "email": "user@example.com",
            "is_active": True,
            "is_verified": False,
            "created_at": datetime.utcnow()
        }
        response = UserResponse(**data)
        assert response.id == valid_uuid
    
    def test_datetime_validation(self):
        now = datetime.utcnow()
        data = {
            "id": UUID("550e8400-e29b-41d4-a716-446655440000"),
            "email": "user@example.com",
            "is_active": True,
            "is_verified": True,
            "created_at": now
        }
        response = UserResponse(**data)
        assert response.created_at == now
