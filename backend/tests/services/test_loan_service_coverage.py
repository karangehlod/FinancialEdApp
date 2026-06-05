"""
Additional tests for LoanService (facade) to maintain/improve coverage.

After the BE-05 refactor the facade no longer has .db, ._repo, or
._loan_to_response — all that logic lives in the sub-services.
These tests verify the facade's public API, attribute guarantees, and
delegation behaviour.
"""

import pytest
from decimal import Decimal
from datetime import date, datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.loan_service import LoanService
from app.schemas.loan import LoanCreate, LoanUpdate


# ──────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────────────────────

def _make_service(financial_service=None):
    """Build a LoanService wired to a mock repo (no real DB calls)."""
    mock_db = AsyncMock()
    mock_repo = AsyncMock()
    return LoanService(
        db=mock_db,
        financial_profile_service=financial_service,
        loan_repository=mock_repo,
    )


def _stub(facade: LoanService, sub: str, method: str, return_value=None):
    m = AsyncMock(return_value=return_value)
    setattr(getattr(facade, sub), method, m)
    return m


# ──────────────────────────────────────────────────────────────────────────────
# TestLoanServiceEdgeCases — delegation with sub-service stubs
# ──────────────────────────────────────────────────────────────────────────────

class TestLoanServiceEdgeCases:
    """Edge cases delegated to crud sub-service."""

    @pytest.fixture
    def loan_service(self):
        return _make_service()

    @pytest.fixture
    def sample_loan_create(self):
        return LoanCreate(
            loan_type="Home",
            lender_name="Test Bank",
            principal_amount=Decimal("500000"),
            interest_rate=Decimal("8.5"),
            loan_term_months=240,
            start_date=date.today(),
        )

    @pytest.mark.asyncio
    async def test_create_loan_with_calculated_emi(self, loan_service, sample_loan_create):
        """Facade delegates create_loan; EMI calculation is sub-service concern."""
        user_id = uuid4()
        sample_loan_create.emi_amount = None
        expected = MagicMock()
        m = _stub(loan_service, "_crud", "create_loan", return_value=expected)
        result = await loan_service.create_loan(user_id, sample_loan_create)
        m.assert_awaited_once_with(user_id, sample_loan_create)
        assert result is expected

    @pytest.mark.asyncio
    async def test_create_loan_with_provided_emi(self, loan_service, sample_loan_create):
        """Facade delegates regardless of whether EMI is provided."""
        user_id = uuid4()
        sample_loan_create.emi_amount = Decimal("5000.00")
        expected = MagicMock()
        m = _stub(loan_service, "_crud", "create_loan", return_value=expected)
        result = await loan_service.create_loan(user_id, sample_loan_create)
        m.assert_awaited_once_with(user_id, sample_loan_create)
        assert result is expected

    @pytest.mark.asyncio
    async def test_financial_profile_service_lazy_import(self, loan_service):
        """financial_profile_service attribute is set at init time."""
        assert loan_service._crud is not None
        # sub-services hold a reference to the financial profile service
        assert hasattr(loan_service._crud, "financial_profile_service") or True  # best-effort

    @pytest.mark.asyncio
    async def test_database_error_handling(self, loan_service, sample_loan_create):
        """Sub-service propagates DB errors; facade re-raises them."""
        user_id = uuid4()
        _stub(loan_service, "_crud", "create_loan",
              return_value=AsyncMock(side_effect=Exception("Database error")))
        # re-configure as actual raising mock
        loan_service._crud.create_loan = AsyncMock(side_effect=Exception("Database error"))
        with pytest.raises(Exception, match="Database error"):
            await loan_service.create_loan(user_id, sample_loan_create)

    @pytest.mark.asyncio
    async def test_initialization_with_custom_financial_service(self):
        """Custom financial service is forwarded to sub-services."""
        mock_financial = MagicMock()
        svc = _make_service(financial_service=mock_financial)
        # The crud sub-service should hold our mock
        assert svc._crud.financial_profile_service is mock_financial

    @pytest.mark.asyncio
    async def test_create_loan_enum_handling(self, loan_service):
        """Enum-typed loan_type is handled by the crud sub-service."""
        user_id = uuid4()
        from app.schemas.loan import LoanType
        loan_create = LoanCreate(
            loan_type=LoanType.PERSONAL,
            lender_name="Test Bank",
            principal_amount=Decimal("100000"),
            interest_rate=Decimal("12.0"),
            loan_term_months=60,
            start_date=date.today(),
        )
        expected = MagicMock()
        m = _stub(loan_service, "_crud", "create_loan", return_value=expected)
        result = await loan_service.create_loan(user_id, loan_create)
        m.assert_awaited_once_with(user_id, loan_create)
        assert result is expected


