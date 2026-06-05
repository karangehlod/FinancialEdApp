"""
P1-2: Email verification & password reset endpoint tests.

Test coverage:
  - Email verification token creation and consumption
  - Password reset token flow (forgot-password → reset-password)
  - Rate limiting on email endpoints
  - Single-use token guarantee
  - Token expiry enforcement
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.verification_token_service import VerificationTokenService
from app.core.exceptions import AuthenticationError


@pytest.mark.asyncio
class TestEmailVerificationFlow:
    """Test email verification token lifecycle."""

    async def test_create_verification_token(self):
        """Creating a verification token should return a JWT."""
        mock_token_provider = MagicMock()  # sync token provider
        mock_token_provider.create_access_token.return_value = "jwt_token_123"
        mock_cache = AsyncMock()

        service = VerificationTokenService(
            token_provider=mock_token_provider,
            cache=mock_cache,
        )

        user_id = uuid4()
        token = await service.create_verification_token(user_id, "user@example.com")
        
        assert token == "jwt_token_123"
        mock_cache.set.assert_called_once()

    async def test_consume_verification_token_success(self):
        """Consuming a valid verification token should return user_id."""
        user_id = uuid4()
        mock_token_provider = MagicMock()  # sync token provider
        mock_token_provider.decode_token.return_value = {
            "sub": str(user_id),
            "purpose": "email_verify",
        }
        mock_cache = AsyncMock()
        mock_cache.get.return_value = str(user_id)
        mock_cache.delete.return_value = True

        service = VerificationTokenService(
            token_provider=mock_token_provider,
            cache=mock_cache,
        )

        result = await service.consume_verification_token("valid_token")
        assert result == user_id

    async def test_consume_verification_token_wrong_purpose(self):
        """Consuming a token with wrong purpose should raise error."""
        mock_token_provider = MagicMock()  # sync token provider
        mock_token_provider.decode_token.return_value = {
            "sub": str(uuid4()),
            "purpose": "pwd_reset",  # Wrong purpose
        }
        mock_cache = AsyncMock()

        service = VerificationTokenService(
            token_provider=mock_token_provider,
            cache=mock_cache,
        )

        with pytest.raises(AuthenticationError):
            await service.consume_verification_token("token_with_wrong_purpose")

    async def test_consume_verification_token_already_used(self):
        """Consuming a token twice should fail on second attempt."""
        mock_token_provider = MagicMock()  # sync token provider
        mock_token_provider.decode_token.return_value = {
            "sub": str(uuid4()),
            "purpose": "email_verify",
        }
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None  # Token already deleted

        service = VerificationTokenService(
            token_provider=mock_token_provider,
            cache=mock_cache,
        )

        with pytest.raises(AuthenticationError):
            await service.consume_verification_token("already_used_token")


@pytest.mark.asyncio
class TestPasswordResetFlow:
    """Test password reset token lifecycle."""

    async def test_create_password_reset_token(self):
        """Creating a password reset token should return a JWT."""
        mock_token_provider = MagicMock()  # sync token provider
        mock_token_provider.create_access_token.return_value = "reset_jwt_123"
        mock_cache = AsyncMock()

        service = VerificationTokenService(
            token_provider=mock_token_provider,
            cache=mock_cache,
        )

        user_id = uuid4()
        token = await service.create_password_reset_token(user_id, "user@example.com")
        
        assert token == "reset_jwt_123"
        mock_cache.set.assert_called_once()

    async def test_consume_password_reset_token_success(self):
        """Consuming a valid reset token should return user_id."""
        user_id = uuid4()
        mock_token_provider = MagicMock()  # sync token provider
        mock_token_provider.decode_token.return_value = {
            "sub": str(user_id),
            "purpose": "pwd_reset",
        }
        mock_cache = AsyncMock()
        mock_cache.get.return_value = str(user_id)
        mock_cache.delete.return_value = True

        service = VerificationTokenService(
            token_provider=mock_token_provider,
            cache=mock_cache,
        )

        result = await service.consume_password_reset_token("valid_reset_token")
        assert result == user_id


@pytest.mark.asyncio
class TestVerificationRateLimiting:
    """Test rate limiting on email verification endpoints."""

    async def test_rate_limit_exceeded_on_third_request(self):
        """Exceeding rate limit (3 per hour) should raise error."""
        mock_token_provider = MagicMock()  # sync token provider
        mock_token_provider.create_access_token.return_value = "jwt_token"
        mock_cache = AsyncMock()
        # Simulate: first call count=0, second=1, third=2 (allowed), fourth=3 (blocked)
        # Each create_verification_token calls cache.get once for rate check
        mock_cache.get.side_effect = ["0", "1", "2", "3"]
        mock_cache.set.return_value = True
        mock_cache.increment.return_value = None

        service = VerificationTokenService(
            token_provider=mock_token_provider,
            cache=mock_cache,
        )

        user_id = uuid4()
        email = "user@example.com"

        # First three requests succeed (counts 0, 1, 2 < 3)
        token1 = await service.create_verification_token(user_id, email)
        token2 = await service.create_verification_token(user_id, email)
        token3 = await service.create_verification_token(user_id, email)
        assert token1 and token2 and token3

        # Fourth request should fail (count=3 >= 3)
        with pytest.raises(AuthenticationError):
            await service.create_verification_token(user_id, email)


@pytest.mark.asyncio
class TestTokenExpiry:
    """Test token expiry enforcement."""

    async def test_expired_token_raises_error(self):
        """An expired token should be rejected."""
        mock_token_provider = MagicMock()  # sync token provider
        mock_token_provider.decode_token.side_effect = Exception("Token expired")
        mock_cache = AsyncMock()

        service = VerificationTokenService(
            token_provider=mock_token_provider,
            cache=mock_cache,
        )

        with pytest.raises(AuthenticationError):
            await service.consume_verification_token("expired_token")

    async def test_invalid_token_signature(self):
        """A token with invalid signature should be rejected."""
        mock_token_provider = MagicMock()  # sync token provider
        mock_token_provider.decode_token.side_effect = Exception("Invalid signature")
        mock_cache = AsyncMock()

        service = VerificationTokenService(
            token_provider=mock_token_provider,
            cache=mock_cache,
        )

        with pytest.raises(AuthenticationError):
            await service.consume_verification_token("invalid_token")


@pytest.mark.asyncio
class TestSingleUseTokens:
    """Test single-use token guarantee."""

    async def test_token_deleted_after_first_use(self):
        """Token should be deleted from cache after successful consumption."""
        user_id = uuid4()
        mock_token_provider = MagicMock()  # sync token provider
        mock_token_provider.decode_token.return_value = {
            "sub": str(user_id),
            "purpose": "email_verify",
        }
        mock_cache = AsyncMock()
        mock_cache.get.return_value = str(user_id)
        mock_cache.delete.return_value = True

        service = VerificationTokenService(
            token_provider=mock_token_provider,
            cache=mock_cache,
        )

        await service.consume_verification_token("token_to_delete")
        
        # Verify delete was called
        mock_cache.delete.assert_called_once()

    async def test_second_use_fails_after_deletion(self):
        """Using the same token twice should fail."""
        user_id = uuid4()
        mock_token_provider = MagicMock()  # sync token provider
        mock_token_provider.decode_token.return_value = {
            "sub": str(user_id),
            "purpose": "email_verify",
        }
        mock_cache = AsyncMock()
        
        # First use: token exists
        # Second use: token doesn't exist
        mock_cache.get.side_effect = [str(user_id), None]
        mock_cache.delete.return_value = True

        service = VerificationTokenService(
            token_provider=mock_token_provider,
            cache=mock_cache,
        )

        # First use succeeds
        result1 = await service.consume_verification_token("token")
        assert result1 == user_id

        # Second use fails
        with pytest.raises(AuthenticationError):
            await service.consume_verification_token("token")
