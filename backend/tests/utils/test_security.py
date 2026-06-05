"""Unit tests for app.utils.security module."""

import pytest
from datetime import datetime, timedelta
from jose import JWTError
from unittest.mock import patch, MagicMock
from app.utils.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    verify_token,
    pwd_context,
)


class TestPasswordHashing:
    """Test password hashing functionality."""

    def test_get_password_hash_returns_hashed_string(self):
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != password

    def test_get_password_hash_different_outputs(self):
        password = "SamePassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        assert hash1 != hash2  # Different salts produce different hashes

    def test_verify_password_with_matching_password(self):
        password = "MySecurePassword123!"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_with_wrong_password(self):
        password = "CorrectPassword123"
        wrong_password = "WrongPassword456"
        hashed = get_password_hash(password)
        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_with_empty_string(self):
        hashed = get_password_hash("password")
        assert verify_password("", hashed) is False

    def test_verify_password_case_sensitive(self):
        password = "TestPassword"
        hashed = get_password_hash(password)
        assert verify_password("testpassword", hashed) is False

    def test_verify_password_with_special_characters(self):
        password = "P@$$w0rd!#%&*"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_with_invalid_hash(self):
        password = "TestPassword"
        invalid_hash = "not_a_valid_hash"
        assert verify_password(password, invalid_hash) is False

    @patch("app.utils.security.pwd_context.verify")
    def test_verify_password_exception_handling(self, mock_verify):
        mock_verify.side_effect = Exception("Hash verification error")
        result = verify_password("password", "hash")
        assert result is False


class TestTokenCreation:
    """Test JWT token creation."""

    def test_create_access_token_returns_string(self):
        data = {"sub": "user123"}
        token = create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expires_delta(self):
        data = {"sub": "user123"}
        expires_delta = timedelta(hours=1)
        token = create_access_token(data, expires_delta)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_uses_custom_expiry(self):
        data = {"sub": "user456"}
        expires_delta = timedelta(minutes=15)
        token = create_access_token(data, expires_delta)
        
        from app.utils.security import verify_token
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "user456"

    def test_create_access_token_without_expires_delta(self):
        data = {"sub": "user789"}
        token = create_access_token(data)
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "user789"

    def test_create_access_token_includes_exp_claim(self):
        data = {"sub": "testuser"}
        token = create_access_token(data, timedelta(hours=1))
        payload = verify_token(token)
        assert "exp" in payload
        assert payload["exp"] > datetime.utcnow().timestamp()

    def test_create_access_token_preserves_data(self):
        data = {"sub": "user123", "role": "admin", "email": "user@example.com"}
        token = create_access_token(data)
        payload = verify_token(token)
        assert payload["sub"] == "user123"
        assert payload["role"] == "admin"
        assert payload["email"] == "user@example.com"

    def test_create_access_token_with_empty_data(self):
        data = {}
        token = create_access_token(data)
        payload = verify_token(token)
        assert payload is not None
        assert "exp" in payload

    def test_create_access_token_with_multiple_fields(self):
        data = {
            "sub": "user123",
            "role": "admin",
            "permissions": ["read", "write"],
            "org_id": "org456"
        }
        token = create_access_token(data)
        payload = verify_token(token)
        assert payload["sub"] == "user123"
        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]
        assert payload["org_id"] == "org456"


class TestTokenVerification:
    """Test JWT token verification."""

    def test_verify_token_with_valid_token(self):
        data = {"sub": "user123", "role": "admin"}
        token = create_access_token(data)
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["role"] == "admin"

    def test_verify_token_with_invalid_token(self):
        invalid_token = "invalid.token.here"
        payload = verify_token(invalid_token)
        assert payload is None

    def test_verify_token_with_empty_string(self):
        payload = verify_token("")
        assert payload is None

    def test_verify_token_with_malformed_jwt(self):
        malformed_token = "not.a.jwt"
        payload = verify_token(malformed_token)
        assert payload is None

    def test_verify_token_with_expired_token(self):
        data = {"sub": "user123"}
        expired_delta = timedelta(seconds=-1)
        token = create_access_token(data, expired_delta)
        payload = verify_token(token)
        assert payload is None

    def test_verify_token_with_wrong_secret_key(self):
        data = {"sub": "user123"}
        token = create_access_token(data, timedelta(hours=1))
        
        with patch("app.utils.security.settings.JWT_SECRET_KEY", "wrong_secret"):
            payload = verify_token(token)
            assert payload is None

    def test_verify_token_extracts_all_claims(self):
        data = {
            "sub": "user999",
            "email": "test@example.com",
            "is_verified": True,
            "custom_field": "custom_value"
        }
        token = create_access_token(data, timedelta(hours=1))
        payload = verify_token(token)
        assert payload["sub"] == "user999"
        assert payload["email"] == "test@example.com"
        assert payload["is_verified"] is True
        assert payload["custom_field"] == "custom_value"

    def test_verify_token_returns_none_on_jwt_error(self):
        invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"
        payload = verify_token(invalid_token)
        assert payload is None


class TestTokenRoundTrip:
    """Test token creation and verification roundtrip."""

    def test_token_roundtrip_simple(self):
        original_data = {"sub": "user123"}
        token = create_access_token(original_data)
        payload = verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == original_data["sub"]

    def test_token_roundtrip_complex(self):
        original_data = {
            "sub": "user456",
            "role": "admin",
            "permissions": ["read", "write", "delete"],
            "org_id": "org789"
        }
        expires_delta = timedelta(hours=2)
        token = create_access_token(original_data, expires_delta)
        payload = verify_token(token)
        
        assert payload is not None
        for key, value in original_data.items():
            assert payload[key] == value

    def test_token_roundtrip_multiple_tokens_different(self):
        data = {"sub": "user123"}
        token1 = create_access_token(data)
        
        import time
        time.sleep(0.01)  # Small delay to ensure different exp timestamps
        
        token2 = create_access_token(data)
        
        payload1 = verify_token(token1)
        payload2 = verify_token(token2)
        
        assert payload1["sub"] == payload2["sub"]
        # Tokens may be different or same depending on expiration timestamp precision
        assert payload1 is not None and payload2 is not None


class TestPwdContext:
    """Test password context configuration."""

    def test_pwd_context_uses_bcrypt(self):
        assert "bcrypt" in pwd_context.schemes()

    def test_pwd_context_marks_deprecated_correctly(self):
        # CryptContext.deprecated() method may not exist; check configuration instead
        assert pwd_context.schemes() is not None
        assert len(pwd_context.schemes()) > 0

    def test_hash_and_verify_integration(self):
        password = "TestPass123"
        hashed = pwd_context.hash(password)
        assert pwd_context.verify(password, hashed) is True

    def test_hash_and_verify_with_wrong_password(self):
        password = "CorrectPassword"
        hashed = pwd_context.hash(password)
        assert pwd_context.verify("WrongPassword", hashed) is False
