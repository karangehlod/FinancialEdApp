"""Tests for gdpr_service.py — export, delete, purge, and helpers."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from zipfile import ZipFile
from io import BytesIO

from app.services.gdpr_service import GDPRService


@pytest.fixture
def mock_auth_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def mock_data_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def gdpr_service(mock_auth_db, mock_data_db):
    return GDPRService(auth_db=mock_auth_db, data_db=mock_data_db)


class TestExportUserData:

    @pytest.mark.asyncio
    async def test_export_produces_zip(self, gdpr_service, mock_auth_db, mock_data_db):
        """export_user_data returns a valid ZIP with JSON data."""
        user_id = str(uuid4())

        # Mock user profile query
        profile_result = MagicMock()
        profile_mapping = MagicMock()
        profile_mapping.one_or_none.return_value = {
            "id": user_id, "email": "user@test.com", "is_active": True,
            "is_verified": True, "last_login": None, "created_at": "2024-01-01",
        }
        profile_result.mappings.return_value = profile_mapping

        # Mock all _fetch_table queries to return empty lists
        table_result = MagicMock()
        table_mappings = MagicMock()
        table_mappings.all.return_value = []
        table_result.mappings.return_value = table_mappings

        # First call = profile, rest = table queries
        mock_auth_db.execute.return_value = profile_result
        mock_data_db.execute.return_value = table_result

        data = await gdpr_service.export_user_data(user_id)

        assert isinstance(data, bytes)
        # Verify it's a valid ZIP
        buf = BytesIO(data)
        with ZipFile(buf) as zf:
            names = zf.namelist()
            assert "data_export.json" in names
            assert "README.txt" in names
            export_json = json.loads(zf.read("data_export.json"))
            assert export_json["export_metadata"]["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_export_no_profile(self, gdpr_service, mock_auth_db, mock_data_db):
        """If user doesn't exist, profile is empty dict."""
        profile_result = MagicMock()
        profile_mapping = MagicMock()
        profile_mapping.one_or_none.return_value = None
        profile_result.mappings.return_value = profile_mapping

        table_result = MagicMock()
        table_mappings = MagicMock()
        table_mappings.all.return_value = []
        table_result.mappings.return_value = table_mappings

        mock_auth_db.execute.return_value = profile_result
        mock_data_db.execute.return_value = table_result

        data = await gdpr_service.export_user_data(str(uuid4()))
        assert isinstance(data, bytes)


class TestDeleteUserAccount:

    @pytest.mark.asyncio
    async def test_delete_account_returns_summary(self, gdpr_service, mock_auth_db, mock_data_db):
        """delete_user_account anonymises and soft-deletes."""
        user_id = str(uuid4())

        # Auth DB execute: anonymise + revoke tokens
        anon_result = MagicMock()
        anon_result.rowcount = 1
        revoke_result = MagicMock()
        revoke_result.rowcount = 3
        mock_auth_db.execute = AsyncMock(side_effect=[anon_result, revoke_result])

        # Data DB: soft-delete for each table + audit
        data_result = MagicMock()
        data_result.rowcount = 5
        mock_data_db.execute = AsyncMock(return_value=data_result)

        summary = await gdpr_service.delete_user_account(user_id)

        assert summary["user_id"] == user_id
        assert "anonymised" in summary
        assert summary["anonymised"]["refresh_tokens_revoked"] == 3
        mock_auth_db.commit.assert_called_once()
        mock_data_db.commit.assert_called_once()


class TestPurgeInactiveAccounts:

    @pytest.mark.asyncio
    async def test_purge_no_inactive(self, gdpr_service, mock_auth_db):
        """No accounts to purge returns 0."""
        result = MagicMock()
        result.fetchall.return_value = []
        mock_auth_db.execute.return_value = result

        count = await gdpr_service.purge_inactive_accounts()
        assert count == 0

    @pytest.mark.asyncio
    async def test_purge_with_inactive(self, gdpr_service, mock_auth_db, mock_data_db):
        """Purge processes inactive accounts."""
        uid = str(uuid4())
        select_result = MagicMock()
        select_result.fetchall.return_value = [(uid,)]

        # Subsequent calls for delete_user_account
        anon_result = MagicMock()
        anon_result.rowcount = 1
        revoke_result = MagicMock()
        revoke_result.rowcount = 0
        mock_auth_db.execute = AsyncMock(side_effect=[select_result, anon_result, revoke_result])

        data_result = MagicMock()
        data_result.rowcount = 0
        mock_data_db.execute = AsyncMock(return_value=data_result)

        count = await gdpr_service.purge_inactive_accounts()
        assert count == 1

    @pytest.mark.asyncio
    async def test_purge_handles_error(self, gdpr_service, mock_auth_db):
        """Purge continues even if one account fails."""
        uid = str(uuid4())
        select_result = MagicMock()
        select_result.fetchall.return_value = [(uid,)]

        mock_auth_db.execute = AsyncMock(side_effect=[
            select_result,  # SELECT inactive
            Exception("DB error"),  # first operation of delete_user_account fails
        ])

        count = await gdpr_service.purge_inactive_accounts()
        assert count == 0  # failed to purge


class TestHelpers:

    def test_user_hash(self):
        h = GDPRService._user_hash("test-user-id")
        assert isinstance(h, str) and len(h) == 8

    @pytest.mark.asyncio
    async def test_fetch_table_exception_returns_empty(self):
        db = AsyncMock()
        db.execute.side_effect = Exception("table doesn't exist")
        result = await GDPRService._fetch_table(db, "expenses", "SELECT 1", "uid")
        assert result == []
