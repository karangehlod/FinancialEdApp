"""
Unit tests for LoanAnalyticsService.

Tests cover:
  - generate_repayment_schedule: correct amortisation math, empty on missing loan
  - get_loan_analytics: aggregate totals
  - get_monthly_loan_summary: monthly rollup
  - get_loan_summary: per-loan and portfolio variants
  - analyze_prepayment: delegates to PrepaymentCalculator
  - calculate_emi_impact: delegates to PrepaymentCalculator
"""
from __future__ import annotations

import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch, AsyncMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.data import Loan, LoanPayment
from app.schemas.loan import LoanStatus
from app.services.loan_analytics_service import LoanAnalyticsService
from app.services.loan_crud_service import LoanCrudService


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    db = AsyncMock(spec=AsyncSession)
    # Default: return a mock result set for aggregate queries
    mock_row = MagicMock()
    mock_row.__getitem__ = lambda self, idx: [2, Decimal("200000"), Decimal("180000"), Decimal("2500")][idx]
    mock_result = MagicMock()
    mock_result.fetchone.return_value = mock_row
    db.execute = AsyncMock(return_value=mock_result)
    return db


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_loan_by_id = AsyncMock(return_value=None)
    repo.get_loans_by_user = AsyncMock(return_value=[])
    repo.get_loan_payments = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_crud():
    crud = AsyncMock(spec=LoanCrudService)
    crud.to_response = AsyncMock()
    crud.get_user_loans = AsyncMock(return_value=[])
    return crud


@pytest.fixture
def analytics_service(mock_db, mock_repo, mock_crud):
    return LoanAnalyticsService(
        db=mock_db,
        loan_repository=mock_repo,
        crud_service=mock_crud,
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
        principal_amount=Decimal("120000"),
        outstanding_balance=Decimal("100000"),
        interest_rate=Decimal("10.0"),
        loan_term_months=12,
        emi_amount=Decimal("10548"),
        start_date=date(2025, 1, 1),
        next_due_date=date(2025, 2, 1),
        remaining_months=11,
        status="active",
        loan_type="Personal",
        lender_name="TestBank",
        description="Test",
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
async def test_validate_dependencies_ok(analytics_service):
    assert await analytics_service.validate_dependencies() is True


# ---------------------------------------------------------------------------
# generate_repayment_schedule
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_repayment_schedule_returns_empty_for_missing_loan(
    analytics_service, mock_repo, user_id, loan_id
):
    mock_repo.get_loan_by_id.return_value = None
    result = await analytics_service.generate_repayment_schedule(user_id, loan_id)
    assert result == []


@pytest.mark.asyncio
async def test_generate_repayment_schedule_correct_length(
    analytics_service, mock_repo, user_id, loan_id
):
    """Schedule should have at most loan_term_months entries."""
    loan = _make_loan(user_id, loan_id, loan_term_months=12)
    mock_repo.get_loan_by_id.return_value = loan
    mock_repo.get_loan_payments.return_value = []

    schedule = await analytics_service.generate_repayment_schedule(user_id, loan_id)

    assert len(schedule) <= 12
    assert len(schedule) > 0


@pytest.mark.asyncio
async def test_generate_repayment_schedule_balance_converges_to_zero(
    analytics_service, mock_repo, user_id, loan_id
):
    """Remaining balance on the last entry must be zero (or very close)."""
    loan = _make_loan(user_id, loan_id, loan_term_months=12, principal_amount=Decimal("10000"))
    mock_repo.get_loan_by_id.return_value = loan
    mock_repo.get_loan_payments.return_value = []

    schedule = await analytics_service.generate_repayment_schedule(user_id, loan_id)

    last_balance = schedule[-1].remaining_balance
    assert last_balance >= Decimal("0")
    assert last_balance < Decimal("10")   # within rounding of zero


@pytest.mark.asyncio
async def test_generate_repayment_schedule_marks_paid_from_recorded_dates(
    analytics_service, mock_repo, user_id, loan_id
):
    """Entries whose payment_date is in recorded_dates should be is_paid=True."""
    loan = _make_loan(user_id, loan_id, loan_term_months=3, principal_amount=Decimal("3000"))
    mock_repo.get_loan_by_id.return_value = loan

    paid_payment = MagicMock(spec=LoanPayment)
    paid_payment.payment_date = date(2025, 2, 1)
    mock_repo.get_loan_payments.return_value = [paid_payment]

    schedule = await analytics_service.generate_repayment_schedule(user_id, loan_id)

    paid_entries = [s for s in schedule if s.is_paid]
    assert len(paid_entries) >= 1


# ---------------------------------------------------------------------------
# get_loan_analytics
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_loan_analytics_returns_analytics_object(
    analytics_service, user_id
):
    result = await analytics_service.get_loan_analytics(user_id)
    # Should be a LoanAnalytics pydantic model
    assert hasattr(result, "total_loans")
    assert hasattr(result, "total_outstanding_balance")


@pytest.mark.asyncio
async def test_get_loan_analytics_falls_back_to_repo_on_db_error(
    mock_db, mock_repo, mock_crud, user_id, loan_id
):
    """When the aggregate SQL fails, analytics must fall back to repo.get_loans_by_user."""
    mock_db.execute.side_effect = Exception("DB offline")
    loan = _make_loan(user_id, loan_id, status="active")
    mock_repo.get_loans_by_user.return_value = [loan]

    svc = LoanAnalyticsService(db=mock_db, loan_repository=mock_repo, crud_service=mock_crud)
    result = await svc.get_loan_analytics(user_id)

    mock_repo.get_loans_by_user.assert_awaited()
    assert result.total_loans == 1


# ---------------------------------------------------------------------------
# get_monthly_loan_summary
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_monthly_loan_summary_returns_correct_month_string(
    analytics_service, user_id
):
    # db.execute returns empty scalars list for LoanPayment query
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    analytics_service._db.execute = AsyncMock(return_value=mock_result)

    result = await analytics_service.get_monthly_loan_summary(user_id, 2025, 4)
    assert result.month == "2025-04"


# ---------------------------------------------------------------------------
# get_loan_summary
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_loan_summary_returns_none_for_missing_loan(
    analytics_service, mock_repo, user_id, loan_id
):
    mock_repo.get_loan_by_id.return_value = None
    result = await analytics_service.get_loan_summary(user_id, loan_id)
    assert result is None


@pytest.mark.asyncio
async def test_get_loan_summary_portfolio_returns_object(
    analytics_service, mock_repo, user_id
):
    """get_loan_summary(loan_id=None) must return a portfolio summary."""
    mock_repo.get_loans_by_user.return_value = []
    result = await analytics_service.get_loan_summary(user_id, loan_id=None)
    assert hasattr(result, "total_loans")
    assert result.total_loans == 0


# ---------------------------------------------------------------------------
# analyze_prepayment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyze_prepayment_raises_for_missing_loan(
    analytics_service, mock_repo, user_id, loan_id
):
    mock_repo.get_loan_by_id.return_value = None
    with pytest.raises(ValueError, match="Loan not found"):
        await analytics_service.analyze_prepayment(user_id, loan_id, Decimal("5000"))


