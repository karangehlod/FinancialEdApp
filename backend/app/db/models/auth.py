import json
import uuid

from sqlalchemy import Column, String, Boolean, DateTime, UUID, Text, ARRAY, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator
from app.db.session import AuthBase


class StringList(TypeDecorator):
    """
    A portable list-of-strings column type.

    Uses PostgreSQL ``ARRAY(Text)`` in production and stores JSON-encoded text
    in SQLite (which does not support native ARRAY columns).  This allows the
    same ORM models to be used in both production and the in-memory SQLite
    test suite without modification.
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(Text))
        return dialect.type_descriptor(Text)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value  # native ARRAY handles list natively
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value  # already a Python list
        return json.loads(value)


class User(AuthBase):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    # Nullable to support OAuth-only users (no local password)
    password_hash = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=False), nullable=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now())

    # --- Two-Factor Authentication (P2-3) ---
    # Fernet-encrypted TOTP secret (base32). NULL = 2FA not set up.
    totp_secret_encrypted = Column(Text, nullable=True)
    # True only after the user confirms the first TOTP code post-setup.
    totp_enabled = Column(Boolean, default=False, nullable=False)
    # SHA-256 hash of totp_secret to detect secret rotation.
    totp_secret_hash = Column(String(64), nullable=True)
    # Hashed one-time backup codes (PostgreSQL ARRAY or JSON-serialized TEXT).
    totp_backup_codes = Column(StringList, nullable=True)
    # Timestamp of last successful 2FA login.
    totp_last_used_at = Column(DateTime(timezone=False), nullable=True)


class OAuthAccount(AuthBase):
    """
    Linked social / OAuth account record.

    Design:
      - A user may have multiple OAuth accounts (Google + Apple on same user).
      - provider + provider_user_id is the unique identity key.
      - access_token / refresh_token stored encrypted (optional; needed for
        server-side API calls on behalf of the user).
      - Soft unlink: set is_active = False instead of hard-deleting.

    P2-6: OAuth / Social Login
    """

    __tablename__ = "oauth_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_uid"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    # e.g. "google", "apple"
    provider = Column(String(50), nullable=False)
    # Subject claim from the provider's ID token (immutable, unique per provider)
    provider_user_id = Column(String(255), nullable=False)
    # Normalised email received from the provider (may differ from account email)
    provider_email = Column(String(255), nullable=True)
    # Display name from provider profile
    display_name = Column(String(255), nullable=True)
    # Provider profile picture URL
    avatar_url = Column(Text, nullable=True)
    # Encrypted OAuth access token (optional — only stored if needed for API calls)
    access_token_encrypted = Column(Text, nullable=True)
    # Encrypted OAuth refresh token
    refresh_token_encrypted = Column(Text, nullable=True)
    # Token expiry (access token)
    token_expires_at = Column(DateTime(timezone=False), nullable=True)
    # Soft unlink support
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now())


class RefreshToken(AuthBase):
    """
    Persisted refresh token record.

    Security design:
      - Only a SHA-256 hash of the token is stored (never the raw JWT).
      - Each refresh rotates the token: old record is revoked, new one inserted.
      - ``is_revoked`` enables instant revocation without waiting for expiry.
      - ``device_info`` supports per-device session management.
      - ``replaced_by`` links the rotation chain for audit purposes.
    """

    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    # SHA-256 hash of the raw JWT — never store the token itself
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=False), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    # Optional chain link for token rotation audit
    replaced_by = Column(UUID(as_uuid=True), nullable=True)
    # Free-form device/client info (User-Agent, device ID, etc.)
    device_info = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    revoked_at = Column(DateTime(timezone=False), nullable=True)
    # Timestamp when this token was rotated (if replaced by a newer token)
    rotated_at = Column(DateTime(timezone=False), nullable=True)
