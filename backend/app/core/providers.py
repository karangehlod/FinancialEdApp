"""Provider interfaces for dependency injection and composition."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import timedelta


class PasswordHasher(ABC):
    """Interface for password hashing operations."""
    
    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash a plain text password."""
        pass
    
    @abstractmethod
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        pass


class TokenProvider(ABC):
    """Interface for JWT token operations."""
    
    @abstractmethod
    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create an access token."""
        pass
    
    @abstractmethod
    def create_refresh_token(self, data: dict) -> str:
        """Create a refresh token."""
        pass
    
    @abstractmethod
    def decode_token(self, token: str) -> dict:
        """Decode and validate a token."""
        pass
    
    @abstractmethod
    def is_token_expired(self, token: str) -> bool:
        """Check if a token is expired."""
        pass


class EmailProvider(ABC):
    """Interface for email sending operations."""
    
    @abstractmethod
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[Dict[str, bytes]] = None
    ) -> bool:
        """Send an email asynchronously."""
        pass
    
    @abstractmethod
    async def send_bulk_email(
        self,
        recipients: list,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> Dict[str, bool]:
        """Send emails to multiple recipients."""
        pass
    
    @abstractmethod
    async def send_templated_email(
        self,
        to: str,
        template_name: str,
        context: Dict[str, Any]
    ) -> bool:
        """Send a templated email."""
        pass


class NotificationProvider(ABC):
    """Interface for notification operations."""
    
    @abstractmethod
    async def send_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: str
    ) -> bool:
        """Send a notification to a user."""
        pass
    
    @abstractmethod
    async def send_bulk_notification(
        self,
        user_ids: list,
        title: str,
        message: str,
        notification_type: str
    ) -> Dict[str, bool]:
        """Send notifications to multiple users."""
        pass


class CacheProvider(ABC):
    """Interface for caching operations."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        pass
    
    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set a value in cache."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        pass
    
    @abstractmethod
    async def clear_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        pass


class EncryptionProvider(ABC):
    """Interface for encryption operations."""
    
    @abstractmethod
    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext data."""
        pass
    
    @abstractmethod
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext data."""
        pass
    
    @abstractmethod
    def hash_value(self, value: str) -> str:
        """Hash a value (one-way encryption)."""
        pass


class AuditLogger(ABC):
    """Interface for audit logging operations."""
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def log_security_event(
        self,
        user_id: Optional[str],
        event_type: str,
        details: Dict[str, Any],
        severity: str = "info"
    ) -> bool:
        """Log a security-related event."""
        pass
    
    @abstractmethod
    async def get_audit_trail(
        self,
        resource_id: str,
        limit: int = 100
    ) -> list:
        """Get audit trail for a resource."""
        pass


class RateLimitProvider(ABC):
    """Interface for rate limiting operations."""
    
    @abstractmethod
    async def is_allowed(
        self,
        identifier: str,
        limit: int,
        window: int
    ) -> bool:
        """Check if an action is within rate limit."""
        pass
    
    @abstractmethod
    async def get_remaining(
        self,
        identifier: str,
        limit: int,
        window: int
    ) -> int:
        """Get remaining requests in current window."""
        pass
    
    @abstractmethod
    async def reset(self, identifier: str) -> bool:
        """Reset rate limit for an identifier."""
        pass


class CircuitBreakerProvider(ABC):
    """Interface for circuit breaker pattern."""
    
    @abstractmethod
    async def call(
        self,
        operation,
        *args,
        **kwargs
    ) -> Any:
        """Execute an operation with circuit breaker protection."""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the circuit is available."""
        pass
    
    @abstractmethod
    async def reset(self) -> None:
        """Reset the circuit breaker."""
        pass