@pytest.mark.asyncio
async def test_analyze_prepayment_returns_analysis(
    analytics_service, mock_repo, user_id, loan_id
):
    loan = _make_loan(user_id, loan_id)
    mock_repo.get_loan_by_id.return_value = loan

    with patch(
        "app.services.loan_analytics_service.PrepaymentCalculator.calculate_prepayment_impact",
        return_value={
            "new_outstanding_balance": Decimal("90000"),
            "tenure_reduction_months": 5,
            "interest_savings": Decimal("3000"),
            "savings_percentage": Decimal("8.5"),
        },
    ):
        result = await analytics_service.analyze_prepayment(user_id, loan_id, Decimal("10000"))

    assert result.tenure_reduction_months == 5
    assert result.interest_savings == Decimal("3000")


# ---------------------------------------------------------------------------
# calculate_emi_impact
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_calculate_emi_impact_delegates_to_calculator(
    analytics_service,
):
    request = MagicMock()
    request.principal_amount = Decimal("100000")
    request.interest_rate = Decimal("9.0")
    request.loan_term_months = 120
    request.current_emi = Decimal("1100")

    fake_impact = {
        "original_emi": Decimal("1100"),
        "new_emi": Decimal("1050"),
        "original_tenure_months": 120,
        "new_tenure_months": 115,
        "tenure_reduction_months": 5,
        "original_total_interest": Decimal("32000"),
        "new_total_interest": Decimal("28000"),
        "interest_savings": Decimal("4000"),
        "savings_percentage": Decimal("12.5"),
    }

    with patch(
        "app.services.loan_analytics_service.PrepaymentCalculator.calculate_emi_change_impact",
        return_value=fake_impact,
    ):
        result = await analytics_service.calculate_emi_impact(request)

    assert result.tenure_reduction_months == 5
    assert result.interest_savings == Decimal("4000")
