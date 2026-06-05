"""Concrete provider implementations."""

import bcrypt
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import hashlib
import logging
from jose import JWTError, jwt

from app.core.providers import (
    PasswordHasher,
    TokenProvider,
    CacheProvider,
    EncryptionProvider,
    AuditLogger,
)
from app.config import settings

logger = logging.getLogger(__name__)


class BcryptPasswordHasher(PasswordHasher):
    """Bcrypt-based password hashing implementation."""
    
    def __init__(self, rounds: int = 12):
        """
        Initialize password hasher.
        
        Args:
            rounds: Number of rounds for bcrypt hashing (higher = slower but more secure)
        """
        self.rounds = rounds
    
    def hash_password(self, password: str) -> str:
        """Hash a plain text password using bcrypt."""
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=self.rounds)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        try:
            password_bytes = plain_password.encode('utf-8')
            hashed_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception as e:
            logger.error("Error verifying password: %s", e)
            return False


class JWTTokenProvider(TokenProvider):
    """JWT-based token provider implementation."""
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7
    ):
        """
        Initialize JWT token provider.
        
        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm to use
            access_token_expire_minutes: Access token expiration time
            refresh_token_expire_days: Refresh token expiration time
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
    
    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create an access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=self.access_token_expire_minutes
            )
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(
            to_encode,
            self.secret_key,
            algorithm=self.algorithm
        )
        return encoded_jwt
    
    def create_refresh_token(self, data: dict) -> str:
        """Create a refresh token."""
        import uuid as _uuid
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh", "jti": str(_uuid.uuid4())})
        encoded_jwt = jwt.encode(
            to_encode,
            self.secret_key,
            algorithm=self.algorithm
        )
        return encoded_jwt
    
    def decode_token(self, token: str) -> dict:
        """Decode and validate a token."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except JWTError as e:
            logger.error("Error decoding token: %s", e)
            raise
    
    def is_token_expired(self, token: str) -> bool:
        """Check if a token is expired.

        Uses UTC-based timestamp comparison to avoid local timezone issues.
        """
        try:
            payload = self.decode_token(token)
            exp = payload.get("exp")
            if exp is None:
                return True
            # exp is an int epoch-seconds value per the JWT spec
            try:
                exp_dt = datetime.fromtimestamp(int(exp), tz=timezone.utc)
            except Exception:
                if isinstance(exp, datetime):
                    exp_dt = exp.replace(tzinfo=timezone.utc) if exp.tzinfo is None else exp
                else:
                    return True
            return exp_dt < datetime.now(timezone.utc)
        except Exception:
            return True
    
    def compute_token_sha256(self, token: str) -> str:
        """Return SHA-256 hex digest for a given token string.

        Clear name (sha256) to distinguish from HMAC-based digests used for DB storage.
        """
        return hashlib.sha256(token.encode('utf-8')).hexdigest()

    # Backwards-compatible alias for existing callers
    _compute_token_hash = compute_token_sha256

    def compute_token_hmac(self, token: str) -> str:
        """Return HMAC-SHA256 hex digest for a given token using the application secret.

        Use HMAC when persisting/verifying tokens in the DB to avoid storing raw token/unsalted hashes.
        """
        import hmac
        import hashlib as _hashlib
        key = settings.SECRET_KEY.encode('utf-8')
        return hmac.new(key, token.encode('utf-8'), _hashlib.sha256).hexdigest()

    @staticmethod
    def secure_compare(a: str, b: str) -> bool:
        """Constant-time comparison for digests to avoid timing attacks."""
        import hmac as _hmac
        try:
            return _hmac.compare_digest(a, b)
        except Exception:
            return False


