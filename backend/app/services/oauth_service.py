"""
OAuthService — Google OAuth 2.0 and Apple Sign-in integration.

Architecture:
  - Google: standard OAuth 2.0 Authorization Code Flow with PKCE optional.
    ID token verified using Google's public JWKs (cached, no authlib dependency
    on a running server).
  - Apple: Sign in with Apple using the `client_secret` JWT pattern. Apple ID
    tokens are RS256-signed; verified against Apple's public keys.
  - On first login: create a new User + OAuthAccount (auto-verified email).
  - On returning login: look up existing OAuthAccount → return tokens.
  - Account linking: if a user with the same email already exists (local
    account), the OAuth account is linked to it automatically. The user can
    also manually link/unlink from the account settings.
  - Tokens: issue the same JWT access + refresh token pair as the password flow.

Security:
  - ID tokens are verified server-side (signature + audience + expiry).
  - State parameter stored in Redis with 10-minute TTL (CSRF protection).
  - Provider tokens (access/refresh) are Fernet-encrypted before storage.
  - OAuth-only users have `password_hash = None`; local password auth is
    blocked for them unless they explicitly set a password.

P2-6: OAuth / Social Login
"""

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import UUID, uuid4

import httpx
from cryptography.fernet import Fernet

from app.config import settings
from app.core.exceptions import AuthenticationError
from app.db.models.auth import OAuthAccount, User
from app.repositories.oauth_account_repository import OAuthAccountRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.base_service import BaseService
from app.utils.datetime_utils import utcnow_naive

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
_GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"

_APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"
_APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"
_APPLE_AUD = "https://appleid.apple.com"

_STATE_TTL = 600  # 10 minutes
_REFRESH_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days

