"""
AuthService — authentication, token lifecycle, and security operations.

Responsibilities:
  - User registration and authentication
  - Access + refresh token creation (JWT)
  - Refresh token persistence, rotation, and revocation (DB-backed)
  - Account blacklisting (Redis) after logout
  - Account lockout tracking (Redis) on failed logins
  - Password change with old-password verification

Security guarantees:
  - Refresh tokens are never stored in plain text; only SHA-256 hashes are persisted.
  - Token rotation: every /refresh call revokes the old token and issues a new one.
  - Stolen token → detected by DB lookup, all sessions revoked instantly.
  - Failed login tracking → account lockout after N failures (P1-1 prerequisite).

SOLID compliance:
  - Single Responsibility: only auth concerns, no HTTP/ASGI knowledge.
  - Open/Closed: new strategies via TokenProvider / PasswordHasher interfaces.
  - Dependency Inversion: depends on abstract interfaces, not concrete classes.
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from app.config import settings
from app.core.auth_lock import AuthLock
from app.core.exceptions import AuthenticationError, UserAlreadyExistsError
from app.core.providers import CacheProvider, PasswordHasher, TokenProvider
from app.db.models.auth import User
from app.repositories.interfaces import IUserRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.schemas.auth import UserCreate
from app.services.base_service import BaseService
from app.core.cache_service import CacheKey, CacheTTL
from app.utils.datetime_utils import utcnow_naive

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# TTL / threshold constants
# --------------------------------------------------------------------------
_REFRESH_TOKEN_TTL_SECONDS  = 60 * 60 * 24 * 7   # 7 days
_USER_SESSION_BLACKLIST_TTL = 60 * 60 * 24         # 24 hours


class AuthService(BaseService):
    """
    Authentication service with dependency injection and Redis caching.

    Constructor args:
        user_repository:          IUserRepository for user CRUD.
        password_hasher:          PasswordHasher for bcrypt operations.
        token_provider:           TokenProvider for JWT creation/decoding.
        refresh_token_repository: RefreshTokenRepository for DB-backed token lifecycle.
        cache:                    Optional CacheProvider for Redis operations.
    """

    def __init__(
        self,
        user_repository: IUserRepository,
        password_hasher: PasswordHasher,
        token_provider: TokenProvider,
        refresh_token_repository: RefreshTokenRepository,
        cache: Optional[CacheProvider] = None,
    ) -> None:
        super().__init__()
        self.user_repository = user_repository
        self.password_hasher = password_hasher
        self.token_provider = token_provider
        self.refresh_token_repo = refresh_token_repository
        self.cache = cache
        self.auth_lock = AuthLock(cache)
        self.log_operation("auth_service_initialized")
    
    async def validate_dependencies(self) -> bool:
        """Validate that all required dependencies are available."""
        if not all([
            self.user_repository,
            self.password_hasher,
            self.token_provider,
            self.refresh_token_repo,
        ]):
            raise AuthenticationError("One or more required dependencies are not available")
        return True
    
    async def register_user(self, user_data: UserCreate) -> User:
        """Register a new user."""
        operation = "register_user"
        try:
            self.log_operation(operation, {"email": user_data.email})
            
            # Check if user exists
            existing_user = await self.user_repository.get_user_by_email(user_data.email)
            if existing_user:
                raise UserAlreadyExistsError("Email already registered")
            
            # Create new user
            user = await self.user_repository.create_user(user_data)
            self.log_operation(f"{operation}_success", {"user_id": str(user.id)})
            return user
        except (UserAlreadyExistsError, AuthenticationError) as e:
            raise
        except Exception as e:
            self.handle_error(operation, e, {"email": user_data.email})
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Validate email/password and return the User, or None on failure.

        Tracks failed attempts in Redis; raises AuthenticationError if locked out.
        """
        operation = "authenticate_user"
        self.log_operation(operation, {"email": email})

        # Account lockout check
        if await self.auth_lock.is_locked(email):
            logger.warning("Login blocked — account locked out: %s", email)
            raise AuthenticationError("Account temporarily locked. Try again later.")

        user = await self.user_repository.get_user_by_email(email)
        if not user:
            # Consume time to prevent user-enumeration via response timing
            self.password_hasher.verify_password(
                "dummy", "$2b$12$notarealhash00000000000000000000000000000000000"
            )
            await self.auth_lock.record_failed_login(email)
            self.log_operation(f"{operation}_failed_not_found", {"email": email}, level="warning")
            return None

        if not self.password_hasher.verify_password(password, user.password_hash):
            await self.auth_lock.record_failed_login(email)
            self.log_operation(f"{operation}_failed_bad_password", {"email": email}, level="warning")
            return None

        # Successful — clear lockout counter
        await self.auth_lock.clear_failed_logins(email)
        await self.user_repository.update_last_login(user.id)
        self.log_operation(f"{operation}_success", {"user_id": str(user.id)})
        return user
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        operation = "get_user_by_id"
        self.log_operation(operation, {"user_id": str(user_id)})
        return await self.user_repository.get_user_by_id(user_id)

    async def create_user_token(
        self,
        user: User,
        device_info: Optional[str] = None,
    ) -> dict:
        """
        Issue access + refresh tokens and persist the refresh token hash in the DB.

        Args:
            user:        Authenticated User object.
            device_info: Optional device/User-Agent string for session tracking.

        Returns:
            Token response dict with access_token, refresh_token, token_type, user.
        """
        operation = "create_user_token"
        self.log_operation(operation, {"user_id": str(user.id)})

        access_token = self.token_provider.create_access_token(
            data={"sub": str(user.id), "email": user.email},
            expires_delta=timedelta(minutes=30),
        )
        refresh_token = self.token_provider.create_refresh_token(
            data={"sub": str(user.id), "type": "refresh"},
        )

        # Persist hash — never the raw token
        token_hash = _sha256(refresh_token)
        expires_at = utcnow_naive() + timedelta(
            seconds=_REFRESH_TOKEN_TTL_SECONDS
        )
        await self.refresh_token_repo.create(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            device_info=device_info,
        )

        # Populate token->user cache (cache-aside) keyed by user id so
        # subsequent requests presenting the same access token can avoid DB lookup.
        try:
            if self.cache:
                await self.cache.set(
                    CacheKey.token_user(str(user.id)),
                    {
                        "id": str(user.id),
                        "email": user.email,
                        "is_active": user.is_active,
                        "is_verified": user.is_verified,
                    },
                    ttl=CacheTTL.TOKEN_USER,
                )
        except Exception:
            # Non-fatal — cache failures should not block auth flows
            logger.debug("Failed to populate token->user cache for user %s", str(user.id))

        self.log_operation(f"{operation}_success", {"user_id": str(user.id)})
        return _build_token_response(access_token, refresh_token, user)

    async def refresh_user_token(
        self,
        refresh_token: str,
        device_info: Optional[str] = None,
    ) -> dict:
        """
        Rotate a refresh token: validate against the DB, revoke the old one,
        and issue a new access + refresh token pair.

        Security:
          - Token must exist in the DB and not be revoked or expired.
          - If the token is not found (already used or forged), ALL sessions
            for the user are revoked (token reuse attack mitigation).

        Raises:
            AuthenticationError: for any invalid/expired/revoked token.
        """
        operation = "refresh_user_token"
        self.log_operation(operation)

        # 1. Verify JWT signature and expiry
        try:
            payload = self.token_provider.decode_token(refresh_token)
        except Exception as exc:
            raise AuthenticationError("Invalid or expired refresh token") from exc

        if payload.get("type") != "refresh":
            raise AuthenticationError("Wrong token type")

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise AuthenticationError("Malformed token payload")

        # 2. Validate against DB (existence, not revoked, not expired)
        token_hash = _sha256(refresh_token)
        db_record = await self.refresh_token_repo.get_valid(token_hash)
        if db_record is None:
            logger.warning(
                "Refresh token not found or already revoked — possible token reuse for user %s",
                user_id_str,
            )
            # Revoke ALL sessions as a security precaution
            try:
                await self.refresh_token_repo.revoke_all_for_user(UUID(user_id_str))
                if self.cache:
                    await self.cache.set(
                        f"user_blacklist:{user_id_str}", "all_revoked",
                        ttl=_USER_SESSION_BLACKLIST_TTL,
                    )
            except Exception:
                pass
            raise AuthenticationError("Refresh token is invalid or has been revoked")

        # 3. Load user
        user_id = UUID(user_id_str)
        user = await self.user_repository.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")

        # 4. Issue new token pair
        new_access_token = self.token_provider.create_access_token(
            data={"sub": str(user.id), "email": user.email},
        )
        new_refresh_token = self.token_provider.create_refresh_token(
            data={"sub": str(user.id), "type": "refresh"},
        )

        # 5. Atomically rotate: revoke old token + persist new one in a single commit.
        #    This prevents the unique-constraint violation that occurred when
        #    create() and revoke() each committed independently.
        new_hash = _sha256(new_refresh_token)
        new_expires_at = utcnow_naive() + timedelta(
            seconds=_REFRESH_TOKEN_TTL_SECONDS
        )
        await self.refresh_token_repo.rotate(
            old_token_hash=token_hash,
            new_user_id=user.id,
            new_token_hash=new_hash,
            new_expires_at=new_expires_at,
            device_info=device_info,
        )

        # Update token->user cache after rotation
        try:
            if self.cache:
                await self.cache.set(
                    CacheKey.token_user(str(user.id)),
                    {
                        "id": str(user.id),
                        "email": user.email,
                        "is_active": user.is_active,
                        "is_verified": user.is_verified,
                    },
                    ttl=CacheTTL.TOKEN_USER,
                )
        except Exception:
            logger.debug("Failed to update token->user cache for user %s", str(user.id))

        self.log_operation(f"{operation}_success", {"user_id": str(user.id)})
        return _build_token_response(new_access_token, new_refresh_token, user)

    async def logout_user(self, user_id: UUID, refresh_token: Optional[str] = None) -> bool:
        """
        Logout a user:
          1. Revoke the specific refresh token from the DB (if provided).
          2. Add to Redis session blacklist so in-flight access tokens fail fast.
        """
        operation = "logout_user"
        self.log_operation(operation, {"user_id": str(user_id)})

        if refresh_token:
            token_hash = _sha256(refresh_token)
            await self.refresh_token_repo.revoke(token_hash)

        if self.cache:
            await self.cache.set(
                f"user_blacklist:{user_id}", "logged_out",
                ttl=_USER_SESSION_BLACKLIST_TTL,
            )
            # Evict token->user cache so further requests hit DB and fail fast if session ended
            try:
                await self.cache.delete(CacheKey.token_user(str(user_id)))
            except Exception:
                logger.debug("Failed to evict token->user cache for user %s", str(user_id))

        self.log_operation(f"{operation}_success", {"user_id": str(user_id)})
        return True

    async def revoke_all_sessions(self, user_id: UUID) -> int:
        """
        Revoke all active refresh tokens for a user.

        Use on: password change, security event, admin suspension.
        Returns the number of tokens revoked.
        """
        count = await self.refresh_token_repo.revoke_all_for_user(user_id)
        if self.cache:
            await self.cache.set(
                f"user_blacklist:{user_id}", "all_revoked",
                ttl=_USER_SESSION_BLACKLIST_TTL,
            )
        self.log_operation("revoke_all_sessions_success", {"user_id": str(user_id), "count": count})
        return count
    
    async def is_user_blacklisted(self, user_id: UUID) -> bool:
        """Return True if the user has been globally blacklisted (e.g., logged out all sessions)."""
        if not self.cache:
            return False
        try:
            return bool(await self.cache.exists(f"user_blacklist:{user_id}"))
        except Exception as exc:
            logger.error("Error checking user blacklist: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Password change
    # ------------------------------------------------------------------

    async def change_password(self, user_id: UUID, old_password: str, new_password: str) -> bool:
        """
        Change user password after verifying the old one.

        Also revokes all active sessions to force re-login everywhere.

        Raises:
            AuthenticationError: if user not found or old password is wrong.
        """
        operation = "change_password"
        self.log_operation(operation, {"user_id": str(user_id)})

        user = await self.get_user_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")

        if not self.password_hasher.verify_password(old_password, user.password_hash):
            self.log_operation(
                f"{operation}_failed_invalid_old_password",
                {"user_id": str(user_id)},
                level="warning",
            )
            raise AuthenticationError("Current password is incorrect")

        new_hash = self.password_hasher.hash_password(new_password)
        await self.user_repository.update_password(user_id, new_hash)
        await self.revoke_all_sessions(user_id)

        self.log_operation(f"{operation}_success", {"user_id": str(user_id)})
        return True

    async def update_user_profile(self, user_id: UUID, profile_data):
        """Orchestration stub — actual profile update happens in UserProfileRepository."""
        self.log_operation("update_user_profile", {"user_id": str(user_id)})
        return profile_data


# --------------------------------------------------------------------------
# Module-level helpers
# --------------------------------------------------------------------------

def _sha256(value: str) -> str:
    """Return the hex-encoded HMAC-SHA-256 digest of a UTF-8 string using the app secret.

    Uses settings.SECRET_KEY as the HMAC key. This provides a fast, keyed one-way
    hash suitable for storing refresh token fingerprints in the database.
    """
    import hmac
    import hashlib as _hashlib
    key = settings.SECRET_KEY.encode('utf-8')
    return hmac.new(key, value.encode('utf-8'), _hashlib.sha256).hexdigest()


def _build_token_response(access_token: str, refresh_token: str, user: User) -> dict:
    """Construct the standard token response payload."""
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
        },
    }


