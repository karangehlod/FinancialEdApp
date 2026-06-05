"""
Unit tests for the financial profile auto-create logic.

Tests:
  • GET /auth/financial-profile auto-creates a profile when none exists.
  • GET /auth/financial-profile returns an existing profile when one exists.
  • FinancialProfileRepository.create_profile creates a default profile.
  • FinancialProfileRepository.get_profile_by_user_id returns None for missing.
  • FinancialProfileRepository.update_profile creates + updates when missing.
"""

import uuid
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import status
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Repository-level unit tests (mocked DB session)
# ---------------------------------------------------------------------------

class TestFinancialProfileRepository:
    """Test FinancialProfileRepository with mocked async session."""

    @pytest.mark.asyncio
    async def test_get_profile_by_user_id_returns_none_when_missing(self):
        from app.repositories.financial_profile_repository import FinancialProfileRepository

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        repo = FinancialProfileRepository(mock_db)
        profile = await repo.get_profile_by_user_id(uuid.uuid4())

        assert profile is None

    @pytest.mark.asyncio
    async def test_create_profile_default_values(self):
        """create_profile with no data should produce a profile with INR currency."""
        from app.repositories.financial_profile_repository import FinancialProfileRepository
        from app.db.models.data import UserFinancialProfile

        user_id = uuid.uuid4()
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        # Make refresh set the expected attributes on the profile
        async def fake_refresh(obj):
            obj.user_id = user_id
            obj.currency = obj.currency or "INR"

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        repo = FinancialProfileRepository(mock_db)
        profile = await repo.create_profile(user_id)

        assert profile is not None
        assert profile.user_id == user_id
        assert profile.currency == "INR"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_profile_creates_when_missing(self):
        """update_profile should create a new profile when one doesn't exist."""
        from app.repositories.financial_profile_repository import FinancialProfileRepository
        from app.schemas.financial_profile import FinancialProfileUpdate

        user_id = uuid.uuid4()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        # Capture what was added
        added_objects = []
        def track_add(obj):
            added_objects.append(obj)
        mock_db.add = MagicMock(side_effect=track_add)

        async def fake_refresh(obj):
            obj.user_id = user_id
        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        update_data = FinancialProfileUpdate(monthly_salary=5000, currency="USD")

        repo = FinancialProfileRepository(mock_db)
        profile = await repo.update_profile(user_id, update_data)

        assert profile is not None
        assert len(added_objects) == 1  # A new profile was created
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_profile_returns_false_when_missing(self):
        from app.repositories.financial_profile_repository import FinancialProfileRepository

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        repo = FinancialProfileRepository(mock_db)
        deleted = await repo.delete_profile(uuid.uuid4())

        assert deleted is False


# ---------------------------------------------------------------------------
# Endpoint-level tests (mocked dependencies)
# ---------------------------------------------------------------------------

class TestFinancialProfileEndpoint:
    """Test the GET /auth/financial-profile endpoint auto-create logic."""

    @pytest.mark.asyncio
    async def test_auto_create_on_first_get(self):
        """When no profile exists, the endpoint should auto-create one."""
        from app.api.v1.auth import get_financial_profile
        from app.db.models.data import UserFinancialProfile

        user_id = uuid.uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id

        fake_profile = MagicMock(spec=UserFinancialProfile)
        fake_profile.user_id = user_id
        fake_profile.monthly_salary = None
        fake_profile.currency = "INR"
        fake_profile.total_emi = None
        fake_profile.rent = None
        fake_profile.insurance = None
        fake_profile.subscriptions = None
        fake_profile.disposable_income = None

        mock_repo_instance = MagicMock()
        mock_repo_instance.get_profile_by_user_id = AsyncMock(return_value=None)
        mock_repo_instance.create_profile = AsyncMock(return_value=fake_profile)

        mock_data_db = AsyncMock()

        # Patch at the source module so the lazy import picks it up
        with patch(
            "app.repositories.financial_profile_repository.FinancialProfileRepository",
            return_value=mock_repo_instance,
        ):
            result = await get_financial_profile(
                current_user=mock_user,
                data_db=mock_data_db,
            )

        # Verify auto-create was called
        mock_repo_instance.get_profile_by_user_id.assert_awaited_once_with(user_id)
        mock_repo_instance.create_profile.assert_awaited_once_with(user_id)

    @pytest.mark.asyncio
    async def test_returns_existing_profile(self):
        """When a profile already exists, it should be returned without creating."""
        from app.api.v1.auth import get_financial_profile
        from app.db.models.data import UserFinancialProfile

        user_id = uuid.uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id

        existing_profile = MagicMock(spec=UserFinancialProfile)
        existing_profile.user_id = user_id
        existing_profile.monthly_salary = Decimal("5000.00")
        existing_profile.currency = "USD"

        mock_repo_instance = MagicMock()
        mock_repo_instance.get_profile_by_user_id = AsyncMock(return_value=existing_profile)
        mock_repo_instance.create_profile = AsyncMock()

        mock_data_db = AsyncMock()

        with patch(
            "app.repositories.financial_profile_repository.FinancialProfileRepository",
            return_value=mock_repo_instance,
        ):
            result = await get_financial_profile(
                current_user=mock_user,
                data_db=mock_data_db,
            )

        # Verify create was NOT called
        mock_repo_instance.create_profile.assert_not_awaited()
        assert result == existing_profile
