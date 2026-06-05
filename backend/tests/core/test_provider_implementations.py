"""Tests for core provider implementations."""
import pytest
import bcrypt
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from jose import JWTError, jwt
from decimal import Decimal

from app.core.provider_implementations import (
    BcryptPasswordHasher,
    JWTTokenProvider,
    RedisCache,
    AESEncryption,
    DatabaseAuditLogger,
)


# ==================== BcryptPasswordHasher Tests ====================

class TestBcryptPasswordHasher:
    """Test BcryptPasswordHasher."""
    
    def test_hash_password_creates_hash(self):
        """Test that hash_password creates a valid hash."""
        hasher = BcryptPasswordHasher()
        password = "test_password_123"
        
        hashed = hasher.hash_password(password)
        
        assert hashed != password
        assert isinstance(hashed, str)
        assert len(hashed) > 0
    
    def test_hash_password_creates_different_hashes(self):
        """Test that the same password creates different hashes each time."""
        hasher = BcryptPasswordHasher()
        password = "test_password_123"
        
        hash1 = hasher.hash_password(password)
        hash2 = hasher.hash_password(password)
        
        assert hash1 != hash2  # Different salts
    
    def test_verify_password_correct(self):
        """Test verifying correct password."""
        hasher = BcryptPasswordHasher()
        password = "correct_password"
        
        hashed = hasher.hash_password(password)
        result = hasher.verify_password(password, hashed)
        
        assert result is True
    
    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        hasher = BcryptPasswordHasher()
        password = "correct_password"
        wrong_password = "wrong_password"
        
        hashed = hasher.hash_password(password)
        result = hasher.verify_password(wrong_password, hashed)
        
        assert result is False
    
    def test_verify_password_error_handling(self):
        """Test error handling in password verification."""
        hasher = BcryptPasswordHasher()
        
        result = hasher.verify_password("password", "invalid_hash_format")
        
        assert result is False
    
    def test_custom_rounds(self):
        """Test initializing with custom rounds."""
        hasher = BcryptPasswordHasher(rounds=10)
        password = "test_password"
        
        hashed = hasher.hash_password(password)
        
        assert hasher.verify_password(password, hashed)


# ==================== JWTTokenProvider Tests ====================

class TestJWTTokenProvider:
    """Test JWTTokenProvider."""
    
    def test_create_access_token(self):
        """Test creating an access token."""
        provider = JWTTokenProvider(secret_key="test_secret_key")
        data = {"sub": "user123"}
        
        token = provider.create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_access_token_with_custom_expiration(self):
        """Test creating access token with custom expiration."""
        provider = JWTTokenProvider(secret_key="test_secret_key")
        data = {"sub": "user123"}
        expires_delta = timedelta(minutes=15)
        
        token = provider.create_access_token(data, expires_delta)
        
        assert isinstance(token, str)
    
    def test_create_refresh_token(self):
        """Test creating a refresh token."""
        provider = JWTTokenProvider(secret_key="test_secret_key")
        data = {"sub": "user123"}
        
        token = provider.create_refresh_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_token_valid(self):
        """Test decoding a valid token."""
        provider = JWTTokenProvider(secret_key="test_secret_key")
        data = {"sub": "user123", "email": "test@example.com"}
        
        token = provider.create_access_token(data)
        decoded = provider.decode_token(token)
        
        assert decoded["sub"] == "user123"
        assert decoded["email"] == "test@example.com"
    
    def test_decode_token_invalid(self):
        """Test decoding an invalid token."""
        provider = JWTTokenProvider(secret_key="test_secret_key")
        
        with pytest.raises(JWTError):
            provider.decode_token("invalid.token.here")
    
    def test_decode_token_wrong_secret(self):
        """Test decoding token with wrong secret."""
        provider1 = JWTTokenProvider(secret_key="secret_key_1")
        provider2 = JWTTokenProvider(secret_key="secret_key_2")
        
        token = provider1.create_access_token({"sub": "user123"})
        
        with pytest.raises(JWTError):
            provider2.decode_token(token)
    
    def test_is_token_expired_valid_token(self):
        """Test checking if valid token is not expired."""
        provider = JWTTokenProvider(secret_key="test_secret_key")
        data = {"sub": "user123"}
        
        token = provider.create_access_token(data)
        is_expired = provider.is_token_expired(token)
        
        assert is_expired is False
    
    def test_is_token_expired_invalid_token(self):
        """Test checking if invalid token is considered expired."""
        provider = JWTTokenProvider(secret_key="test_secret_key")
        
        is_expired = provider.is_token_expired("invalid.token.here")
        
        assert is_expired is True
    
    def test_is_token_expired_with_expired_token(self):
        """Test checking if truly expired token is detected."""
        provider = JWTTokenProvider(secret_key="test_secret_key")
        data = {"sub": "user123"}
        
        # Create token with negative expiration
        expires_delta = timedelta(minutes=-1)
        token = provider.create_access_token(data, expires_delta)
        
        is_expired = provider.is_token_expired(token)
        
        assert is_expired is True
    
    def test_token_contains_type_field(self):
        """Test that access token contains type field."""
        provider = JWTTokenProvider(secret_key="test_secret_key")
        data = {"sub": "user123"}
        
        token = provider.create_access_token(data)
        decoded = provider.decode_token(token)
        
        assert decoded["type"] == "access"
    
    def test_refresh_token_contains_type_field(self):
        """Test that refresh token contains type field."""
        provider = JWTTokenProvider(secret_key="test_secret_key")
        data = {"sub": "user123"}
        
        token = provider.create_refresh_token(data)
        decoded = provider.decode_token(token)
        
        assert decoded["type"] == "refresh"


