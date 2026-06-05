"""
Unit tests for LoanPaymentService.

Tests cover:
  - make_payment: principal/interest split, balance update, loan closure
  - make_payment: returns None for missing or inactive loans
  - get_loan_payments: user-ownership filtering
  - _payment_to_response: schema mapping
"""
from __future__ import annotations

import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.data import Loan, LoanPayment
from app.schemas.loan import LoanPaymentCreate, LoanStatus
from app.services.loan_payment_service import LoanPaymentService


# ---------------------------------------------------------------------------
# Fixtures
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
    repo.get_loan_by_id = AsyncMock()
    repo.create_payment = AsyncMock()
    repo.get_loan_payments = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def payment_service(mock_db, mock_repo):
    return LoanPaymentService(db=mock_db, loan_repository=mock_repo)


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def loan_id():
    return uuid4()


def _make_loan(user_id, loan_id, balance="50000", status="active", remaining=60) -> Loan:
    loan = MagicMock(spec=Loan)
    loan.id = loan_id
    loan.user_id = user_id
    loan.outstanding_balance = Decimal(balance)
    loan.status = status
    loan.interest_rate = Decimal("10.0")
    loan.remaining_months = remaining
    loan.next_due_date = date(2025, 1, 1)
    loan.updated_at = datetime.now(timezone.utc)
    return loan


def _make_payment(loan_id, user_id, amount="5000") -> LoanPayment:
    p = MagicMock(spec=LoanPayment)
    p.id = uuid4()
    p.loan_id = loan_id
    p.user_id = user_id
    p.amount_paid = Decimal(amount)
    p.principal_amount = Decimal("4600")
    p.interest_amount = Decimal("400")
    p.outstanding_balance = Decimal("45000")
    p.payment_date = date(2025, 1, 1)
    p.notes = None
    p.created_at = datetime.now(timezone.utc)
    return p


# ---------------------------------------------------------------------------
# validate_dependencies
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_dependencies_ok(payment_service):
    assert await payment_service.validate_dependencies() is True


@pytest.mark.asyncio
async def test_validate_dependencies_raises_without_repo(mock_db):
    svc = LoanPaymentService(db=mock_db, loan_repository=None)
    svc._repo = None
    with pytest.raises(Exception):
        await svc.validate_dependencies()


# ---------------------------------------------------------------------------
# make_payment — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_make_payment_splits_principal_and_interest(
    payment_service, mock_repo, mock_db, user_id, loan_id
):
    """Principal portion = amount - interest; balance reduced accordingly."""
    loan = _make_loan(user_id, loan_id, balance="12000", status="active")
    mock_repo.get_loan_by_id.return_value = loan

    payment_record = _make_payment(loan_id, user_id, amount="2000")
    mock_repo.create_payment.return_value = payment_record

    payment_data = LoanPaymentCreate(amount=Decimal("2000"), payment_date=date(2025, 1, 10))
    result = await payment_service.make_payment(user_id, loan_id, payment_data)

    assert result is not None
    # create_payment must have been called with computed portions
    call_kwargs = mock_repo.create_payment.call_args[1]
    assert call_kwargs["interest_amount"] == pytest.approx(
        float(Decimal("12000") * Decimal("10.0") / 12 / 100), rel=1e-4
    )
    assert call_kwargs["principal_amount"] > 0
    mock_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_make_payment_closes_loan_when_balance_reaches_zero(
    payment_service, mock_repo, mock_db, user_id, loan_id
):
    """Loan status should become CLOSED when new_balance == 0."""
    loan = _make_loan(user_id, loan_id, balance="100", status="active", remaining=1)
    mock_repo.get_loan_by_id.return_value = loan

    payment_record = _make_payment(loan_id, user_id, amount="200")
    mock_repo.create_payment.return_value = payment_record

    payment_data = LoanPaymentCreate(amount=Decimal("200"), payment_date=date(2025, 1, 10))
    await payment_service.make_payment(user_id, loan_id, payment_data)

    assert loan.status == LoanStatus.CLOSED.value
    assert loan.remaining_months == 0


@pytest.mark.asyncio
async def test_make_payment_advances_due_date_when_balance_remains(
    payment_service, mock_repo, mock_db, user_id, loan_id
):
    loan = _make_loan(user_id, loan_id, balance="50000", status="active", remaining=55)
    mock_repo.get_loan_by_id.return_value = loan

    payment_record = _make_payment(loan_id, user_id, amount="2000")
    mock_repo.create_payment.return_value = payment_record

    payment_data = LoanPaymentCreate(amount=Decimal("2000"), payment_date=date(2025, 3, 15))
    await payment_service.make_payment(user_id, loan_id, payment_data)

    assert loan.remaining_months == 54
    assert loan.next_due_date is not None


# ---------------------------------------------------------------------------
# make_payment — guard cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_make_payment_returns_none_when_loan_not_found(
    payment_service, mock_repo, user_id, loan_id
):
    mock_repo.get_loan_by_id.return_value = None
    payment_data = LoanPaymentCreate(amount=Decimal("1000"), payment_date=date(2025, 1, 1))
    result = await payment_service.make_payment(user_id, loan_id, payment_data)
    assert result is None


@pytest.mark.asyncio
async def test_make_payment_returns_none_for_inactive_loan(
    payment_service, mock_repo, user_id, loan_id
):
    loan = _make_loan(user_id, loan_id, status="closed")
    mock_repo.get_loan_by_id.return_value = loan

    payment_data = LoanPaymentCreate(amount=Decimal("1000"), payment_date=date(2025, 1, 1))
    result = await payment_service.make_payment(user_id, loan_id, payment_data)
    assert result is None


# ---------------------------------------------------------------------------
# get_loan_payments
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_loan_payments_filters_by_user(
    payment_service, mock_repo, user_id, loan_id
):
    """Payments belonging to a different user must be excluded."""
    other_user = uuid4()
    p1 = _make_payment(loan_id, user_id)
    p2 = _make_payment(loan_id, other_user)
    mock_repo.get_loan_payments.return_value = [p1, p2]

    results = await payment_service.get_loan_payments(user_id, loan_id)
    assert len(results) == 1
    assert results[0].user_id == user_id


@pytest.mark.asyncio
async def test_get_loan_payments_returns_empty_list(
    payment_service, mock_repo, user_id, loan_id
):
    mock_repo.get_loan_payments.return_value = []
    results = await payment_service.get_loan_payments(user_id, loan_id)
    assert results == []


# ---------------------------------------------------------------------------
# _payment_to_response
# ---------------------------------------------------------------------------

def test_payment_to_response_maps_fields(payment_service, user_id, loan_id):
    p = _make_payment(loan_id, user_id, amount="3000")
    response = payment_service._payment_to_response(p)

    assert response.loan_id == loan_id
    assert response.user_id == user_id
    assert response.amount == Decimal("3000")
    assert response.principal_portion == p.principal_amount
    assert response.interest_portion == p.interest_amount