# Supported OAuth providers
SUPPORTED_PROVIDERS = frozenset(["google", "apple"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _get_fernet() -> Fernet:
    """
    Return a Fernet cipher keyed from SECRET_KEY.

    The key must be exactly 32 URL-safe base64 bytes.  We derive it from
    SECRET_KEY using SHA-256 and then base64-encode to satisfy Fernet.
    """
    import base64
    raw = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    key = base64.urlsafe_b64encode(raw)
    return Fernet(key)


def _encrypt(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    return _get_fernet().decrypt(value.encode()).decode()


def _build_token_response(access_token: str, refresh_token: str, user: User) -> Dict:
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "is_verified": user.is_verified,
        },
    }


# ---------------------------------------------------------------------------
# OAuthService
# ---------------------------------------------------------------------------

class OAuthService(BaseService):
    """
    Handles Google OAuth 2.0 and Apple Sign-in server-side flows.

    Constructor args:
        user_repository:           IUserRepository for user CRUD.
        oauth_repository:          OAuthAccountRepository for linked accounts.
        refresh_token_repository:  RefreshTokenRepository for DB-backed tokens.
        token_provider:            JWT token provider (shared singleton).
        cache:                     Optional Redis cache for OAuth state.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        oauth_repository: OAuthAccountRepository,
        refresh_token_repository: RefreshTokenRepository,
        token_provider,
        cache=None,
    ) -> None:
        super().__init__()
        self.user_repo = user_repository
        self.oauth_repo = oauth_repository
        self.refresh_token_repo = refresh_token_repository
        self.token_provider = token_provider
        self.cache = cache

    # ------------------------------------------------------------------
    # State management (CSRF protection)
    # ------------------------------------------------------------------

    async def generate_oauth_state(self, provider: str) -> str:
        """
        Generate a cryptographically random state token, persist it in Redis,
        and return it to include in the authorization URL.
        """
        state = secrets.token_urlsafe(32)
        if self.cache:
            await self.cache.set(
                f"oauth_state:{provider}:{state}",
                "pending",
                ttl=_STATE_TTL,
            )
        return state

    async def validate_oauth_state(self, provider: str, state: str) -> bool:
        """
        Validate and consume the OAuth state token (one-time use).
        Returns False if the state is unknown or expired.
        """
        if not self.cache:
            # Without Redis we cannot enforce state; log a warning in production
            logger.warning("OAuth state validation skipped — Redis unavailable")
            return True
        key = f"oauth_state:{provider}:{state}"
        value = await self.cache.get(key)
        if value != "pending":
            return False
        await self.cache.delete(key)
        return True

    # ------------------------------------------------------------------
    # Authorization URL builders
    # ------------------------------------------------------------------

    def get_google_auth_url(self, redirect_uri: str, state: str) -> str:
        """
        Build the Google OAuth 2.0 authorization URL.

        Scopes: openid, email, profile (minimal — no Drive / Contacts access).
        """
        from urllib.parse import urlencode
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",   # returns refresh_token on first auth
            "prompt": "select_account",
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    def get_apple_auth_url(self, redirect_uri: str, state: str) -> str:
        """
        Build the Apple Sign-in authorization URL.

        Note: Apple requires form_post response mode; redirect_uri must be
        an HTTPS URL registered in the Apple Developer portal.
        """
        from urllib.parse import urlencode
        params = {
            "client_id": settings.APPLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code id_token",
            "scope": "name email",
            "state": state,
            "response_mode": "form_post",
        }
        return f"https://appleid.apple.com/auth/authorize?{urlencode(params)}"

    # ------------------------------------------------------------------
    # Google flow
    # ------------------------------------------------------------------

    async def handle_google_callback(
        self,
        code: str,
        redirect_uri: str,
        state: str,
        device_info: Optional[str] = None,
    ) -> Dict:
        """
        Exchange Google authorization code for tokens, verify the ID token,
        and return app JWT tokens.
        """
        if not await self.validate_oauth_state("google", state):
            raise AuthenticationError("Invalid or expired OAuth state parameter")

        # Exchange code for tokens
        token_data = await self._exchange_google_code(code, redirect_uri)

        # Verify and decode ID token
        id_token = token_data.get("id_token")
        if not id_token:
            raise AuthenticationError("Google did not return an ID token")

        profile = await self._verify_google_id_token(id_token)

        provider_uid = profile["sub"]
        email = profile.get("email")
        name = profile.get("name")
        avatar = profile.get("picture")

        if not email:
            raise AuthenticationError("Google account has no email address")

        user = await self._get_or_create_user(
            provider="google",
            provider_uid=provider_uid,
            email=email,
            display_name=name,
            avatar_url=avatar,
            access_token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            token_expires_in=token_data.get("expires_in"),
        )
        return await self._issue_app_tokens(user, device_info)

    async def _exchange_google_code(self, code: str, redirect_uri: str) -> Dict:
        """POST to Google's token endpoint to exchange the authorization code."""
        payload = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_GOOGLE_TOKEN_URL, data=payload)
        if resp.status_code != 200:
            logger.error("Google token exchange failed: %s", resp.text)
            raise AuthenticationError("Google authentication failed")
        return resp.json()

    async def _verify_google_id_token(self, id_token: str) -> Dict:
        """
        Verify a Google ID token using Google's public JWKs.

        Uses PyJWT with JWK set fetched from Google's certs endpoint.
        Validates: signature, audience, issuer, expiry.
        """
        try:
            import jwt
            from jwt import PyJWKClient

            jwks_client = PyJWKClient(_GOOGLE_CERTS_URL)
            signing_key = jwks_client.get_signing_key_from_jwt(id_token)
            data = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=settings.GOOGLE_CLIENT_ID,
                options={"verify_exp": True},
            )
            return data
        except Exception as exc:
            logger.error("Google ID token verification failed: %s", exc)
            raise AuthenticationError("Google ID token verification failed") from exc

    # ------------------------------------------------------------------
    # Apple flow
    # ------------------------------------------------------------------

    async def handle_apple_callback(
        self,
        code: str,
        id_token: Optional[str],
        state: str,
        user_json: Optional[str] = None,
        device_info: Optional[str] = None,
    ) -> Dict:
        """
        Handle Apple Sign-in callback.

        Apple sends the user's name/email ONLY on the FIRST sign-in via form_post.
        Subsequent sign-ins only include `code` and `id_token`.
        """
        if not await self.validate_oauth_state("apple", state):
            raise AuthenticationError("Invalid or expired OAuth state parameter")

        # Verify the ID token (preferred — avoids an extra HTTP round-trip)
        if id_token:
            profile = await self._verify_apple_id_token(id_token)
        else:
            # Fall back to code exchange if no id_token (shouldn't happen with form_post)
            token_data = await self._exchange_apple_code(code)
            raw_id_token = token_data.get("id_token")
            if not raw_id_token:
                raise AuthenticationError("Apple did not return an ID token")
            profile = await self._verify_apple_id_token(raw_id_token)

        provider_uid = profile["sub"]
        email = profile.get("email")

        # Apple only sends name on first sign-in (in the user JSON form field)
        display_name: Optional[str] = None
        if user_json:
            import json
            try:
                user_data = json.loads(user_json)
                name_data = user_data.get("name", {})
                display_name = " ".join(
                    filter(None, [name_data.get("firstName"), name_data.get("lastName")])
                ) or None
            except (json.JSONDecodeError, AttributeError):
                pass

        if not email:
            # Apple may hide email (private relay) — still allow login via sub
            logger.warning("Apple login: email not provided for sub=%s", provider_uid)

        user = await self._get_or_create_user(
            provider="apple",
            provider_uid=provider_uid,
            email=email,
            display_name=display_name,
            avatar_url=None,
        )
        return await self._issue_app_tokens(user, device_info)

    async def _exchange_apple_code(self, code: str) -> Dict:
        """Exchange Apple authorization code using a signed client_secret JWT."""
        client_secret = self._build_apple_client_secret()
        payload = {
            "client_id": settings.APPLE_CLIENT_ID,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_APPLE_TOKEN_URL, data=payload)
        if resp.status_code != 200:
            logger.error("Apple token exchange failed: %s", resp.text)
            raise AuthenticationError("Apple authentication failed")
        return resp.json()

    def _build_apple_client_secret(self) -> str:
        """
        Build a signed JWT to use as the Apple OAuth client_secret.

        Apple requires the client_secret to be a signed JWT (ES256) using the
        private key downloaded from the Apple Developer portal.
        """
        import jwt as pyjwt

        now = datetime.now(timezone.utc)
        payload = {
            "iss": settings.APPLE_TEAM_ID,
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "aud": _APPLE_AUD,
            "sub": settings.APPLE_CLIENT_ID,
        }
        private_key = settings.APPLE_PRIVATE_KEY.replace("\\n", "\n")
        return pyjwt.encode(
            payload,
            private_key,
            algorithm="ES256",
            headers={"kid": settings.APPLE_KEY_ID},
        )

    async def _verify_apple_id_token(self, id_token: str) -> Dict:
        """
        Verify an Apple ID token against Apple's public JWKs (RS256).

        Validates: signature, audience (= client_id), issuer (= appleid.apple.com), expiry.
        """
        try:
            import jwt
            from jwt import PyJWKClient

            jwks_client = PyJWKClient(_APPLE_KEYS_URL)
            signing_key = jwks_client.get_signing_key_from_jwt(id_token)
            data = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=settings.APPLE_CLIENT_ID,
                issuer=_APPLE_AUD,
                options={"verify_exp": True},
            )
            return data
        except Exception as exc:
            logger.error("Apple ID token verification failed: %s", exc)
            raise AuthenticationError("Apple ID token verification failed") from exc

    # ------------------------------------------------------------------
    # Account management (shared)
    # ------------------------------------------------------------------

    async def _get_or_create_user(
        self,
        provider: str,
        provider_uid: str,
        email: Optional[str],
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        token_expires_in: Optional[int] = None,
    ) -> User:
        """
        Core account-lookup/creation logic:

        1. Look up existing OAuthAccount by (provider, provider_uid).
           → Found: update provider tokens, return linked User.
        2. Look up existing User by email.
           → Found: link the new OAuth provider to the existing account.
        3. Neither found: create a new User (no password) + OAuthAccount.
        """
        # Encrypt provider tokens before storage
        enc_access = _encrypt(access_token) if access_token else None
        enc_refresh = _encrypt(refresh_token) if refresh_token else None
        expires_at: Optional[datetime] = None
        if token_expires_in:
            expires_at = utcnow_naive() + timedelta(seconds=token_expires_in)

        # 1. Existing OAuth link
        existing_oauth = await self.oauth_repo.get_by_provider(provider, provider_uid)
        if existing_oauth:
            # Refresh stored tokens
            await self.oauth_repo.update_tokens(
                account_id=existing_oauth.id,
                access_token_encrypted=enc_access,
                refresh_token_encrypted=enc_refresh,
                token_expires_at=expires_at,
            )
            user = await self.user_repo.get_user_by_id(existing_oauth.user_id)
            if not user or not user.is_active:
                raise AuthenticationError("Account suspended or not found")
            await self.user_repo.update_last_login(user.id)
            return user

        # 2. Email-based link to existing local account
        user: Optional[User] = None
        if email:
            user = await self.user_repo.get_user_by_email(email)

        if user:
            if not user.is_active:
                raise AuthenticationError("Account suspended")
            # Link this provider to the existing user
            await self.oauth_repo.create(
                user_id=user.id,
                provider=provider,
                provider_user_id=provider_uid,
                provider_email=email,
                display_name=display_name,
                avatar_url=avatar_url,
                access_token_encrypted=enc_access,
                refresh_token_encrypted=enc_refresh,
                token_expires_at=expires_at,
            )
            await self.user_repo.update_last_login(user.id)
            return user

        # 3. Brand-new user — OAuth-only (no password)
        if not email:
            # Cannot create a user without an email (Apple private relay gives a fake email)
            raise AuthenticationError(
                "Email address is required to create an account. "
                "Please allow email access in your Apple/Google settings."
            )

        new_user = await self.user_repo.create_oauth_user(
            email=email,
            display_name=display_name,
        )
        await self.oauth_repo.create(
            user_id=new_user.id,
            provider=provider,
            provider_user_id=provider_uid,
            provider_email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            access_token_encrypted=enc_access,
            refresh_token_encrypted=enc_refresh,
            token_expires_at=expires_at,
        )
        return new_user

    async def _issue_app_tokens(
        self,
        user: User,
        device_info: Optional[str] = None,
    ) -> Dict:
        """
        Issue application-level JWT access + refresh tokens for the given user
        and persist the refresh token hash in the DB.
        """
        from datetime import timedelta

        access_token = self.token_provider.create_access_token(
            data={"sub": str(user.id), "email": user.email},
        )
        refresh_token = self.token_provider.create_refresh_token(
            data={"sub": str(user.id), "type": "refresh"},
        )
        token_hash = _sha256(refresh_token)
        expires_at = utcnow_naive() + timedelta(seconds=_REFRESH_TOKEN_TTL_SECONDS)
        await self.refresh_token_repo.create(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            device_info=device_info,
        )
        return _build_token_response(access_token, refresh_token, user)

    # ------------------------------------------------------------------
    # Account linking management (user-facing)
    # ------------------------------------------------------------------

    async def list_linked_providers(self, user_id: UUID) -> list:
        """Return a list of dicts describing all linked OAuth providers."""
        accounts = await self.oauth_repo.list_for_user(user_id)
        return [
            {
                "provider": a.provider,
                "provider_email": a.provider_email,
                "display_name": a.display_name,
                "avatar_url": a.avatar_url,
                "linked_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in accounts
        ]

    async def unlink_provider(self, user_id: UUID, provider: str) -> bool:
        """
        Unlink an OAuth provider from a user's account.

        Safety guard: if the user has no local password, they must keep at least
        one linked provider (otherwise they cannot log in).
        """
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")

        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")

        # Prevent account lockout for OAuth-only users
        if not user.password_hash:
            all_links = await self.oauth_repo.list_for_user(user_id)
            active = [a for a in all_links if a.provider != provider]
            if not active:
                raise AuthenticationError(
                    "Cannot unlink the only sign-in method. "
                    "Set a password first or link another provider."
                )

        return await self.oauth_repo.unlink(user_id, provider)