# ==================== RedisCache Tests ====================

class TestRedisCache:
    """Test RedisCache."""
    
    @pytest.mark.asyncio
    async def test_set_and_get_value(self):
        """Test setting and getting a value."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "value1"
        mock_redis.set.return_value = True
        
        cache = RedisCache(mock_redis)
        
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        
        assert result == "value1"
        mock_redis.set.assert_called_once()
        mock_redis.get.assert_called_once_with("key1")
    
    @pytest.mark.asyncio
    async def test_get_non_existent_key(self):
        """Test getting a non-existent key returns None."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        
        cache = RedisCache(mock_redis)
        
        result = await cache.get("non_existent_key")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_key(self):
        """Test deleting a key."""
        mock_redis = AsyncMock()
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1  # Redis returns number of keys deleted
        mock_redis.get.return_value = None
        
        cache = RedisCache(mock_redis)
        await cache.set("key1", "value1")
        
        result = await cache.delete("key1")
        
        assert result is True
        assert await cache.get("key1") is None
    
    @pytest.mark.asyncio
    async def test_delete_non_existent_key(self):
        """Test deleting a non-existent key."""
        mock_redis = AsyncMock()
        mock_redis.delete.return_value = 0  # Redis returns 0 for non-existent keys
        
        cache = RedisCache(mock_redis)
        
        result = await cache.delete("non_existent_key")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_exists_key(self):
        """Test checking if key exists."""
        mock_redis = AsyncMock()
        mock_redis.set.return_value = True
        mock_redis.exists.return_value = 1  # Redis returns 1 if key exists
        
        cache = RedisCache(mock_redis)
        await cache.set("key1", "value1")
        
        exists = await cache.exists("key1")
        
        assert exists is True
    
    @pytest.mark.asyncio
    async def test_exists_non_existent_key(self):
        """Test checking if non-existent key exists."""
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 0  # Redis returns 0 if key doesn't exist
        
        cache = RedisCache(mock_redis)
        
        exists = await cache.exists("non_existent_key")
        
        assert exists is False
    
    @pytest.mark.asyncio
    async def test_clear_pattern(self):
        """Test clearing keys matching a pattern."""
        mock_redis = AsyncMock()
        mock_redis.set.return_value = True
        mock_redis.scan.return_value = (0, ["user:1", "user:2"])  # Mocking scan result
        mock_redis.delete.return_value = 2  # 2 keys deleted
        mock_redis.get.side_effect = lambda key: None if key.startswith("user:") else "session1"
        
        cache = RedisCache(mock_redis)
        await cache.set("user:1", "user1")
        await cache.set("user:2", "user2")
        await cache.set("session:1", "session1")
        
        count = await cache.clear_pattern("user:*")
        
        assert count == 2
        assert await cache.get("user:1") is None
        assert await cache.get("session:1") == "session1"
    
    @pytest.mark.asyncio
    async def test_store_different_types(self):
        """Test storing different types of values."""
        mock_redis = AsyncMock()
        mock_redis.set.return_value = True
        # Redis always returns bytes/strings; mock realistic JSON-encoded values
        mock_redis.get.side_effect = lambda key: {
            "string_key": '"string_value"',
            "int_key": '42',
            "list_key": '[1, 2, 3]',
            "dict_key": '{"a": 1, "b": 2}',
        }.get(key)
        
        cache = RedisCache(mock_redis)
        
        await cache.set("string_key", "string_value")
        await cache.set("int_key", 42)
        await cache.set("list_key", [1, 2, 3])
        await cache.set("dict_key", {"a": 1, "b": 2})
        
        assert await cache.get("string_key") == "string_value"
        assert await cache.get("int_key") == 42
        assert await cache.get("list_key") == [1, 2, 3]
        assert await cache.get("dict_key") == {"a": 1, "b": 2}
    
    @pytest.mark.asyncio
    async def test_error_handling_get(self):
        """Test error handling in get operation."""
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis connection error")
        
        cache = RedisCache(mock_redis)
        # Should handle errors gracefully and return None
        result = await cache.get("any_key")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_error_handling_set(self):
        """Test error handling in set operation."""
        mock_redis = AsyncMock()
        mock_redis.set.side_effect = Exception("Redis connection error")
        
        cache = RedisCache(mock_redis)
        # Should handle errors gracefully and return False
        result = await cache.set("key", "value")
        assert result is False


