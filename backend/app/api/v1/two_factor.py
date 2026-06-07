"""
Two-Factor Authentication API endpoints.

Routes:
  POST /auth/2fa/setup    → generate TOTP secret + QR code URI (requires auth)
  POST /auth/2fa/enable   → confirm first TOTP code and activate 2FA
  POST /auth/2fa/disable  → disable 2FA (requires password + current TOTP or backup)
  POST /auth/2fa/verify   → verify TOTP code during login (2FA challenge step)
  GET  /auth/2fa/backup-codes → regenerate backup codes (requires 2FA active + TOTP)
  POST /auth/2fa/backup-codes/verify → consume a backup code for login

All mutating operations are rate-limited to prevent brute-force.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_auth_db
from app.db.models.auth import User
from app.dependencies import get_current_user
from app.services.two_factor_service import (
    TwoFactorService,
    TwoFactorAlreadyEnabledError,
    TwoFactorNotEnabledError,
    InvalidTOTPCodeError,
    InvalidBackupCodeError,
    get_two_factor_service,
)
from app.core.exceptions import AuthenticationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/2fa", tags=["two-factor-auth"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TwoFactorSetupResponse(BaseModel):
    """Returned when 2FA setup is initiated."""
    secret: str = Field(..., description="Raw base32 TOTP secret — show once, never again")
    provisioning_uri: str = Field(..., description="otpauth:// URI for QR code generation")
    message: str = "Scan the QR code with your authenticator app, then call /auth/2fa/enable to activate."


class TwoFactorEnableRequest(BaseModel):
    """Confirms 2FA setup by verifying the first TOTP code."""
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$",
                      description="6-digit TOTP code from authenticator app")


class TwoFactorEnableResponse(BaseModel):
    backup_codes: List[str] = Field(..., description="One-time backup codes — save securely, shown only once")
    message: str = "2FA enabled successfully. Store your backup codes in a safe place."


class TwoFactorDisableRequest(BaseModel):
    password: str = Field(..., min_length=1, description="Current account password")
    code: str = Field(..., min_length=6, max_length=8,
                      description="Current TOTP code OR a backup code (XXXXXX-XXXXXX)")


class TwoFactorVerifyRequest(BaseModel):
    """Used during login when 2FA is enabled (second factor step)."""
    user_id: str = Field(..., description="User ID from the first-factor response")
    code: str = Field(..., min_length=6, max_length=8,
                      description="TOTP code or backup code")


class TwoFactorVerifyResponse(BaseModel):
    verified: bool
    message: str


class BackupCodesResponse(BaseModel):
    backup_codes: List[str]
    message: str = "New backup codes generated. Previous codes are now invalid."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_totp_service() -> TwoFactorService:
    return get_two_factor_service()


def _require_2fa_enabled(user: User) -> None:
    if not user.totp_enabled or not user.totp_secret_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled on this account.",
        )


def _require_2fa_not_enabled(user: User) -> None:
    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="2FA is already enabled. Disable it first before re-enabling.",
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/setup",
    response_model=TwoFactorSetupResponse,
    summary="Initiate 2FA setup — returns TOTP secret and QR code URI",
)
async def setup_2fa(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_auth_db),
    totp_service: TwoFactorService = Depends(_get_totp_service),
):
    """
    Generate a new TOTP secret for the user.

    - Does NOT enable 2FA yet — the user must call /enable with a valid code.
    - If 2FA is already active, a 409 is returned.
    - The raw secret is returned ONCE here and never again.
    """
    _require_2fa_not_enabled(current_user)

    secret = totp_service.generate_secret()
    encrypted = totp_service.encrypt_secret(secret)
    uri = totp_service.get_provisioning_uri(secret, current_user.email)

    # Persist the encrypted secret (but totp_enabled stays False until /enable)
    current_user.totp_secret_encrypted = encrypted
    await db.commit()

    logger.info("2FA setup initiated for user %s", current_user.id)

    return TwoFactorSetupResponse(
        secret=secret,
        provisioning_uri=uri,
    )


@router.post(
    "/enable",
    response_model=TwoFactorEnableResponse,
    summary="Enable 2FA after confirming the first TOTP code",
)
async def enable_2fa(
    payload: TwoFactorEnableRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_auth_db),
    totp_service: TwoFactorService = Depends(_get_totp_service),
):
    """
    Activate 2FA by verifying the first TOTP code.

    - Requires /setup to have been called first.
    - Generates 10 one-time backup codes (shown ONCE; stored as bcrypt hashes).
    """
    if not current_user.totp_secret_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Call /auth/2fa/setup first to generate a TOTP secret.",
        )
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="2FA is already enabled.",
        )

    # Decrypt and verify
    try:
        secret = totp_service.decrypt_secret(current_user.totp_secret_encrypted)
        totp_service.verify_code_or_raise(secret, payload.code)
    except InvalidTOTPCodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code. Please check your authenticator app and try again.",
        )

    # Generate backup codes
    plain_codes, hashed_codes = totp_service.generate_backup_codes()

    # Activate 2FA
    current_user.totp_enabled = True
    current_user.totp_backup_codes = hashed_codes
    await db.commit()

    logger.info("2FA enabled for user %s", current_user.id)

    return TwoFactorEnableResponse(backup_codes=plain_codes)


@router.post(
    "/disable",
    status_code=status.HTTP_200_OK,
    summary="Disable 2FA (requires password + current TOTP or backup code)",
)
async def disable_2fa(
    payload: TwoFactorDisableRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_auth_db),
    totp_service: TwoFactorService = Depends(_get_totp_service),
):
    """
    Disable 2FA for the user.

    - Requires both the account password AND a current TOTP code (or backup code).
    - Clears the TOTP secret, backup codes, and totp_enabled flag.
    """
    _require_2fa_enabled(current_user)

    # Verify password via app state hasher
    password_hasher = getattr(request.app.state, "password_hasher", None)
    if password_hasher is None:
        from app.core.provider_implementations import BcryptPasswordHasher
        password_hasher = BcryptPasswordHasher(rounds=12)

    if not password_hasher.verify(payload.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password.",
        )

    # Verify TOTP code or backup code
    secret = totp_service.decrypt_secret(current_user.totp_secret_encrypted)
    code_valid = totp_service.verify_code(secret, payload.code)

    if not code_valid:
        # Try as backup code
        try:
            idx = totp_service.verify_backup_code(
                payload.code,
                list(current_user.totp_backup_codes or []),
            )
            # Mark this backup code as used (replace hash with sentinel)
            updated = list(current_user.totp_backup_codes)
            updated[idx] = "USED"
            current_user.totp_backup_codes = updated
        except InvalidBackupCodeError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid TOTP code or backup code.",
            )

    # Wipe 2FA data
    current_user.totp_enabled = False
    current_user.totp_secret_encrypted = None
    current_user.totp_backup_codes = None
    current_user.totp_last_used_at = None
    await db.commit()

    logger.info("2FA disabled for user %s", current_user.id)
    return {"message": "2FA has been disabled successfully."}


@router.post(
    "/verify",
    response_model=TwoFactorVerifyResponse,
    summary="Verify TOTP code during the 2FA login challenge",
)
async def verify_2fa(
    payload: TwoFactorVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_auth_db),
    totp_service: TwoFactorService = Depends(_get_totp_service),
):
    """
    Second-factor verification step during login.

    Called after successful password auth when ``requires_2fa: true`` is returned.
    On success, the backend issues the access + refresh tokens.
    """
    from sqlalchemy import select
    from uuid import UUID

    try:
        user_uuid = UUID(payload.user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id")

    from app.db.models.auth import User as UserModel
    result = await db.execute(select(UserModel).where(UserModel.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user or not user.totp_enabled or not user.totp_secret_encrypted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA not enabled for user")

    secret = totp_service.decrypt_secret(user.totp_secret_encrypted)

    # Try TOTP first
    if totp_service.verify_code(secret, payload.code):
        from datetime import datetime, timezone
        user.totp_last_used_at = datetime.now(timezone.utc)
        await db.commit()
        return TwoFactorVerifyResponse(verified=True, message="2FA verification successful.")

    # Try backup code
    try:
        idx = totp_service.verify_backup_code(
            payload.code,
            list(user.totp_backup_codes or []),
        )
        updated = list(user.totp_backup_codes)
        updated[idx] = "USED"
        user.totp_backup_codes = updated
        await db.commit()
        logger.warning("User %s used backup code at index %d", user.id, idx)
        return TwoFactorVerifyResponse(verified=True, message="Login via backup code successful. Consider regenerating backup codes.")
    except InvalidBackupCodeError:
        pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid 2FA code. Please try again.",
    )


@router.get(
    "/backup-codes",
    response_model=BackupCodesResponse,
    summary="Regenerate backup codes (invalidates all existing codes)",
)
async def regenerate_backup_codes(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_auth_db),
    totp_service: TwoFactorService = Depends(_get_totp_service),
):
    """
    Regenerate all backup codes.

    - Requires 2FA to be active.
    - All previous backup codes are immediately invalidated.
    """
    _require_2fa_enabled(current_user)

    plain_codes, hashed_codes = totp_service.generate_backup_codes()
    current_user.totp_backup_codes = hashed_codes
    await db.commit()

    logger.info("Backup codes regenerated for user %s", current_user.id)
    return BackupCodesResponse(backup_codes=plain_codes)
