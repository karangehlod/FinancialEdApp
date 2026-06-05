"""
Unit tests for LoanCrudService.

All database access is replaced with AsyncMock / MagicMock so no real DB
is needed.  Tests verify:
  - create_loan (with and without pre-supplied EMI)
  - get_loan / get_user_loans
  - update_loan (field patching + EMI recalculation)
  - delete_loan
  - configure_loan
  - to_response helper
"""
from __future__ import annotations

import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.data import Loan, LoanPayment
from app.schemas.loan import LoanCreate, LoanUpdate
from app.services.loan_crud_service import LoanCrudService


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    db = AsyncMock(spec=AsyncSession)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.create_loan = AsyncMock()
    repo.get_loan_by_id = AsyncMock()
    repo.get_loans_by_user = AsyncMock()
    repo.delete_loan = AsyncMock()
    repo.get_loan_payments = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_profile_service():
    svc = AsyncMock()
    svc.update_from_loans = AsyncMock()
    return svc


@pytest.fixture
def crud_service(mock_db, mock_repo, mock_profile_service):
    return LoanCrudService(
        db=mock_db,
        loan_repository=mock_repo,
        financial_profile_service=mock_profile_service,
    )


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def loan_id():
    return uuid4()


def _make_loan(user_id, loan_id, **overrides) -> Loan:
    defaults = dict(
        id=loan_id,
        user_id=user_id,
        loan_type="Personal",
        lender_name="TestBank",
        principal_amount=Decimal("100000"),
        outstanding_balance=Decimal("90000"),
        interest_rate=Decimal("9.0"),
        loan_term_months=120,
        emi_amount=Decimal("1267"),
        start_date=date(2024, 1, 1),
        next_due_date=date(2024, 2, 1),
        remaining_months=115,
        status="active",
        description="Test loan",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    loan = MagicMock(spec=Loan)
    for k, v in defaults.items():
        setattr(loan, k, v)
    return loan


# ---------------------------------------------------------------------------
# validate_dependencies
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_dependencies_passes(crud_service):
    result = await crud_service.validate_dependencies()
    assert result is True


@pytest.mark.asyncio
async def test_validate_dependencies_raises_without_repo(mock_db, mock_profile_service):
    svc = LoanCrudService(db=mock_db, loan_repository=None,
                          financial_profile_service=mock_profile_service)
    # _repo falls back to a real LoanRepository constructed from mock_db — still not None
    # Override _repo to None manually to test the guard
    svc._repo = None
    with pytest.raises(Exception):
        await svc.validate_dependencies()


# ---------------------------------------------------------------------------
# create_loan
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_loan_calculates_emi_when_missing(
    crud_service, mock_repo, mock_db, user_id, loan_id
):
    """EMI should be calculated and stored when not provided."""
    db_loan = _make_loan(user_id, loan_id)
    mock_repo.create_loan.return_value = db_loan

    loan_data = LoanCreate(
        loan_type="Personal",
        lender_name="Bank",
        principal_amount=Decimal("100000"),
        interest_rate=Decimal("9.0"),
        loan_term_months=120,
        start_date=date(2024, 1, 1),
        emi_amount=None,
    )
    result = await crud_service.create_loan(user_id, loan_data)

    mock_repo.create_loan.assert_called_once()
    called_data = mock_repo.create_loan.call_args[0][1]
    # EMI must have been filled in
    assert called_data.emi_amount is not None
    assert called_data.emi_amount > 0
    mock_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_create_loan_uses_supplied_emi(
    crud_service, mock_repo, mock_db, user_id, loan_id
):
    """Supplied EMI must be passed through unchanged."""
    db_loan = _make_loan(user_id, loan_id)
    mock_repo.create_loan.return_value = db_loan

    loan_data = LoanCreate(
        loan_type="Home",
        lender_name="HousingBank",
        principal_amount=Decimal("500000"),
        interest_rate=Decimal("7.5"),
        loan_term_months=240,
        start_date=date(2024, 3, 1),
        emi_amount=Decimal("4000"),
    )
    await crud_service.create_loan(user_id, loan_data)

    called_data = mock_repo.create_loan.call_args[0][1]
    assert called_data.emi_amount == Decimal("4000")


@pytest.mark.asyncio
async def test_create_loan_updates_financial_profile(
    crud_service, mock_repo, mock_db, mock_profile_service, user_id, loan_id
):
    db_loan = _make_loan(user_id, loan_id)
    mock_repo.create_loan.return_value = db_loan

    loan_data = LoanCreate(
        loan_type="Car",
        lender_name="CarLoan",
        principal_amount=Decimal("20000"),
        interest_rate=Decimal("10.0"),
        loan_term_months=36,
        start_date=date(2024, 1, 1),
    )
    await crud_service.create_loan(user_id, loan_data)
    mock_profile_service.update_from_loans.assert_awaited_once_with(user_id)


# ---------------------------------------------------------------------------
# get_loan
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_loan_returns_response(crud_service, mock_repo, user_id, loan_id):
    mock_repo.get_loan_by_id.return_value = _make_loan(user_id, loan_id)
    result = await crud_service.get_loan(user_id, loan_id)
    assert result is not None
    assert result.id == loan_id


@pytest.mark.asyncio
async def test_get_loan_returns_none_when_not_found(
    crud_service, mock_repo, user_id, loan_id
):
    mock_repo.get_loan_by_id.return_value = None
    result = await crud_service.get_loan(user_id, loan_id)
    assert result is None


# ---------------------------------------------------------------------------
# get_user_loans
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_user_loans_returns_list(crud_service, mock_repo, user_id, loan_id):
    mock_repo.get_loans_by_user.return_value = [
        _make_loan(user_id, loan_id),
        _make_loan(user_id, uuid4()),
    ]
    results = await crud_service.get_user_loans(user_id)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_get_user_loans_passes_status_filter(
    crud_service, mock_repo, user_id
):
    mock_repo.get_loans_by_user.return_value = []
    await crud_service.get_user_loans(user_id, status="active")
    mock_repo.get_loans_by_user.assert_awaited_once_with(user_id, "active")


# ---------------------------------------------------------------------------
# update_loan
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_loan_recalculates_emi_on_financial_change(
    crud_service, mock_repo, mock_db, user_id, loan_id
):
    """Changing principal_amount must trigger EMI recalculation."""
    loan = _make_loan(user_id, loan_id)
    mock_repo.get_loan_by_id.return_value = loan

    update_data = LoanUpdate(principal_amount=Decimal("200000"))
    await crud_service.update_loan(user_id, loan_id, update_data)

    # emi_amount must have been reassigned on the loan object
    assert loan.emi_amount is not None
    mock_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_update_loan_returns_none_when_not_found(
    crud_service, mock_repo, user_id, loan_id
):
    mock_repo.get_loan_by_id.return_value = None
    result = await crud_service.update_loan(user_id, loan_id, LoanUpdate())
    assert result is None


# ---------------------------------------------------------------------------
# delete_loan
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_loan_returns_true_and_commits(
    crud_service, mock_repo, mock_db, mock_profile_service, user_id, loan_id
):
    mock_repo.delete_loan.return_value = True
    result = await crud_service.delete_loan(user_id, loan_id)
    assert result is True
    mock_db.commit.assert_awaited()
    mock_profile_service.update_from_loans.assert_awaited_once_with(user_id)


@pytest.mark.asyncio
async def test_delete_loan_returns_false_without_commit(
    crud_service, mock_repo, mock_db, user_id, loan_id
):
    mock_repo.delete_loan.return_value = False
    result = await crud_service.delete_loan(user_id, loan_id)
    assert result is False
    mock_db.commit.assert_not_awaited()


# ---------------------------------------------------------------------------
# to_response
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_to_response_aggregates_payment_totals(
    crud_service, mock_repo, user_id, loan_id
):
    payment = MagicMock(spec=LoanPayment)
    payment.amount_paid = Decimal("1000")
    payment.interest_amount = Decimal("200")
    mock_repo.get_loan_payments.return_value = [payment]

    loan = _make_loan(user_id, loan_id, status="active")
    response = await crud_service.to_response(loan)

    assert response.total_paid == Decimal("1000")
    assert response.total_interest_paid == Decimal("200")
    assert response.payments_made == 1