# ==================== AESEncryption Tests ====================

class TestAESEncryption:
    """Test AESEncryption."""
    
    def test_encrypt_and_decrypt(self):
        """Test encrypting and decrypting data."""
        encryptor = AESEncryption(encryption_key="a" * 32)
        plaintext = "sensitive data"
        
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_encrypt_creates_different_ciphertexts(self):
        """Test that encryption creates different ciphertexts each time."""
        encryptor = AESEncryption(encryption_key="a" * 32)
        plaintext = "same plaintext"
        
        encrypted1 = encryptor.encrypt(plaintext)
        encrypted2 = encryptor.encrypt(plaintext)
        
        assert encrypted1 != encrypted2  # Different IVs
    
    def test_encrypt_empty_string(self):
        """Test encrypting empty string."""
        encryptor = AESEncryption(encryption_key="a" * 32)
        
        encrypted = encryptor.encrypt("")
        decrypted = encryptor.decrypt(encrypted)
        
        assert decrypted == ""
    
    def test_encrypt_special_characters(self):
        """Test encrypting special characters."""
        encryptor = AESEncryption(encryption_key="a" * 32)
        plaintext = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_encrypt_unicode(self):
        """Test encrypting unicode characters."""
        encryptor = AESEncryption(encryption_key="a" * 32)
        plaintext = "Hello 世界 🌍 مرحبا"
        
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_hash_value(self):
        """Test hashing a value."""
        encryptor = AESEncryption(encryption_key="a" * 32)
        value = "test_value"
        
        hash1 = encryptor.hash_value(value)
        hash2 = encryptor.hash_value(value)
        
        assert hash1 == hash2  # Hash should be deterministic
        assert hash1 != value
        assert len(hash1) == 64  # SHA256 hex digest
    
    def test_decrypt_invalid_data(self):
        """Test decrypting invalid data."""
        encryptor = AESEncryption(encryption_key="a" * 32)
        
        with pytest.raises(Exception):
            encryptor.decrypt("invalid_encrypted_data")
    
    def test_decrypt_tampered_data(self):
        """Test decrypting tampered encrypted data."""
        encryptor = AESEncryption(encryption_key="a" * 32)
        plaintext = "original message"
        
        encrypted = encryptor.encrypt(plaintext)
        # Tamper with the encrypted data
        tampered = encrypted[:-5] + "xxxxx"
        
        with pytest.raises(Exception):
            encryptor.decrypt(tampered)


