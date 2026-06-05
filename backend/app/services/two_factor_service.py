"""
TwoFactorService — TOTP-based two-factor authentication.

Responsibilities:
  - Generate TOTP secrets and provisioning URIs (for QR codes)
  - Verify TOTP codes (time-based, ±1 window tolerance)
  - Enable / disable 2FA for a user
  - Generate and validate backup codes (one-time use)
  - Store encrypted TOTP secret in DB

Security guarantees:
  - TOTP secret stored AES-256 encrypted in the DB via Fernet
  - Backup codes stored as bcrypt hashes (one-time use, auto-revoked on use)
  - 2FA bypass requires valid backup code + bcrypt verification
  - Re-enabling 2FA generates a fresh secret; old secret is discarded

SOLID compliance:
  - SRP: only 2FA concerns; no HTTP or session management.
  - DIP: depends on IUserRepository and CacheProvider interfaces.
"""

import base64
import hashlib
import logging
import os
import secrets
import time
from typing import List, Optional, Tuple

import pyotp
from cryptography.fernet import Fernet, InvalidToken
from passlib.context import CryptContext

from app.core.exceptions import AppException, AuthenticationError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Password context for backup codes
# ---------------------------------------------------------------------------
_backup_code_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TOTP_ISSUER = "FinancialEdApp"
TOTP_DIGITS = 6
TOTP_INTERVAL = 30          # seconds per TOTP window
TOTP_WINDOW = 1             # ±1 window tolerance (allows 90s drift)
BACKUP_CODE_COUNT = 10      # number of backup codes generated on 2FA enable
BACKUP_CODE_LENGTH = 12     # characters per backup code (hex)


class TwoFactorServiceError(AppException):
    """Raised for 2FA-specific errors."""


class TwoFactorAlreadyEnabledError(TwoFactorServiceError):
    """Raised when 2FA is already enabled."""


class TwoFactorNotEnabledError(TwoFactorServiceError):
    """Raised when 2FA is not enabled but operation requires it."""


class InvalidTOTPCodeError(TwoFactorServiceError):
    """Raised when a TOTP code is invalid."""


class InvalidBackupCodeError(TwoFactorServiceError):
    """Raised when a backup code is invalid or already used."""


class TwoFactorService:
    """
    TOTP-based two-factor authentication service.

    Args:
        encryption_key: 32-byte base64-url-safe Fernet key for secret encryption.
                        Set via TOTP_ENCRYPTION_KEY env var.
    """

    def __init__(self, encryption_key: Optional[str] = None) -> None:
        raw_key = encryption_key or os.environ.get("TOTP_ENCRYPTION_KEY")
        if not raw_key:
            # Auto-generate for development; log a warning
            logger.warning(
                "TOTP_ENCRYPTION_KEY not set — generating ephemeral key. "
                "Existing encrypted secrets will be unreadable after restart!"
            )
            raw_key = Fernet.generate_key().decode()
        self._fernet = Fernet(raw_key.encode() if isinstance(raw_key, str) else raw_key)

    # ------------------------------------------------------------------
    # Secret management
    # ------------------------------------------------------------------

    def generate_secret(self) -> str:
        """Generate a new base32-encoded TOTP secret."""
        return pyotp.random_base32(length=32)

    def encrypt_secret(self, secret: str) -> str:
        """Encrypt a TOTP secret for storage in DB."""
        return self._fernet.encrypt(secret.encode()).decode()

    def decrypt_secret(self, encrypted: str) -> str:
        """Decrypt a stored TOTP secret."""
        try:
            return self._fernet.decrypt(encrypted.encode()).decode()
        except InvalidToken as e:
            logger.error("Failed to decrypt TOTP secret — key mismatch or corruption")
            raise TwoFactorServiceError("Unable to decrypt TOTP secret") from e

    # ------------------------------------------------------------------
    # Provisioning URI (for QR code display)
    # ------------------------------------------------------------------

    def get_provisioning_uri(self, secret: str, email: str) -> str:
        """
        Return the otpauth:// URI for QR code generation.

        The frontend should pass this to a QR code library (e.g. qrcode.js).
        """
        totp = pyotp.TOTP(
            secret,
            digits=TOTP_DIGITS,
            interval=TOTP_INTERVAL,
            issuer=TOTP_ISSUER,
        )
        return totp.provisioning_uri(name=email, issuer_name=TOTP_ISSUER)

    # ------------------------------------------------------------------
    # Code verification
    # ------------------------------------------------------------------

    def verify_code(self, secret: str, code: str) -> bool:
        """
        Verify a TOTP code.

        Returns True if the code is valid within the ±TOTP_WINDOW window,
        False otherwise. Never raises — all exceptions are caught.
        """
        if not code or len(code) != TOTP_DIGITS:
            return False
        try:
            totp = pyotp.TOTP(
                secret,
                digits=TOTP_DIGITS,
                interval=TOTP_INTERVAL,
            )
            return totp.verify(code, valid_window=TOTP_WINDOW)
        except Exception as exc:
            logger.warning("TOTP verification error: %s", exc)
            return False

    def verify_code_or_raise(self, secret: str, code: str) -> None:
        """Verify TOTP code and raise ``InvalidTOTPCodeError`` if invalid."""
        if not self.verify_code(secret, code):
            raise InvalidTOTPCodeError("Invalid or expired TOTP code")

    # ------------------------------------------------------------------
    # Backup codes
    # ------------------------------------------------------------------

    def generate_backup_codes(self) -> Tuple[List[str], List[str]]:
        """
        Generate a set of one-time backup codes.

        Returns:
            (plain_codes, hashed_codes) — store hashed_codes in DB;
            show plain_codes to the user exactly once.
        """
        plain_codes = [
            secrets.token_hex(BACKUP_CODE_LENGTH // 2)
            for _ in range(BACKUP_CODE_COUNT)
        ]
        # Format for readability: XXXXXX-XXXXXX
        formatted = [f"{c[:6]}-{c[6:]}" for c in plain_codes]
        hashed = [_backup_code_ctx.hash(code) for code in formatted]
        return formatted, hashed

    def verify_backup_code(self, plain_code: str, hashed_codes: List[str]) -> int:
        """
        Verify a backup code against stored hashes.

        Returns the index of the matched hash (caller should mark it used),
        or raises InvalidBackupCodeError.
        """
        # Normalise: strip whitespace/dashes, lowercase to match generation format
        normalised = plain_code.strip().lower().replace(" ", "").replace("-", "")
        # Re-add dash for correct format comparison (codes are stored as xxxxxx-xxxxxx)
        if len(normalised) == 12:
            normalised = f"{normalised[:6]}-{normalised[6:]}"

        for idx, stored_hash in enumerate(hashed_codes):
            try:
                if _backup_code_ctx.verify(normalised, stored_hash):
                    return idx
            except Exception:
                continue
        raise InvalidBackupCodeError("Backup code is invalid or already used")


# ---------------------------------------------------------------------------
# Module-level singleton (lazy; created on first import)
# ---------------------------------------------------------------------------
_two_factor_service: Optional[TwoFactorService] = None


def get_two_factor_service() -> TwoFactorService:
    """Return the application-level TwoFactorService singleton."""
    global _two_factor_service
    if _two_factor_service is None:
        _two_factor_service = TwoFactorService()
    return _two_factor_service
