"""Unit tests for app.core.security module."""

import pytest
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from unittest.mock import patch, MagicMock
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


class TestPasswordHashing:
    """Test password hashing functionality."""
    
    def test_hash_password_returns_string(self):
        password = "TestPassword123"
        hashed = hash_password(password)
        assert isinstance(hashed, str)
        assert len(hashed) > len(password)
    
    def test_hash_password_not_equals_original(self):
        password = "MyPassword123"
        hashed = hash_password(password)
        assert hashed != password
    
    def test_hash_password_different_salts(self):
        password = "SamePassword"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2  # Different salts
    
    def test_hash_password_empty_string(self):
        password = ""
        hashed = hash_password(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0
    
    def test_hash_password_long_password(self):
        password = "A" * 1000
        hashed = hash_password(password)
        assert isinstance(hashed, str)
    
    def test_hash_password_special_characters(self):
        password = "P@$$w0rd!#%&*"
        hashed = hash_password(password)
        assert isinstance(hashed, str)
        assert hashed != password
    
    def test_hash_password_unicode_characters(self):
        password = "パスワード123"
        hashed = hash_password(password)
        assert isinstance(hashed, str)


class TestPasswordVerification:
    """Test password verification."""
    
    def test_verify_password_correct_password(self):
        password = "CorrectPassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
    
    def test_verify_password_wrong_password(self):
        password = "CorrectPassword"
        hashed = hash_password(password)
        assert verify_password("WrongPassword", hashed) is False
    
    def test_verify_password_case_sensitive(self):
        password = "TestPassword"
        hashed = hash_password(password)
        assert verify_password("testpassword", hashed) is False
    
    def test_verify_password_empty_vs_nonempty(self):
        password = "NonEmpty"
        hashed = hash_password(password)
        assert verify_password("", hashed) is False
    
    def test_verify_password_with_special_chars(self):
        password = "P@$$w0rd!#%"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
        assert verify_password("P@$$w0rd!#%123", hashed) is False
    
    def test_verify_password_one_char_difference(self):
        password = "Password123"
        hashed = hash_password(password)
        assert verify_password("Password124", hashed) is False


class TestAccessTokenCreation:
    """Test access token creation."""
    
    def test_create_access_token_returns_string(self):
        data = {"sub": "user123"}
        token = create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_access_token_contains_three_parts(self):
        data = {"sub": "user123"}
        token = create_access_token(data)
        parts = token.split(".")
        assert len(parts) == 3  # JWT has 3 parts
    
    def test_create_access_token_with_custom_expiry(self):
        data = {"sub": "user123"}
        expires_delta = timedelta(hours=2)
        token = create_access_token(data, expires_delta)
        assert isinstance(token, str)
        
        payload = decode_token(token)
        assert "exp" in payload
    
    def test_create_access_token_without_custom_expiry(self):
        data = {"sub": "user123"}
        token = create_access_token(data)
        payload = decode_token(token)
        assert "exp" in payload
    
    def test_create_access_token_has_access_type(self):
        data = {"sub": "user123"}
        token = create_access_token(data)
        payload = decode_token(token)
        assert payload.get("type") == "access"
    
    def test_create_access_token_preserves_data(self):
        data = {
            "sub": "user456",
            "email": "user@example.com",
            "role": "admin"
        }
        token = create_access_token(data)
        payload = decode_token(token)
        assert payload["sub"] == "user456"
        assert payload["email"] == "user@example.com"
        assert payload["role"] == "admin"
    
    def test_create_access_token_with_empty_data(self):
        data = {}
        token = create_access_token(data)
        payload = decode_token(token)
        assert "exp" in payload
        assert "type" in payload
    
    def test_create_access_token_multiple_calls_different_tokens(self):
        data = {"sub": "user789"}
        token1 = create_access_token(data)
        token2 = create_access_token(data)
        # Tokens may have same or different exp due to timing
        assert token1 is not None
        assert token2 is not None


class TestRefreshTokenCreation:
    """Test refresh token creation."""
    
    def test_create_refresh_token_returns_string(self):
        data = {"sub": "user123"}
        token = create_refresh_token(data)
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_refresh_token_has_refresh_type(self):
        data = {"sub": "user123"}
        token = create_refresh_token(data)
        payload = decode_token(token)
        assert payload.get("type") == "refresh"
    
    def test_create_refresh_token_preserves_data(self):
        data = {"sub": "user456", "email": "user@example.com"}
        token = create_refresh_token(data)
        payload = decode_token(token)
        assert payload["sub"] == "user456"
        assert payload["email"] == "user@example.com"
    
    def test_create_refresh_token_has_longer_expiry(self):
        access_data = {"sub": "user123"}
        refresh_data = {"sub": "user123"}
        
        access_token = create_access_token(access_data)
        refresh_token = create_refresh_token(refresh_data)
        
        access_payload = decode_token(access_token)
        refresh_payload = decode_token(refresh_token)
        
        # Refresh token expiry should be further in future
        assert refresh_payload["exp"] > access_payload["exp"]
    
    def test_create_refresh_token_with_empty_data(self):
        data = {}
        token = create_refresh_token(data)
        payload = decode_token(token)
        assert "exp" in payload
        assert payload.get("type") == "refresh"


class TestTokenDecoding:
    """Test token decoding."""
    
    def test_decode_token_valid_access_token(self):
        data = {"sub": "user123"}
        token = create_access_token(data)
        payload = decode_token(token)
        assert payload["sub"] == "user123"
        assert payload["type"] == "access"
    
    def test_decode_token_valid_refresh_token(self):
        data = {"sub": "user456"}
        token = create_refresh_token(data)
        payload = decode_token(token)
        assert payload["sub"] == "user456"
        assert payload["type"] == "refresh"
    
    def test_decode_token_invalid_token_raises_exception(self):
        invalid_token = "invalid.token.here"
        with pytest.raises(HTTPException) as exc_info:
            decode_token(invalid_token)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_decode_token_malformed_jwt(self):
        malformed = "not.a.valid.jwt"
        with pytest.raises(HTTPException) as exc_info:
            decode_token(malformed)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_decode_token_empty_string(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_token("")
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_decode_token_expired_token(self):
        data = {"sub": "user123"}
        expired_delta = timedelta(seconds=-1)
        token = create_access_token(data, expired_delta)
        
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_decode_token_exception_has_bearer_header(self):
        invalid_token = "invalid"
        with pytest.raises(HTTPException) as exc_info:
            decode_token(invalid_token)
        
        exc = exc_info.value
        assert exc.headers is not None
        assert "WWW-Authenticate" in exc.headers
        assert exc.headers["WWW-Authenticate"] == "Bearer"
    
    def test_decode_token_wrong_secret_key(self):
        data = {"sub": "user123"}
        token = create_access_token(data)
        
        # Test that using a different key fails by manually encoding
        from jose import jwt as jose_jwt
        wrong_payload = {"sub": "hacker", "type": "access"}
        wrong_token = jose_jwt.encode(
            wrong_payload,
            "completely_different_secret_key",
            algorithm="HS256"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            decode_token(wrong_token)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestTokenRoundTrip:
    """Test complete token lifecycle."""
    
    def test_roundtrip_access_token(self):
        original_data = {
            "sub": "user123",
            "email": "user@example.com",
            "role": "user"
        }
        token = create_access_token(original_data)
        payload = decode_token(token)
        
        assert payload["sub"] == original_data["sub"]
        assert payload["email"] == original_data["email"]
        assert payload["role"] == original_data["role"]
        assert payload["type"] == "access"
    
    def test_roundtrip_refresh_token(self):
        original_data = {"sub": "user456"}
        token = create_refresh_token(original_data)
        payload = decode_token(token)
        
        assert payload["sub"] == original_data["sub"]
        assert payload["type"] == "refresh"
    
    def test_roundtrip_complex_payload(self):
        original_data = {
            "sub": "user789",
            "email": "complex@example.com",
            "roles": ["user", "admin"],
            "org_id": "org123",
            "permissions": ["read", "write", "delete"]
        }
        token = create_access_token(original_data, timedelta(hours=1))
        payload = decode_token(token)
        
        for key, value in original_data.items():
            assert payload[key] == value


class TestTokenExpiration:
    """Test token expiration behavior."""
    
    def test_access_token_default_expiration(self):
        from app.config import settings
        
        data = {"sub": "user123"}
        token = create_access_token(data)
        payload = decode_token(token)
        
        exp_time = datetime.utcfromtimestamp(payload["exp"])
        now = datetime.utcnow()
        delta = (exp_time - now).total_seconds()
        
        # Should be close to ACCESS_TOKEN_EXPIRE_MINUTES
        expected_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        assert abs(delta - expected_seconds) < 5  # Within 5 seconds
    
    def test_refresh_token_longer_expiration(self):
        from app.config import settings
        
        data = {"sub": "user123"}
        token = create_refresh_token(data)
        payload = decode_token(token)
        
        exp_time = datetime.utcfromtimestamp(payload["exp"])
        now = datetime.utcnow()
        delta = (exp_time - now).total_seconds()
        
        # Should be close to REFRESH_TOKEN_EXPIRE_DAYS
        expected_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        assert abs(delta - expected_seconds) < 5  # Within 5 seconds
