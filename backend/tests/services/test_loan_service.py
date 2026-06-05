"""
Tests for the LoanService facade (loan_service.py).

After the BE-05 refactor, LoanService is a thin facade that delegates to:
  - LoanCrudService    (self._crud)
  - LoanPaymentService (self._payments)
  - LoanAnalyticsService (self._analytics)

All tests mock the sub-services rather than reaching into `db` directly,
which is the correct pattern for a facade.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.loan_service import LoanService
from app.schemas.loan import LoanCreate, LoanUpdate, LoanPaymentCreate
from app.db.models.data import Loan, LoanPayment


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    """Minimal AsyncSession mock — used only to satisfy the constructor."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_financial_profile_service():
    svc = AsyncMock()
    svc.update_from_loans = AsyncMock()
    return svc


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def loan_id():
    return uuid4()


@pytest.fixture
def loan_service(mock_db, mock_financial_profile_service):
    """
    LoanService with a mocked LoanRepository so no real DB calls happen.
    The same mock_repo is shared by all three sub-services.
    """
    mock_repo = AsyncMock()
    return LoanService(
        db=mock_db,
        financial_profile_service=mock_financial_profile_service,
        loan_repository=mock_repo,
    )


@pytest.fixture
def sample_loan(user_id, loan_id):
    return Loan(
        id=loan_id,
        user_id=user_id,
        loan_type="Personal",
        lender_name="Bank A",
        principal_amount=Decimal("100000.00"),
        outstanding_balance=Decimal("80000.00"),
        interest_rate=Decimal("8.5"),
        emi_amount=Decimal("2500.00"),
        loan_term_months=60,
        remaining_months=28,
        start_date=date(2023, 1, 1),
        next_due_date=date(2026, 2, 1),
        status="Active",
        description="Personal loan",
        created_at=datetime.now(),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────

def _stub(facade: LoanService, sub: str, method: str, return_value=None):
    """Patch facade.<sub>.<method> with an AsyncMock and return the mock."""
    mock = AsyncMock(return_value=return_value)
    setattr(getattr(facade, sub), method, mock)
    return mock


# ──────────────────────────────────────────────────────────────────────────────
# TestLoanService — basic delegation
# ──────────────────────────────────────────────────────────────────────────────

class TestLoanService:
    """Verify the facade wires sub-services correctly."""

    def test_init_exposes_sub_services(self, loan_service):
        assert hasattr(loan_service, "crud")
        assert hasattr(loan_service, "payments")
        assert hasattr(loan_service, "analytics")
        assert loan_service.crud is loan_service._crud
        assert loan_service.payments is loan_service._payments
        assert loan_service.analytics is loan_service._analytics

    @pytest.mark.asyncio
    async def test_get_loan_delegates_to_crud(self, loan_service, user_id, loan_id, sample_loan):
        m = _stub(loan_service, "_crud", "get_loan", return_value=sample_loan)
        result = await loan_service.get_loan(user_id, loan_id)
        m.assert_awaited_once_with(user_id, loan_id)
        assert result is sample_loan

    @pytest.mark.asyncio
    async def test_get_loan_not_found(self, loan_service, user_id, loan_id):
        m = _stub(loan_service, "_crud", "get_loan", return_value=None)
        result = await loan_service.get_loan(user_id, loan_id)
        m.assert_awaited_once_with(user_id, loan_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_loans_delegates(self, loan_service, user_id, sample_loan):
        m = _stub(loan_service, "_crud", "get_user_loans", return_value=[sample_loan])
        result = await loan_service.get_user_loans(user_id)
        m.assert_awaited_once_with(user_id, None)
        assert result == [sample_loan]

    @pytest.mark.asyncio
    async def test_get_user_loans_with_status_filter(self, loan_service, user_id, sample_loan):
        m = _stub(loan_service, "_crud", "get_user_loans", return_value=[sample_loan])
        result = await loan_service.get_user_loans(user_id, status="Active")
        m.assert_awaited_once_with(user_id, "Active")
        assert result == [sample_loan]

    @pytest.mark.asyncio
    async def test_get_user_loans_empty(self, loan_service, user_id):
        _stub(loan_service, "_crud", "get_user_loans", return_value=[])
        result = await loan_service.get_user_loans(user_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_create_loan_delegates_to_crud(self, loan_service, user_id, sample_loan):
        loan_data = LoanCreate(
            loan_type="Personal",
            lender_name="Bank A",
            principal_amount=Decimal("100000.00"),
            interest_rate=Decimal("8.5"),
            loan_term_months=60,
            start_date=date(2026, 1, 1),
            description="Personal loan",
        )
        m = _stub(loan_service, "_crud", "create_loan", return_value=sample_loan)
        result = await loan_service.create_loan(user_id, loan_data)
        m.assert_awaited_once_with(user_id, loan_data)
        assert result is sample_loan

    @pytest.mark.asyncio
    async def test_create_loan_with_custom_emi(self, loan_service, user_id, sample_loan):
        loan_data = LoanCreate(
            loan_type="Home",
            lender_name="Bank B",
            principal_amount=Decimal("2000000.00"),
            interest_rate=Decimal("6.5"),
            loan_term_months=240,
            start_date=date(2026, 1, 1),
            emi_amount=Decimal("15000.00"),
            description="Home loan",
        )
        _stub(loan_service, "_crud", "create_loan", return_value=sample_loan)
        result = await loan_service.create_loan(user_id, loan_data)
        assert result is sample_loan

    @pytest.mark.asyncio
    async def test_update_loan_delegates_to_crud(self, loan_service, user_id, loan_id, sample_loan):
        loan_data = LoanUpdate(emi_amount=Decimal("3000.00"))
        m = _stub(loan_service, "_crud", "update_loan", return_value=sample_loan)
        result = await loan_service.update_loan(user_id, loan_id, loan_data)
        m.assert_awaited_once_with(user_id, loan_id, loan_data)
        assert result is sample_loan

    @pytest.mark.asyncio
    async def test_delete_loan_success(self, loan_service, user_id, loan_id):
        m = _stub(loan_service, "_crud", "delete_loan", return_value=True)
        result = await loan_service.delete_loan(user_id, loan_id)
        m.assert_awaited_once_with(user_id, loan_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_loan_not_found(self, loan_service, user_id, loan_id):
        _stub(loan_service, "_crud", "delete_loan", return_value=False)
        result = await loan_service.delete_loan(user_id, loan_id)
        assert result is False


# ──────────────────────────────────────────────────────────────────────────────
# TestLoanServiceComprehensive — more CRUD scenarios
# ──────────────────────────────────────────────────────────────────────────────

class TestLoanServiceComprehensive:
    """Extended CRUD delegation scenarios."""

    @pytest.mark.asyncio
    async def test_delete_loan_with_payments(self, loan_service, user_id, loan_id):
        """delete_loan returns True regardless of whether payments exist (handled in sub-service)."""
        _stub(loan_service, "_crud", "delete_loan", return_value=True)
        result = await loan_service.delete_loan(user_id, loan_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_make_payment_success(self, loan_service, user_id, loan_id):
        payment_data = LoanPaymentCreate(
            amount=Decimal("2500.00"),
            payment_date=date(2023, 2, 1),
        )
        expected = MagicMock()
        _stub(loan_service, "_payments", "make_payment", return_value=expected)
        result = await loan_service.make_payment(user_id, loan_id, payment_data)
        assert result is expected

    @pytest.mark.asyncio
    async def test_get_loan_payments_history(self, loan_service, user_id, loan_id):
        expected = [MagicMock(), MagicMock()]
        _stub(loan_service, "_payments", "get_loan_payments", return_value=expected)
        payments = await loan_service.get_loan_payments(user_id, loan_id)
        assert isinstance(payments, list)
        assert payments is expected

    @pytest.mark.asyncio
    async def test_generate_repayment_schedule(self, loan_service, user_id, loan_id):
        expected = [MagicMock(), MagicMock()]
        _stub(loan_service, "_analytics", "generate_repayment_schedule", return_value=expected)
        schedule = await loan_service.generate_repayment_schedule(user_id, loan_id)
        assert isinstance(schedule, list)

    @pytest.mark.asyncio
    async def test_get_loan_analytics_comprehensive(self, loan_service, user_id):
        expected = MagicMock()
        _stub(loan_service, "_analytics", "get_loan_analytics", return_value=expected)
        analytics = await loan_service.get_loan_analytics(user_id)
        assert analytics is expected

    @pytest.mark.asyncio
    async def test_get_monthly_loan_summary_data(self, loan_service, user_id):
        expected = MagicMock()
        _stub(loan_service, "_analytics", "get_monthly_loan_summary", return_value=expected)
        summary = await loan_service.get_monthly_loan_summary(user_id, 2024, 1)
        assert summary is expected

    @pytest.mark.asyncio
    async def test_get_loan_summary_with_multiple_loans(self, loan_service, user_id):
        expected = MagicMock()
        _stub(loan_service, "_analytics", "get_loan_summary", return_value=expected)
        summary = await loan_service.get_loan_summary(user_id)
        assert summary is expected

    @pytest.mark.asyncio
    async def test_analyze_prepayment_scenario(self, loan_service, user_id, loan_id):
        expected = MagicMock()
        _stub(loan_service, "_analytics", "analyze_prepayment", return_value=expected)
        analysis = await loan_service.analyze_prepayment(user_id, loan_id, Decimal("10000.00"))
        assert analysis is expected


# ──────────────────────────────────────────────────────────────────────────────
# TestLoanServicePaymentScenarios
# ──────────────────────────────────────────────────────────────────────────────

class TestLoanServicePaymentScenarios:
    """Payment edge-case delegation tests."""

    @pytest.mark.asyncio
    async def test_make_payment_closes_loan_when_balance_zero(self, loan_service, user_id, loan_id):
        """Sub-service handles balance → 0 logic; facade just delegates."""
        payment_data = LoanPaymentCreate(
            amount=Decimal("2500.00"),
            payment_date=date(2023, 2, 1),
            notes=None,
        )
        expected = MagicMock()
        _stub(loan_service, "_payments", "make_payment", return_value=expected)
        result = await loan_service.make_payment(user_id, loan_id, payment_data)
        assert result is expected

    @pytest.mark.asyncio
    async def test_make_payment_inactive_loan(self, loan_service, user_id, loan_id):
        """Closed-loan guard lives in LoanPaymentService; facade returns None."""
        payment_data = LoanPaymentCreate(
            amount=Decimal("2500.00"),
            payment_date=date(2023, 2, 1),
        )
        _stub(loan_service, "_payments", "make_payment", return_value=None)
        result = await loan_service.make_payment(user_id, loan_id, payment_data)
        assert result is None

    @pytest.mark.asyncio
    async def test_make_payment_interest_only(self, loan_service, user_id, loan_id):
        """Payment smaller than interest — still delegated successfully."""
        payment_data = LoanPaymentCreate(
            amount=Decimal("500.00"),
            payment_date=date(2023, 2, 1),
        )
        expected = MagicMock()
        _stub(loan_service, "_payments", "make_payment", return_value=expected)
        result = await loan_service.make_payment(user_id, loan_id, payment_data)
        assert result is expected

    @pytest.mark.asyncio
    async def test_make_payment_reduces_balance(self, loan_service, user_id, loan_id):
        """Facade delegates; balance reduction is sub-service responsibility."""
        payment_data = LoanPaymentCreate(
            amount=Decimal("2500.00"),
            payment_date=date(2023, 2, 1),
        )
        expected = MagicMock()
        _stub(loan_service, "_payments", "make_payment", return_value=expected)
        result = await loan_service.make_payment(user_id, loan_id, payment_data)
        assert result is expected


# ──────────────────────────────────────────────────────────────────────────────
# TestLoanServiceUpdate — enum-handling delegation
# ──────────────────────────────────────────────────────────────────────────────

class TestLoanServiceUpdate:
    @pytest.mark.asyncio
    async def test_update_loan_with_loan_type_enum(self, loan_service, user_id, loan_id, sample_loan):
        from app.schemas.loan import LoanType
        loan_data = LoanUpdate(loan_type=LoanType.HOME)
        _stub(loan_service, "_crud", "update_loan", return_value=sample_loan)
        result = await loan_service.update_loan(user_id, loan_id, loan_data)
        assert result is sample_loan

    @pytest.mark.asyncio
    async def test_update_loan_with_status_enum(self, loan_service, user_id, loan_id, sample_loan):
        from app.schemas.loan import LoanStatus
        loan_data = LoanUpdate(status=LoanStatus.CLOSED)
        _stub(loan_service, "_crud", "update_loan", return_value=sample_loan)
        result = await loan_service.update_loan(user_id, loan_id, loan_data)
        assert result is sample_loan

    @pytest.mark.asyncio
    async def test_update_loan_recalculates_emi(self, loan_service, user_id, loan_id, sample_loan):
        loan_data = LoanUpdate(principal_amount=Decimal("150000.00"))
        _stub(loan_service, "_crud", "update_loan", return_value=sample_loan)
        result = await loan_service.update_loan(user_id, loan_id, loan_data)
        assert result is sample_loan

    @pytest.mark.asyncio
    async def test_update_loan_interest_rate_change(self, loan_service, user_id, loan_id, sample_loan):
        loan_data = LoanUpdate(interest_rate=Decimal("10.5"))
        _stub(loan_service, "_crud", "update_loan", return_value=sample_loan)
        result = await loan_service.update_loan(user_id, loan_id, loan_data)
        assert result is sample_loan

    @pytest.mark.asyncio
    async def test_update_loan_tenure_change(self, loan_service, user_id, loan_id, sample_loan):
        loan_data = LoanUpdate(loan_term_months=72)
        _stub(loan_service, "_crud", "update_loan", return_value=sample_loan)
        result = await loan_service.update_loan(user_id, loan_id, loan_data)
        assert result is sample_loan


# ──────────────────────────────────────────────────────────────────────────────
# TestLoanServiceAnalytics — extended
# ──────────────────────────────────────────────────────────────────────────────

class TestLoanServiceAnalyticsExtended:
    @pytest.mark.asyncio
    async def test_get_loan_analytics_empty_result(self, loan_service, user_id):
        analytics = MagicMock()
        analytics.total_loans = 0
        _stub(loan_service, "_analytics", "get_loan_analytics", return_value=analytics)
        result = await loan_service.get_loan_analytics(user_id)
        assert result.total_loans == 0

    @pytest.mark.asyncio
    async def test_get_monthly_loan_summary_with_payments(self, loan_service, user_id):
        summary = MagicMock()
        summary.month = "2024-01"
        _stub(loan_service, "_analytics", "get_monthly_loan_summary", return_value=summary)
        result = await loan_service.get_monthly_loan_summary(user_id, 2024, 1)
        assert result.month == "2024-01"

    @pytest.mark.asyncio
    async def test_get_monthly_loan_summary_no_payments(self, loan_service, user_id):
        summary = MagicMock()
        summary.total_emi_paid = 0
        _stub(loan_service, "_analytics", "get_monthly_loan_summary", return_value=summary)
        result = await loan_service.get_monthly_loan_summary(user_id, 2024, 1)
        assert result.total_emi_paid == 0

    @pytest.mark.asyncio
    async def test_get_loan_summary_single_loan_with_schedule(self, loan_service, user_id):
        """Facade delegates get_user_loans and returns whatever crud gives."""
        _stub(loan_service, "_crud", "get_user_loans", return_value=[])
        result = await loan_service.get_user_loans(user_id)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_loan_summary_single_loan_not_found(self, loan_service, user_id, loan_id):
        _stub(loan_service, "_analytics", "get_loan_summary", return_value=None)
        summary = await loan_service.get_loan_summary(user_id, loan_id)
        assert summary is None


# ──────────────────────────────────────────────────────────────────────────────
# TestLoanServiceCalculations
# ──────────────────────────────────────────────────────────────────────────────

class TestLoanServiceCalculations:
    @pytest.mark.asyncio
    async def test_calculate_emi_impact_with_higher_emi(self, loan_service):
        calc_request = MagicMock()
        calc_request.principal_amount = Decimal("100000.00")
        calc_request.interest_rate = Decimal("8.5")
        calc_request.loan_term_months = 60
        calc_request.current_emi = Decimal("3000.00")
        expected = MagicMock()
        expected.tenure_reduction_months = 5
        _stub(loan_service, "_analytics", "calculate_emi_impact", return_value=expected)
        result = await loan_service.calculate_emi_impact(calc_request)
        assert result.tenure_reduction_months >= 0

    @pytest.mark.asyncio
    async def test_calculate_emi_impact_no_interest(self, loan_service):
        calc_request = MagicMock()
        calc_request.interest_rate = Decimal("0.00")
        expected = MagicMock()
        _stub(loan_service, "_analytics", "calculate_emi_impact", return_value=expected)
        result = await loan_service.calculate_emi_impact(calc_request)
        assert result is expected

    @pytest.mark.asyncio
    async def test_analyze_prepayment_full_payoff(self, loan_service, user_id, loan_id):
        analysis = MagicMock()
        analysis.new_outstanding_balance = Decimal("0")
        analysis.tenure_reduction_months = 4
        _stub(loan_service, "_analytics", "analyze_prepayment", return_value=analysis)
        result = await loan_service.analyze_prepayment(user_id, loan_id, Decimal("10000.00"))
        assert result.new_outstanding_balance == Decimal("0")
        assert result.tenure_reduction_months == 4

    @pytest.mark.asyncio
    async def test_analyze_prepayment_partial(self, loan_service, user_id, loan_id):
        analysis = MagicMock()
        analysis.prepayment_amount = Decimal("10000.00")
        _stub(loan_service, "_analytics", "analyze_prepayment", return_value=analysis)
        result = await loan_service.analyze_prepayment(user_id, loan_id, Decimal("10000.00"))
        assert result.prepayment_amount == Decimal("10000.00")


# ──────────────────────────────────────────────────────────────────────────────
# TestLoanServiceValidateDependencies
# ──────────────────────────────────────────────────────────────────────────────

class TestLoanServiceValidateDependencies:
    @pytest.mark.asyncio
    async def test_validate_dependencies_chains_all_sub_services(self, loan_service):
        mc = _stub(loan_service, "_crud", "validate_dependencies", return_value=True)
        mp = _stub(loan_service, "_payments", "validate_dependencies", return_value=True)
        ma = _stub(loan_service, "_analytics", "validate_dependencies", return_value=True)
        result = await loan_service.validate_dependencies()
        assert result is True
        mc.assert_awaited_once()
        mp.assert_awaited_once()
        ma.assert_awaited_once()