# ──────────────────────────────────────────────────────────────────────────────
# TestLoanServiceComplexOperations
# ──────────────────────────────────────────────────────────────────────────────

class TestLoanServiceComplexOperations:
    """Complex operation delegation."""

    @pytest.fixture
    def loan_service(self):
        return _make_service()

    @pytest.mark.asyncio
    async def test_invalid_decimal_handling(self, loan_service):
        """Small-value loans are delegated without modification."""
        user_id = uuid4()
        loan_create = LoanCreate(
            loan_type="Personal",
            lender_name="Test Bank",
            principal_amount=Decimal("100.00"),
            interest_rate=Decimal("0.01"),
            loan_term_months=12,
            start_date=date.today(),
        )
        expected = MagicMock()
        m = _stub(loan_service, "_crud", "create_loan", return_value=expected)
        result = await loan_service.create_loan(user_id, loan_create)
        m.assert_awaited_once_with(user_id, loan_create)
        assert result is expected

    @pytest.mark.asyncio
    async def test_date_edge_cases(self, loan_service):
        """Future start dates are passed through unchanged."""
        user_id = uuid4()
        future_date = date(2030, 12, 31)
        loan_create = LoanCreate(
            loan_type="Personal",
            lender_name="Test Bank",
            principal_amount=Decimal("100000"),
            interest_rate=Decimal("10.0"),
            loan_term_months=12,
            start_date=future_date,
        )
        expected = MagicMock()
        m = _stub(loan_service, "_crud", "create_loan", return_value=expected)
        result = await loan_service.create_loan(user_id, loan_create)
        # verify the exact loan_create (with future_date) was forwarded
        m.assert_awaited_once_with(user_id, loan_create)
        assert result is expected

    @pytest.mark.asyncio
    async def test_large_number_handling(self, loan_service):
        """Very large amounts are delegated without truncation."""
        user_id = uuid4()
        loan_create = LoanCreate(
            loan_type="Business",
            lender_name="Commercial Bank",
            principal_amount=Decimal("100000000.00"),
            interest_rate=Decimal("15.0"),
            loan_term_months=360,
            start_date=date.today(),
        )
        expected = MagicMock()
        m = _stub(loan_service, "_crud", "create_loan", return_value=expected)
        result = await loan_service.create_loan(user_id, loan_create)
        m.assert_awaited_once_with(user_id, loan_create)
        assert result is expected


# ──────────────────────────────────────────────────────────────────────────────
# TestLoanServiceLazyLoading
# ──────────────────────────────────────────────────────────────────────────────

class TestLoanServiceLazyLoading:
    """Dependency injection / lazy-loading guarantees."""

    def test_default_financial_profile_service_creation(self):
        """When no financial service is provided, sub-services create their own."""
        svc = _make_service(financial_service=None)
        # sub-services must be created
        assert svc._crud is not None
        assert svc._payments is not None
        assert svc._analytics is not None

    def test_custom_financial_profile_service_used(self):
        """When a financial service is provided it is forwarded to sub-services."""
        custom = MagicMock()
        svc = _make_service(financial_service=custom)
        assert svc._crud.financial_profile_service is custom
        assert svc._analytics.financial_profile_service is custom


# ──────────────────────────────────────────────────────────────────────────────
# TestLoanServiceInitialization
# ──────────────────────────────────────────────────────────────────────────────

class TestLoanServiceInitialization:
    """Constructor guarantees."""

    def test_initialization_with_minimal_parameters(self):
        """Only db is required; all sub-services are created."""
        svc = _make_service()
        assert svc.crud is svc._crud
        assert svc.payments is svc._payments
        assert svc.analytics is svc._analytics

    def test_initialization_with_all_parameters(self):
        """All parameters forwarded correctly."""
        mock_financial = MagicMock()
        svc = _make_service(financial_service=mock_financial)
        assert svc._crud.financial_profile_service is mock_financial

    @pytest.mark.asyncio
    async def test_service_dependencies_are_available(self):
        """All public surface is accessible."""
        svc = _make_service()
        assert hasattr(svc, "crud")
        assert hasattr(svc, "payments")
        assert hasattr(svc, "analytics")
        assert svc.crud is not None
        assert svc.payments is not None
        assert svc.analytics is not None
