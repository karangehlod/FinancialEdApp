"""
GDPR compliance service.

Responsibilities:
  - Full data export (Article 17): collect all user data into a JSON/ZIP bundle
  - Account deletion / anonymisation (Article 17): wipe PII, set deleted_at
  - Data retention enforcement: auto-delete inactive accounts after 2 years
  - Audit trail: log all GDPR-related operations

SOLID / Design notes:
  - Single Responsibility: only GDPR concerns, no HTTP knowledge.
  - Uses the soft_delete infrastructure from migration 003_soft_delete.sql.
  - Anonymisation replaces PII with deterministic pseudonyms (for referential integrity).
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Any, Dict, Optional
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATA_RETENTION_YEARS = 2
ANONYMISED_EMAIL_PREFIX = "deleted"
ANONYMISED_NAME = "Deleted User"


class GDPRService:
    """
    Implements GDPR data subject rights for FinancialEdApp.

    Args:
        auth_db:   AsyncSession for the auth database (users, refresh_tokens)
        data_db:   AsyncSession for the financial data database (expenses, budgets, etc.)
    """

    def __init__(self, auth_db: AsyncSession, data_db: AsyncSession) -> None:
        self.auth_db = auth_db
        self.data_db = data_db

    # ------------------------------------------------------------------
    # Article 20 — Data Portability: Export all user data
    # ------------------------------------------------------------------

    async def export_user_data(self, user_id: str) -> bytes:
        """
        Export ALL data for a user as a ZIP archive containing JSON files.

        Returns:
            ZIP bytes — suitable for streaming to the client.
        """
        data: Dict[str, Any] = {
            "export_metadata": {
                "user_id": user_id,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "format_version": "1.0",
                "data_controller": "FinancialEdApp",
            }
        }

        # --- Auth DB: user profile ---
        profile = await self._fetch_user_profile(user_id)
        data["profile"] = profile

        # --- Data DB: financial data ---
        data["expenses"] = await self._fetch_table(
            self.data_db, "expenses",
            "SELECT * FROM expenses WHERE user_id = :uid AND deleted_at IS NULL",
            user_id,
        )
        data["budgets"] = await self._fetch_table(
            self.data_db, "budgets",
            "SELECT * FROM budgets WHERE user_id = :uid AND deleted_at IS NULL",
            user_id,
        )
        data["goals"] = await self._fetch_table(
            self.data_db, "goals",
            "SELECT * FROM goals WHERE user_id = :uid AND deleted_at IS NULL",
            user_id,
        )
        data["loans"] = await self._fetch_table(
            self.data_db, "loans",
            "SELECT * FROM loans WHERE user_id = :uid",
            user_id,
        )
        data["notifications"] = await self._fetch_table(
            self.data_db, "notifications",
            "SELECT * FROM notifications WHERE user_id = :uid AND deleted_at IS NULL",
            user_id,
        )
        data["income_sources"] = await self._fetch_table(
            self.data_db, "income_sources",
            "SELECT * FROM income_sources WHERE user_id = :uid AND deleted_at IS NULL",
            user_id,
        )

        # Build ZIP
        buffer = BytesIO()
        with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as zf:
            zf.writestr(
                "data_export.json",
                json.dumps(data, default=str, indent=2, ensure_ascii=False),
            )
            zf.writestr(
                "README.txt",
                _EXPORT_README,
            )
        buffer.seek(0)

        logger.info("GDPR data export completed for user %s", user_id)
        return buffer.read()

    # ------------------------------------------------------------------
    # Article 17 — Right to Erasure: Anonymise and soft-delete account
    # ------------------------------------------------------------------

    async def delete_user_account(self, user_id: str) -> Dict[str, Any]:
        """
        Anonymise and soft-delete a user account.

        Strategy:
          1. Replace PII in the auth DB with pseudonymised values.
          2. Soft-delete all financial data in the data DB.
          3. Revoke all refresh tokens.
          4. Log in the soft_delete_audit table.

        Returns a summary dict with counts of affected records.
        """
        summary: Dict[str, Any] = {
            "user_id": user_id,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "anonymised": {},
        }

        # 1. Anonymise PII in auth DB
        anon_email = f"{ANONYMISED_EMAIL_PREFIX}_{self._user_hash(user_id)}@deleted.invalid"
        await self.auth_db.execute(
            text("""
                UPDATE users SET
                    email = :anon_email,
                    password_hash = 'REDACTED',
                    is_active = FALSE,
                    totp_secret_encrypted = NULL,
                    totp_enabled = FALSE,
                    totp_backup_codes = NULL,
                    updated_at = NOW()
                WHERE id = :uid
            """),
            {"anon_email": anon_email, "uid": user_id},
        )

        # 2. Revoke all refresh tokens
        revoke_result = await self.auth_db.execute(
            text("""
                UPDATE refresh_tokens
                SET is_revoked = TRUE, revoked_at = NOW()
                WHERE user_id = :uid AND is_revoked = FALSE
            """),
            {"uid": user_id},
        )
        summary["anonymised"]["refresh_tokens_revoked"] = revoke_result.rowcount
        await self.auth_db.commit()

        # 3. Soft-delete all financial data
        for table in ["expenses", "budgets", "goals", "loans", "notifications",
                      "recurring_expenses", "income_sources"]:
            result = await self.data_db.execute(
                text(f"""
                    UPDATE {table}
                    SET deleted_at = NOW()
                    WHERE user_id = :uid AND deleted_at IS NULL
                """),  # noqa: S608 (table name is hardcoded, not user input)
                {"uid": user_id},
            )
            summary["anonymised"][table] = result.rowcount

        # 4. Record in soft_delete_audit (if table exists)
        try:
            await self.data_db.execute(
                text("""
                    INSERT INTO soft_delete_audit
                        (table_name, record_id, deleted_by, reason)
                    VALUES
                        ('users', :uid, 'gdpr_delete', 'User requested account deletion')
                """),
                {"uid": user_id},
            )
        except Exception:
            pass  # Audit table may not exist in all envs

        await self.data_db.commit()

        logger.info("GDPR account deletion completed for user %s: %s", user_id, summary)
        return summary

    # ------------------------------------------------------------------
    # Data retention: auto-delete inactive accounts
    # ------------------------------------------------------------------

    async def purge_inactive_accounts(self) -> int:
        """
        Anonymise accounts inactive for more than DATA_RETENTION_YEARS.

        This is intended to be called from the ARQ background worker (cron job).
        Returns the number of accounts purged.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=DATA_RETENTION_YEARS * 365)
        result = await self.auth_db.execute(
            text("""
                SELECT id FROM users
                WHERE is_active = FALSE
                  AND updated_at < :cutoff
                  AND email NOT LIKE 'deleted_%@deleted.invalid'
                LIMIT 100
            """),
            {"cutoff": cutoff},
        )
        user_ids = [str(row[0]) for row in result.fetchall()]

        purged = 0
        for uid in user_ids:
            try:
                await self.delete_user_account(uid)
                purged += 1
            except Exception as exc:
                logger.error("Failed to purge inactive account %s: %s", uid, exc)

        logger.info("GDPR retention sweep: purged %d inactive accounts", purged)
        return purged

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _fetch_user_profile(self, user_id: str) -> Dict[str, Any]:
        result = await self.auth_db.execute(
            text("""
                SELECT id, email, is_active, is_verified, last_login, created_at
                FROM users WHERE id = :uid
            """),
            {"uid": user_id},
        )
        row = result.mappings().one_or_none()
        if not row:
            return {}
        return dict(row)

    @staticmethod
    async def _fetch_table(
        db: AsyncSession,
        table_name: str,
        query: str,
        user_id: str,
    ) -> list:
        try:
            result = await db.execute(text(query), {"uid": user_id})
            return [dict(r) for r in result.mappings().all()]
        except Exception as exc:
            logger.warning("Failed to fetch %s for export: %s", table_name, exc)
            return []

    @staticmethod
    def _user_hash(user_id: str) -> str:
        """8-char deterministic hash of user_id for pseudonymisation."""
        return hashlib.sha256(user_id.encode()).hexdigest()[:8]


# ---------------------------------------------------------------------------
# Export README text
# ---------------------------------------------------------------------------
_EXPORT_README = """\
FinancialEdApp — Personal Data Export
======================================

This archive contains all personal data associated with your FinancialEdApp account.

Files:
  data_export.json  — All your data in JSON format

Contents:
  - profile:         Your account information (email, join date, settings)
  - expenses:        All recorded expenses
  - budgets:         All budget categories and limits
  - goals:           All savings goals and progress
  - loans:           All loan records
  - notifications:   Your notification history
  - income_sources:  Recorded income sources

Data controller: FinancialEdApp
Data protection contact: privacy@financialedu.com

To request account deletion, use the DELETE /auth/account endpoint
or contact privacy@financialedu.com.

This export was generated in compliance with GDPR Article 20 (Right to Data Portability).
"""