# ==================== DatabaseAuditLogger Tests ====================

class TestDatabaseAuditLogger:
    """Test DatabaseAuditLogger."""
    
    @pytest.mark.asyncio
    async def test_log_action_success(self):
        """Test logging an action."""
        db_session = AsyncMock()
        logger = DatabaseAuditLogger(db_session)
        
        result = await logger.log_action(
            user_id="user123",
            action="create",
            resource_type="expense",
            resource_id="expense456"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_log_action_with_changes(self):
        """Test logging an action with changes."""
        db_session = AsyncMock()
        logger = DatabaseAuditLogger(db_session)
        
        changes = {"amount": {"from": 100, "to": 150}}
        result = await logger.log_action(
            user_id="user123",
            action="update",
            resource_type="expense",
            resource_id="expense456",
            changes=changes
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_log_action_with_status(self):
        """Test logging an action with different status."""
        db_session = AsyncMock()
        logger = DatabaseAuditLogger(db_session)
        
        result = await logger.log_action(
            user_id="user123",
            action="delete",
            resource_type="expense",
            resource_id="expense456",
            status="failed"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_log_security_event_info(self):
        """Test logging a security event with info severity."""
        db_session = AsyncMock()
        logger = DatabaseAuditLogger(db_session)
        
        result = await logger.log_security_event(
            user_id="user123",
            event_type="login",
            details={"ip": "192.168.1.1"}
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_log_security_event_warning(self):
        """Test logging a security event with warning severity."""
        db_session = AsyncMock()
        logger = DatabaseAuditLogger(db_session)
        
        result = await logger.log_security_event(
            user_id="user123",
            event_type="failed_login",
            details={"ip": "192.168.1.1", "attempts": 3},
            severity="warning"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_log_security_event_no_user(self):
        """Test logging a security event without user ID."""
        db_session = AsyncMock()
        logger = DatabaseAuditLogger(db_session)
        
        result = await logger.log_security_event(
            user_id=None,
            event_type="unauthorized_access",
            details={"ip": "192.168.1.1"},
            severity="critical"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_get_audit_trail(self):
        """Test getting audit trail."""
        db_session = AsyncMock()
        logger = DatabaseAuditLogger(db_session)
        
        trail = await logger.get_audit_trail("resource123")
        
        assert isinstance(trail, list)
    
    @pytest.mark.asyncio
    async def test_get_audit_trail_with_limit(self):
        """Test getting audit trail with limit."""
        db_session = AsyncMock()
        logger = DatabaseAuditLogger(db_session)
        
        trail = await logger.get_audit_trail("resource123", limit=50)
        
        assert isinstance(trail, list)
    
    @pytest.mark.asyncio
    async def test_log_action_error_handling(self):
        """Test error handling in log action."""
        db_session = AsyncMock()
        db_session.add.side_effect = Exception("Database error")
        logger = DatabaseAuditLogger(db_session)
        
        result = await logger.log_action(
            user_id="user123",
            action="create",
            resource_type="expense",
            resource_id="expense456"
        )
        
        # Should still return True (fail open for logging)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_log_security_event_error_handling(self):
        """Test error handling in log security event."""
        db_session = AsyncMock()
        db_session.add.side_effect = Exception("Database error")
        logger = DatabaseAuditLogger(db_session)
        
        result = await logger.log_security_event(
            user_id="user123",
            event_type="login",
            details={"ip": "192.168.1.1"}
        )
        
        # Should still return True (fail open for security logging)
        assert result is True
