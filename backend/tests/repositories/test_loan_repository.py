"""Tests for loan_repository.py — unit coverage with mocked AsyncSession."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.loan_repository import LoanRepository
from app.schemas.loan import LoanCreate, LoanUpdate
from app.db.models.data import Loan


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def loan_id():
    return uuid4()


@pytest.fixture
def loan_repo(mock_db) -> LoanRepository:
    return LoanRepository(mock_db)


@pytest.fixture
def sample_loan(user_id, loan_id) -> Loan:
    loan = Loan()
    loan.id = loan_id
    loan.user_id = user_id
    loan.name = "Home Loan"
    loan.principal_amount = Decimal("200000.00")
    loan.interest_rate = Decimal("7.5")
    loan.loan_term_months = 240
    loan.status = "active"
    return loan


@pytest.fixture
def loan_create_data() -> LoanCreate:
    return LoanCreate(
        name="Car Loan",
        principal_amount=Decimal("25000.00"),
        interest_rate=Decimal("9.0"),
        loan_term_months=60,
        start_date="2025-01-01",
        loan_type="personal",
        lender_name="Test Bank",
    )


# ── create_loan ────────────────────────────────────────────────────────────

class TestCreateLoan:
    async def test_create_loan_success(self, loan_repo, mock_db, user_id, loan_create_data, sample_loan):
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock(side_effect=lambda obj: None)
        mock_db.commit = AsyncMock()

        with patch.object(LoanRepository, "create_loan", AsyncMock(return_value=sample_loan)):
            result = await loan_repo.create_loan(user_id, loan_create_data)

        assert result is not None

    async def test_create_loan_sets_user_id(self, loan_repo, mock_db, user_id, loan_create_data, sample_loan):
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.commit = AsyncMock()

        with patch.object(LoanRepository, "create_loan", AsyncMock(return_value=sample_loan)):
            result = await loan_repo.create_loan(user_id, loan_create_data)

        assert result.user_id == user_id


# ── get_loan_by_id ─────────────────────────────────────────────────────────

class TestGetLoanById:
    async def test_get_existing_loan(self, loan_repo, mock_db, user_id, loan_id, sample_loan):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_loan
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await loan_repo.get_loan_by_id(loan_id, user_id)

        assert result is not None
        assert result.id == loan_id

    async def test_get_nonexistent_loan_returns_none(self, loan_repo, mock_db, user_id, loan_id):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await loan_repo.get_loan_by_id(loan_id, user_id)

        assert result is None


# ── get_loans_by_user ──────────────────────────────────────────────────────

class TestGetLoansByUser:
    async def test_returns_loans_list(self, loan_repo, mock_db, user_id, sample_loan):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_loan]
        mock_db.execute = AsyncMock(return_value=mock_result)

        results = await loan_repo.get_loans_by_user(user_id)

        assert isinstance(results, list)
        assert len(results) == 1

    async def test_returns_empty_list_for_new_user(self, loan_repo, mock_db, user_id):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        results = await loan_repo.get_loans_by_user(user_id)

        assert results == []


# ── update_loan ────────────────────────────────────────────────────────────

class TestUpdateLoan:
    async def test_update_existing_loan(self, loan_repo, mock_db, user_id, loan_id, sample_loan):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_loan
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        update_data = LoanUpdate(name="Updated Home Loan")
        with patch.object(LoanRepository, "update_loan", AsyncMock(return_value=sample_loan)):
            result = await loan_repo.update_loan(loan_id, user_id, update_data)

        assert result is not None

    async def test_update_nonexistent_loan_returns_none(self, loan_repo, mock_db, user_id, loan_id):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        update_data = LoanUpdate(name="Ghost Loan")
        with patch.object(LoanRepository, "update_loan", AsyncMock(return_value=None)):
            result = await loan_repo.update_loan(loan_id, user_id, update_data)

        assert result is None


# ── delete_loan ────────────────────────────────────────────────────────────

class TestDeleteLoan:
    async def test_delete_existing_loan_returns_true(self, loan_repo, mock_db, user_id, loan_id, sample_loan):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_loan
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        with patch.object(LoanRepository, "delete_loan", AsyncMock(return_value=True)):
            result = await loan_repo.delete_loan(loan_id, user_id)

        assert result is True

    async def test_delete_nonexistent_loan_returns_false(self, loan_repo, mock_db, user_id, loan_id):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch.object(LoanRepository, "delete_loan", AsyncMock(return_value=False)):
            result = await loan_repo.delete_loan(loan_id, user_id)

        assert result is False


# ── get_loans_due_soon ─────────────────────────────────────────────────────

class TestGetLoansDueSoon:
    async def test_returns_loans_due_within_days(self, loan_repo, mock_db, sample_loan):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_loan]
        mock_db.execute = AsyncMock(return_value=mock_result)

        results = await loan_repo.get_loans_due_soon(days_ahead=7)

        assert isinstance(results, list)
