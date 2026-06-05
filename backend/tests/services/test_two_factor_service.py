"""Tests for two_factor_service.py — covers all methods and edge cases."""

import pytest
from unittest.mock import patch, MagicMock
from cryptography.fernet import Fernet

from app.services.two_factor_service import (
    TwoFactorService,
    TwoFactorServiceError,
    InvalidTOTPCodeError,
    InvalidBackupCodeError,
    get_two_factor_service,
    TOTP_DIGITS,
    BACKUP_CODE_COUNT,
)


@pytest.fixture
def encryption_key():
    return Fernet.generate_key().decode()


@pytest.fixture
def svc(encryption_key):
    return TwoFactorService(encryption_key=encryption_key)


class TestTwoFactorServiceInit:

    def test_init_with_key(self, encryption_key):
        svc = TwoFactorService(encryption_key=encryption_key)
        assert svc._fernet is not None

    def test_init_from_env(self, encryption_key):
        with patch.dict("os.environ", {"TOTP_ENCRYPTION_KEY": encryption_key}):
            svc = TwoFactorService()
            assert svc._fernet is not None

    def test_init_auto_generates_key(self):
        with patch.dict("os.environ", {}, clear=True):
            # Remove TOTP_ENCRYPTION_KEY if present
            import os
            os.environ.pop("TOTP_ENCRYPTION_KEY", None)
            svc = TwoFactorService()
            assert svc._fernet is not None


class TestSecretManagement:

    def test_generate_secret(self, svc):
        secret = svc.generate_secret()
        assert isinstance(secret, str)
        assert len(secret) > 0

    def test_encrypt_decrypt_roundtrip(self, svc):
        secret = svc.generate_secret()
        encrypted = svc.encrypt_secret(secret)
        decrypted = svc.decrypt_secret(encrypted)
        assert decrypted == secret

    def test_decrypt_with_wrong_key_raises(self, svc):
        encrypted = svc.encrypt_secret("my_secret")
        # Use a different key to decrypt
        other_svc = TwoFactorService(encryption_key=Fernet.generate_key().decode())
        with pytest.raises(TwoFactorServiceError, match="Unable to decrypt"):
            other_svc.decrypt_secret(encrypted)


class TestProvisioningUri:

    def test_get_provisioning_uri(self, svc):
        secret = svc.generate_secret()
        uri = svc.get_provisioning_uri(secret, "user@example.com")
        assert uri.startswith("otpauth://totp/")
        assert "FinancialEdApp" in uri
        assert "user%40example.com" in uri or "user@example.com" in uri


class TestCodeVerification:

    def test_verify_code_too_short(self, svc):
        assert svc.verify_code("secret", "123") is False

    def test_verify_code_empty(self, svc):
        assert svc.verify_code("secret", "") is False

    def test_verify_code_none(self, svc):
        assert svc.verify_code("secret", None) is False

    def test_verify_code_valid(self, svc):
        import pyotp
        secret = svc.generate_secret()
        totp = pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=30)
        code = totp.now()
        assert svc.verify_code(secret, code) is True

    def test_verify_code_invalid(self, svc):
        secret = svc.generate_secret()
        assert svc.verify_code(secret, "000000") is False

    def test_verify_code_exception_returns_false(self, svc):
        """Exception during verification returns False."""
        with patch("app.services.two_factor_service.pyotp.TOTP") as mock_totp:
            mock_totp.side_effect = Exception("boom")
            assert svc.verify_code("secret", "123456") is False

    def test_verify_code_or_raise_valid(self, svc):
        import pyotp
        secret = svc.generate_secret()
        code = pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=30).now()
        # Should not raise
        svc.verify_code_or_raise(secret, code)

    def test_verify_code_or_raise_invalid(self, svc):
        with pytest.raises(InvalidTOTPCodeError):
            svc.verify_code_or_raise(svc.generate_secret(), "000000")


class TestBackupCodes:

    def test_generate_backup_codes(self, svc):
        plain, hashed = svc.generate_backup_codes()
        assert len(plain) == BACKUP_CODE_COUNT
        assert len(hashed) == BACKUP_CODE_COUNT
        # Formatted as XXXXXX-XXXXXX
        assert "-" in plain[0]

    def test_verify_backup_code_success(self, svc):
        plain, hashed = svc.generate_backup_codes()
        # Verify the first code
        idx = svc.verify_backup_code(plain[0], hashed)
        assert idx == 0

    def test_verify_backup_code_invalid(self, svc):
        _, hashed = svc.generate_backup_codes()
        with pytest.raises(InvalidBackupCodeError):
            svc.verify_backup_code("INVALID-CODE00", hashed)

    def test_verify_backup_code_normalises_input(self, svc):
        plain, hashed = svc.generate_backup_codes()
        # Remove dash and use lowercase
        raw = plain[0].replace("-", "").lower()
        idx = svc.verify_backup_code(raw, hashed)
        assert idx == 0


class TestGetTwoFactorServiceSingleton:

    def test_singleton(self):
        """get_two_factor_service returns the same instance."""
        import app.services.two_factor_service as mod
        mod._two_factor_service = None
        s1 = get_two_factor_service()
        s2 = get_two_factor_service()
        assert s1 is s2
        mod._two_factor_service = None  # cleanup