class RedisCache(CacheProvider):
    """Redis-based cache provider with TTL support."""
    
    def __init__(self, redis_client):
        """
        Initialize cache provider with Redis client.
        
        Args:
            redis_client: Async Redis client instance (required)
        """
        if redis_client is None:
            raise ValueError("RedisCache requires a valid Redis client")
        self.redis = redis_client
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from Redis cache and deserialize it from JSON.

        Returns:
            Deserialized Python object, or None if the key doesn't exist.
        """
        try:
            raw = await self.redis.get(key)
            if raw is None:
                return None
            # Redis client commonly returns bytes; decode to string first
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode('utf-8')
            # Deserialize JSON → Python object
            return json.loads(raw)
        except json.JSONDecodeError:
            # Value stored as plain string (legacy) — return as-is
            return raw
        except Exception as exc:
            # Avoid logging sensitive content; include key and exception for triage
            logger.debug("Cache GET error for key '%s': %s", key, exc)
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Serialize ``value`` to JSON and store it in Redis.

        Args:
            key:   Cache key.
            value: Any JSON-serialisable Python object.
            ttl:   Time-to-live in seconds (None = no expiry).
        """
        try:
            serialized = json.dumps(value, default=str)  # default=str handles UUID/Decimal/date
            if ttl:
                await self.redis.setex(key, ttl, serialized)
            else:
                await self.redis.set(key, serialized)
            return True
        except Exception as exc:
            logger.debug("Cache SET error for key '%s': %s", key, exc)
            return False

    async def delete(self, key: str) -> bool:
        """Delete a single key from Redis."""
        try:
            await self.redis.delete(key)
            return True
        except Exception as exc:
            logger.debug("Cache DELETE error for key '%s': %s", key, exc)
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a glob pattern using non-blocking SCAN.

        Uses SCAN instead of KEYS to avoid blocking Redis on large datasets.
        """
        try:
            cursor: int = 0
            deleted: int = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted += await self.redis.delete(*keys)
                if cursor == 0:
                    break
            logger.debug("Cleared %d cache keys matching '%s'", deleted, pattern)
            return deleted
        except Exception as exc:
            logger.debug("Cache CLEAR_PATTERN error for pattern '%s': %s", pattern, exc)
            return 0

    async def exists(self, key: str) -> bool:
        """Check whether a key exists in Redis."""
        try:
            return bool(await self.redis.exists(key))
        except Exception as exc:
            logger.debug("Cache EXISTS error for key '%s': %s", key, exc)
            return False

    async def increment(self, key: str, ttl: Optional[int] = None) -> int:
        """
        Atomically increment an integer counter stored at ``key``.

        Useful for lightweight counters (e.g., login-attempt tracking).
        """
        try:
            count = await self.redis.incr(key)
            if ttl and count == 1:
                # Only set TTL on first increment so the window starts now
                await self.redis.expire(key, ttl)
            return count
        except Exception as exc:
            logger.debug("Cache INCREMENT error for key '%s': %s", key, exc)
            return 0


class AESEncryption(EncryptionProvider):
    """AES-based encryption provider implementation."""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize AES encryption provider.
        
        Args:
            encryption_key: Encryption key (uses settings.ENCRYPTION_KEY if not provided)
        """
        from cryptography.fernet import Fernet
        import base64

        self.encryption_key = encryption_key or settings.ENCRYPTION_KEY

        # If the provided value already looks like a valid Fernet key (urlsafe base64 32 bytes -> 44 chars),
        # use it directly. Otherwise derive a Fernet-compatible key from the passphrase using PBKDF2HMAC.
        try:
            key_bytes = None
            if isinstance(self.encryption_key, str) and len(self.encryption_key) == 44:
                # probably a valid Fernet URL-safe base64-encoded key
                key_bytes = self.encryption_key.encode('utf-8')
            else:
                # Derive a stable key from passphrase using PBKDF2HMAC. A salt should be provided via
                # settings.ENCRYPTION_SALT for production; fallback to a stable application salt.
                from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
                from cryptography.hazmat.primitives import hashes
                from cryptography.hazmat.backends import default_backend

                salt = getattr(settings, 'ENCRYPTION_SALT', None)
                if salt is None:
                    # Warn but continue; using a fixed fallback salt is less secure but keeps compatibility
                    logger.warning('ENCRYPTION_SALT not set; using default fallback salt. Consider setting ENCRYPTION_SALT in secure config.')
                    salt = b'financialapp-default-salt'
                if isinstance(salt, str):
                    salt = salt.encode('utf-8')

                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100_000,
                    backend=default_backend()
                )
                key_bytes = base64.urlsafe_b64encode(
                    kdf.derive((self.encryption_key or '').encode('utf-8'))
                )

            self.cipher = Fernet(key_bytes)
        except Exception as e:
            logger.error('Failed to initialize AESEncryption: %s', e)
            # Re-raise so misconfiguration fails fast during startup rather than silently degrade
            raise
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext data."""
        try:
            plaintext_bytes = plaintext.encode('utf-8')
            encrypted = self.cipher.encrypt(plaintext_bytes)
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.debug("Error encrypting data: %s", e)
            raise
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext data."""
        try:
            ciphertext_bytes = ciphertext.encode('utf-8')
            decrypted = self.cipher.decrypt(ciphertext_bytes)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.debug("Error decrypting data: %s", e)
            raise
    
    def hash_value(self, value: str) -> str:
        """Hash a value (one-way encryption)."""
        import hashlib
        return hashlib.sha256(value.encode('utf-8')).hexdigest()


class DatabaseAuditLogger(AuditLogger):
    """Database-backed audit logger implementation.

    NOTE: current implementation is a lightweight stub that logs to the application logger.
    For production audit queries and retention, implement DB-backed storage (e.g. audit table
    and use the provided db_session to persist events)."""
    
    def __init__(self, db_session):
        """
        Initialize database audit logger.
        
        Args:
            db_session: Database session
        """
        self.db = db_session
    
    async def log_action(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        changes: Optional[Dict[str, Any]] = None,
        status: str = "success"
    ) -> bool:
        """Log an action for audit purposes."""
        try:
            # This will be implemented with actual database model
            # For now, just log to logger (non-persistent)
            logger.info(
                f"Audit: user={user_id}, action={action}, "
                f"resource={resource_type}:{resource_id}, status={status}",
                extra={"changes": changes}
            )
            return True
        except Exception as e:
            logger.debug("Error logging audit action: %s", e)
            return False
    
    async def log_security_event(
        self,
        user_id: Optional[str],
        event_type: str,
        details: Dict[str, Any],
        severity: str = "info"
    ) -> bool:
        """Log a security-related event."""
        try:
            logger.warning(
                f"Security Event: user={user_id}, type={event_type}, "
                f"severity={severity}",
                extra={"details": details}
            )
            return True
        except Exception as e:
            logger.debug("Error logging security event: %s", e)
            return False
    
    async def get_audit_trail(
        self,
        resource_id: str,
        limit: int = 100
    ) -> list:
        """Get audit trail for a resource."""
        # This will be implemented with actual database queries
        return []
