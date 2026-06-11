"""
OAuthAccountRepository — CRUD for linked social-login accounts.

Follows the repository pattern (consistent with RefreshTokenRepository):
  - All queries are parameterised via SQLAlchemy ORM.
  - Caller owns the session lifecycle.

P2-6: OAuth / Social Login
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import OAuthAccount

logger = logging.getLogger(__name__)


class OAuthAccountRepository:
    """
    Repository for OAuthAccount records.

    All methods accept an `AsyncSession` from the auth database.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_by_provider(
        self,
        provider: str,
        provider_user_id: str,
    ) -> Optional[OAuthAccount]:
        """Fetch a single active OAuth account by provider + provider UID."""
        result = await self.db.execute(
            select(OAuthAccount).where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id,
                OAuthAccount.is_active,
            )
        )
        return result.scalars().first()

    async def list_for_user(self, user_id: UUID) -> List[OAuthAccount]:
        """List all active linked OAuth providers for a user."""
        result = await self.db.execute(
            select(OAuthAccount).where(
                OAuthAccount.user_id == user_id,
                OAuthAccount.is_active,
            ).order_by(OAuthAccount.created_at)
        )
        return list(result.scalars().all())

    async def get_by_user_and_provider(
        self,
        user_id: UUID,
        provider: str,
    ) -> Optional[OAuthAccount]:
        """Get a specific provider link for a user."""
        result = await self.db.execute(
            select(OAuthAccount).where(
                OAuthAccount.user_id == user_id,
                OAuthAccount.provider == provider,
                OAuthAccount.is_active,
            )
        )
        return result.scalars().first()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create(
        self,
        user_id: UUID,
        provider: str,
        provider_user_id: str,
        provider_email: Optional[str] = None,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        access_token_encrypted: Optional[str] = None,
        refresh_token_encrypted: Optional[str] = None,
        token_expires_at: Optional[datetime] = None,
    ) -> OAuthAccount:
        """Persist a new OAuth account link."""
        account = OAuthAccount(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=provider_email,
            display_name=display_name,
            avatar_url=avatar_url,
            access_token_encrypted=access_token_encrypted,
            refresh_token_encrypted=refresh_token_encrypted,
            token_expires_at=token_expires_at,
            is_active=True,
        )
        self.db.add(account)
        await self.db.flush()  # populate id without committing
        logger.info(
            "OAuth account linked: user_id=%s provider=%s",
            user_id,
            provider,
        )
        return account

    async def update_tokens(
        self,
        account_id: UUID,
        access_token_encrypted: Optional[str],
        refresh_token_encrypted: Optional[str],
        token_expires_at: Optional[datetime],
    ) -> None:
        """Refresh stored tokens on an existing link (re-auth flow)."""
        await self.db.execute(
            update(OAuthAccount)
            .where(OAuthAccount.id == account_id)
            .values(
                access_token_encrypted=access_token_encrypted,
                refresh_token_encrypted=refresh_token_encrypted,
                token_expires_at=token_expires_at,
                updated_at=datetime.utcnow(),
            )
        )

    async def unlink(self, user_id: UUID, provider: str) -> bool:
        """
        Soft-unlink a provider from a user's account.

        Returns True if a record was found and deactivated, False otherwise.
        """
        result = await self.db.execute(
            update(OAuthAccount)
            .where(
                OAuthAccount.user_id == user_id,
                OAuthAccount.provider == provider,
                OAuthAccount.is_active,
            )
            .values(
                is_active=False,
                updated_at=datetime.utcnow(),
            )
        )
        rows_affected = result.rowcount
        if rows_affected:
            logger.info(
                "OAuth account unlinked: user_id=%s provider=%s",
                user_id,
                provider,
            )
        return bool(rows_affected)
