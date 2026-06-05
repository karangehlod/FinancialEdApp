"""
RefreshTokenRepository — persistence layer for refresh token lifecycle.

Design:
  - Only SHA-256 hashes of the raw JWT are stored (never the token itself).
  - Token rotation: old token is marked revoked, new token is inserted.
  - ``replaced_by`` links the rotation chain for audit purposes.
  - Expired and revoked tokens are purged via ``purge_expired()``.

Usage:
    repo = RefreshTokenRepository(auth_db)
    record = await repo.create(user_id, token_hash, expires_at, device_info)
    record = await repo.get_valid(token_hash)
    await repo.revoke(token_hash, replaced_by_id)
    await repo.revoke_all_for_user(user_id)
    await repo.purge_expired()
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import RefreshToken

logger = logging.getLogger(__name__)


class RefreshTokenRepository:
    """
    CRUD repository for ``RefreshToken`` records.

    All methods are async and accept / return ``RefreshToken`` ORM objects.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def create(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        device_info: Optional[str] = None,
        *,
        auto_commit: bool = True,
    ) -> RefreshToken:
        """
        Persist a new refresh token record.

        Args:
            user_id:      Owner of the token.
            token_hash:   SHA-256 hex digest of the raw JWT string.
            expires_at:   UTC expiry datetime.
            device_info:  Optional serialised device / User-Agent info.
            auto_commit:  If True (default), flush+commit immediately.
                          Set to False when the caller manages the transaction.

        Returns:
            The newly created ``RefreshToken`` ORM record.
        """
        # Use token_hash column (HMAC-SHA256 fingerprint of the raw token)
        record = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_revoked=False,
            device_info=device_info,
        )
        self._db.add(record)
        if auto_commit:
            await self._db.commit()
            await self._db.refresh(record)
        else:
            # Flush to generate the id without committing the transaction
            await self._db.flush()
        logger.debug("Refresh token stored for user %s", user_id)
        return record

    async def revoke(
        self,
        token_hash: str,
        replaced_by: Optional[UUID] = None,
        *,
        auto_commit: bool = True,
    ) -> bool:
        """
        Mark a single token as revoked.

        Args:
            token_hash:   Hash of the token to revoke.
            replaced_by:  ID of the new token that replaced this one (rotation).
            auto_commit:  If True (default), commit immediately.
                          Set to False when the caller manages the transaction.

        Returns:
            True if a record was updated, False if not found.
        """
        result = await self._db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .values(
                is_revoked=True,
                revoked_at=datetime.now(timezone.utc).replace(tzinfo=None),
                replaced_by=replaced_by,
            )
            .returning(RefreshToken.id)
        )
        if auto_commit:
            await self._db.commit()
        revoked = result.fetchone() is not None
        if revoked:
            logger.debug("Refresh token revoked (replaced_by=%s)", replaced_by)
        else:
            logger.warning("Attempted to revoke non-existent token hash")
        return revoked

    async def rotate(
        self,
        old_token_hash: str,
        new_user_id: UUID,
        new_token_hash: str,
        new_expires_at: datetime,
        device_info: Optional[str] = None,
    ) -> RefreshToken:
        """
        Atomically revoke the old refresh token and persist a new one.

        This avoids the race condition / unique constraint violation that can
        occur when create() and revoke() each commit independently.

        Args:
            old_token_hash:  Hash of the consumed token to revoke.
            new_user_id:     Owner of the new token.
            new_token_hash:  SHA-256 hex digest of the new JWT.
            new_expires_at:  UTC expiry for the new token.
            device_info:     Optional device/User-Agent info.

        Returns:
            The newly created ``RefreshToken`` ORM record.
        """
        new_record = await self.create(
            user_id=new_user_id,
            token_hash=new_token_hash,
            expires_at=new_expires_at,
            device_info=device_info,
            auto_commit=False,
        )
        await self.revoke(
            token_hash=old_token_hash,
            replaced_by=new_record.id,
            auto_commit=False,
        )
        await self._db.commit()
        await self._db.refresh(new_record)
        logger.info(
            "Refresh token rotated for user %s (old revoked, new id=%s)",
            new_user_id,
            new_record.id,
        )
        return new_record

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def get_valid(self, token_hash: str) -> Optional[RefreshToken]:
        """
        Retrieve a refresh token record that is valid (not revoked, not expired).

        Args:
            token_hash: SHA-256 hex digest to look up.

        Returns:
            ``RefreshToken`` if found and valid, ``None`` otherwise.
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        result = await self._db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.token_hash == token_hash,
                    RefreshToken.is_revoked == False,  # noqa: E712
                    RefreshToken.expires_at > now,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: UUID) -> list[RefreshToken]:
        """Return all active (non-revoked) tokens for a user."""
        result = await self._db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.is_revoked == False,  # noqa: E712
                )
            )
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    async def purge_expired(self) -> int:
        """
        Hard-delete all expired or long-revoked tokens.

        Intended to be called by a nightly background task.

        Returns:
            Number of records deleted.
        """
        from sqlalchemy import delete

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        result = await self._db.execute(
            delete(RefreshToken).where(RefreshToken.expires_at <= now)
        )
        await self._db.commit()
        deleted = result.rowcount
        logger.info("Purged %d expired refresh tokens", deleted)
        return deleted

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        """
        Revoke all currently active (non-revoked) refresh tokens for a user.

        Performs a single UPDATE and returns the number of rows affected.
        This is used for security actions like password change or detected token
        reuse where all sessions must be invalidated immediately.
        """
        result = await self._db.execute(
            update(RefreshToken)
            .where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.is_revoked == False,  # noqa: E712
                )
            )
            .values(
                is_revoked=True,
                revoked_at=datetime.now(timezone.utc).replace(tzinfo=None),
                replaced_by=None,
            )
            .returning(RefreshToken.id)
        )
        await self._db.commit()
        count = result.rowcount or 0
        logger.info("Revoked %d refresh tokens for user %s", count, user_id)
        return count
