"""
OAuth / Social Login endpoints — P2-6

Endpoints:
  GET  /auth/oauth/{provider}/authorize   — redirect URL + state
  POST /auth/oauth/{provider}/callback    — code exchange → app JWT tokens
  GET  /auth/oauth/providers              — list linked providers for current user
  DELETE /auth/oauth/{provider}           — unlink a social provider

Supported providers: google, apple

Flow (Google example):
  1. Frontend calls GET /auth/oauth/google/authorize
     → receives { auth_url, state }
  2. Frontend redirects user to auth_url (Google sign-in screen)
  3. Google redirects back to frontend with ?code=...&state=...
  4. Frontend POSTs { code, state, redirect_uri } to /auth/oauth/google/callback
  5. Backend exchanges code → ID token → verifies → creates/looks up user
  6. Backend returns { access_token, refresh_token, token_type, user }

Apple flow:
  Apple uses form_post, so the frontend will receive a POST from Apple's servers
  with code, id_token, state, and optionally user (first sign-in only).
  The frontend forwards these fields to POST /auth/oauth/apple/callback.

Security:
  - State parameter validated server-side (Redis CSRF protection).
  - ID tokens verified against provider's JWKs endpoint.
  - Rate limited at 10 req/min on the callback endpoint.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AuthenticationError
from app.core.logging import get_logger
from app.db.session import get_auth_db
from app.dependencies import get_current_user, get_redis_cache, get_token_provider
from app.repositories.oauth_account_repository import OAuthAccountRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.oauth_service import OAuthService, SUPPORTED_PROVIDERS

logger = get_logger(__name__)
router = APIRouter(prefix="/auth/oauth", tags=["OAuth / Social Login"])

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class OAuthAuthorizeResponse(BaseModel):
    """Returned to the frontend so it can redirect the user."""
    auth_url: str = Field(..., description="Provider authorization URL")
    state: str = Field(..., description="CSRF state token (store and pass back on callback)")


class GoogleCallbackRequest(BaseModel):
    code: str = Field(..., description="Authorization code from Google")
    state: str = Field(..., description="State token (must match the one from /authorize)")
    redirect_uri: str = Field(..., description="Exact redirect URI used in the authorize call")


class AppleCallbackRequest(BaseModel):
    code: str = Field(..., description="Authorization code from Apple")
    state: str = Field(..., description="State token (must match the one from /authorize)")
    id_token: Optional[str] = Field(None, description="ID token from Apple (form_post)")
    user: Optional[str] = Field(None, description="User JSON from Apple (first sign-in only)")


class LinkedProviderResponse(BaseModel):
    provider: str
    provider_email: Optional[str]
    display_name: Optional[str]
    avatar_url: Optional[str]
    linked_at: Optional[str]


# ---------------------------------------------------------------------------
# Dependency: build OAuthService per request
# ---------------------------------------------------------------------------


def get_oauth_service(
    request: Request,
    auth_db: AsyncSession = Depends(get_auth_db),
    token_provider=Depends(get_token_provider),
    cache=Depends(get_redis_cache),
) -> OAuthService:
    return OAuthService(
        user_repository=UserRepository(auth_db),
        oauth_repository=OAuthAccountRepository(auth_db),
        refresh_token_repository=RefreshTokenRepository(auth_db),
        token_provider=token_provider,
        cache=cache,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{provider}/authorize",
    response_model=OAuthAuthorizeResponse,
    summary="Get OAuth authorization URL",
    description=(
        "Returns the provider's authorization URL and a CSRF state token. "
        "The frontend must store the state and include it in the callback request."
    ),
)
async def oauth_authorize(
    provider: str,
    redirect_uri: str,
    oauth_svc: OAuthService = Depends(get_oauth_service),
):
    """
    Generate authorization URL for the requested OAuth provider.

    Query params:
      - provider:      "google" or "apple"
      - redirect_uri:  The frontend callback URL (must match the provider config)
    """
    provider = provider.lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider '{provider}'. Supported: {sorted(SUPPORTED_PROVIDERS)}",
        )

    # Validate that provider credentials are configured
    _check_provider_configured(provider)

    state = await oauth_svc.generate_oauth_state(provider)

    if provider == "google":
        auth_url = oauth_svc.get_google_auth_url(redirect_uri=redirect_uri, state=state)
    else:  # apple
        auth_url = oauth_svc.get_apple_auth_url(redirect_uri=redirect_uri, state=state)

    logger.info("OAuth authorize: provider=%s", provider)
    return OAuthAuthorizeResponse(auth_url=auth_url, state=state)


@router.post(
    "/google/callback",
    summary="Handle Google OAuth callback",
    description="Exchange the Google authorization code for app JWT tokens.",
)
async def google_callback(
    body: GoogleCallbackRequest,
    request: Request,
    oauth_svc: OAuthService = Depends(get_oauth_service),
):
    """
    Google OAuth 2.0 callback handler.

    The frontend receives `code` and `state` from Google's redirect and
    forwards them here along with the original `redirect_uri`.
    Returns the same token shape as the password login endpoint.
    """
    _check_provider_configured("google")
    device_info = request.headers.get("User-Agent")
    try:
        tokens = await oauth_svc.handle_google_callback(
            code=body.code,
            redirect_uri=body.redirect_uri,
            state=body.state,
            device_info=device_info,
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except Exception as exc:
        logger.error("Google OAuth callback error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google authentication failed. Please try again.",
        )

    logger.info("Google OAuth login success: user_id=%s", tokens["user"]["id"])
    return tokens


@router.post(
    "/apple/callback",
    summary="Handle Apple Sign-in callback",
    description=(
        "Handle the Apple Sign-in form_post callback. "
        "Apple POSTs code, state, id_token, and (first sign-in only) user to your backend."
    ),
)
async def apple_callback(
    body: AppleCallbackRequest,
    request: Request,
    oauth_svc: OAuthService = Depends(get_oauth_service),
):
    """
    Apple Sign-in callback handler.

    On first sign-in Apple includes the user's name in the `user` field (JSON string).
    On subsequent sign-ins only `code`, `state`, and `id_token` are provided.
    Returns the same token shape as the password login endpoint.
    """
    _check_provider_configured("apple")
    device_info = request.headers.get("User-Agent")
    try:
        tokens = await oauth_svc.handle_apple_callback(
            code=body.code,
            id_token=body.id_token,
            state=body.state,
            user_json=body.user,
            device_info=device_info,
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except Exception as exc:
        logger.error("Apple OAuth callback error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Apple authentication failed. Please try again.",
        )

    logger.info("Apple OAuth login success: user_id=%s", tokens["user"]["id"])
    return tokens


@router.get(
    "/providers",
    response_model=list[LinkedProviderResponse],
    summary="List linked OAuth providers",
    description="Returns all OAuth providers currently linked to the authenticated user.",
)
async def list_linked_providers(
    current_user=Depends(get_current_user),
    oauth_svc: OAuthService = Depends(get_oauth_service),
):
    """List all active OAuth provider links for the current user."""
    providers = await oauth_svc.list_linked_providers(current_user.id)
    return providers


@router.delete(
    "/{provider}",
    status_code=status.HTTP_200_OK,
    summary="Unlink an OAuth provider",
    description=(
        "Soft-unlinks the specified OAuth provider from the current user's account. "
        "Blocked if it's the user's only sign-in method and they have no local password."
    ),
)
async def unlink_provider(
    provider: str,
    current_user=Depends(get_current_user),
    oauth_svc: OAuthService = Depends(get_oauth_service),
):
    """Unlink an OAuth provider from the current user's account."""
    provider = provider.lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider '{provider}'",
        )
    try:
        unlinked = await oauth_svc.unlink_provider(current_user.id, provider)
    except (AuthenticationError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if not unlinked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active '{provider}' link found for this account",
        )

    logger.info(
        "OAuth provider unlinked: user_id=%s provider=%s",
        current_user.id,
        provider,
    )
    return {"detail": f"'{provider}' unlinked successfully"}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _check_provider_configured(provider: str) -> None:
    """Raise 503 if the provider credentials are not configured."""
    if provider == "google":
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google Sign-In is not configured on this server",
            )
    elif provider == "apple":
        if not all([
            settings.APPLE_CLIENT_ID,
            settings.APPLE_TEAM_ID,
            settings.APPLE_KEY_ID,
            settings.APPLE_PRIVATE_KEY,
        ]):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Apple Sign-In is not configured on this server",
            )
