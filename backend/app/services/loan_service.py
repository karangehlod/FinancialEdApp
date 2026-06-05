"""
LoanService facade — backward-compatible orchestrator for loan operations.

SOLID compliance:
  - SRP: This file only wires sub-services together and delegates every call.
         No business logic lives here.
  - OCP: New capabilities can be added by enhancing a sub-service without
         touching this facade.
  - DIP: All concrete dependencies are injected; callers depend on ILoanService.

Sub-services:
  - LoanCrudService      → CRUD lifecycle (create / read / update / delete).
  - LoanPaymentService   → Payment recording and loan balance/status updates.
  - LoanAnalyticsService → Analytics, schedule generation, summaries.

This facade preserves the original public API so that all existing router
call-sites require zero changes.
"""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.interfaces import ILoanRepository
from app.repositories.loan_repository import LoanRepository
from app.schemas.loan import (
    EMIImpactAnalysis,
    LoanAnalytics,
    LoanCreate,
    LoanPaymentCreate,
    LoanPaymentResponse,
    LoanResponse,
    LoanSummary,
    LoanUpdate,
    MonthlyLoanSummary,
    RepaymentScheduleItem,
)
from app.services.base_service import BaseService
from app.services.loan_analytics_service import LoanAnalyticsService
from app.services.loan_crud_service import LoanCrudService
from app.services.loan_payment_service import LoanPaymentService
from app.services.service_interfaces import ILoanService


class LoanService(BaseService, ILoanService):
    """
    Facade orchestrating all loan domain operations.

    Delegates:
        CRUD       → LoanCrudService
        Payments   → LoanPaymentService
        Analytics  → LoanAnalyticsService

    Constructor args:
        db:                        AsyncSession for sub-service construction and
                                   raw aggregate queries.
        financial_profile_service: Optional service for EMI total sync on profile.
        loan_repository:           ILoanRepository injected for all sub-services.
                                   When omitted a LoanRepository is built from *db*.
    """

    def __init__(
        self,
        db: AsyncSession,
        financial_profile_service=None,
        loan_repository: Optional[ILoanRepository] = None,
    ) -> None:
        super().__init__()
        repo: ILoanRepository = loan_repository or LoanRepository(db)

        self._crud = LoanCrudService(
            db=db,
            loan_repository=repo,
            financial_profile_service=financial_profile_service,
        )
        self._payments = LoanPaymentService(
            db=db,
            loan_repository=repo,
        )
        self._analytics = LoanAnalyticsService(
            db=db,
            loan_repository=repo,
            crud_service=self._crud,
            financial_profile_service=financial_profile_service,
        )

        # Expose sub-services for callers that hold a LoanService reference
        # and need to reach sub-service methods not on ILoanService.
        self.crud = self._crud
        self.payments = self._payments
        self.analytics = self._analytics

    async def validate_dependencies(self) -> bool:
        """Validate all sub-service dependencies."""
        await self._crud.validate_dependencies()
        await self._payments.validate_dependencies()
        await self._analytics.validate_dependencies()
        return True

    # ------------------------------------------------------------------
    # ILoanService — CRUD delegation
    # ------------------------------------------------------------------

    async def create_loan(self, user_id: UUID, loan_data: LoanCreate) -> LoanResponse:
        return await self._crud.create_loan(user_id, loan_data)

    async def get_loan(self, user_id: UUID, loan_id: UUID) -> Optional[LoanResponse]:
        return await self._crud.get_loan(user_id, loan_id)

    async def get_user_loans(
        self, user_id: UUID, status: Optional[str] = None
    ) -> List[LoanResponse]:
        return await self._crud.get_user_loans(user_id, status)

    async def update_loan(
        self, user_id: UUID, loan_id: UUID, loan_data: LoanUpdate
    ) -> Optional[LoanResponse]:
        return await self._crud.update_loan(user_id, loan_id, loan_data)

    async def delete_loan(self, user_id: UUID, loan_id: UUID) -> bool:
        return await self._crud.delete_loan(user_id, loan_id)

    async def add_payment(
        self, user_id: UUID, loan_id: UUID, payment_data: LoanPaymentCreate
    ) -> LoanResponse:
        """ILoanService.add_payment — delegates to LoanPaymentService."""
        return await self._payments.make_payment(user_id, loan_id, payment_data)

    # ------------------------------------------------------------------
    # Payment delegation (extended public API)
    # ------------------------------------------------------------------

    async def make_payment(
        self, user_id: UUID, loan_id: UUID, payment_data: LoanPaymentCreate
    ) -> Optional[LoanPaymentResponse]:
        return await self._payments.make_payment(user_id, loan_id, payment_data)

    async def get_loan_payments(
        self, user_id: UUID, loan_id: UUID
    ) -> List[LoanPaymentResponse]:
        return await self._payments.get_loan_payments(user_id, loan_id)

    # ------------------------------------------------------------------
    # Analytics delegation
    # ------------------------------------------------------------------

    async def generate_repayment_schedule(
        self, user_id: UUID, loan_id: UUID
    ) -> List[RepaymentScheduleItem]:
        return await self._analytics.generate_repayment_schedule(user_id, loan_id)

    async def get_loan_analytics(self, user_id: UUID) -> LoanAnalytics:
        return await self._analytics.get_loan_analytics(user_id)

    async def get_monthly_loan_summary(
        self, user_id: UUID, year: int, month: int
    ) -> MonthlyLoanSummary:
        return await self._analytics.get_monthly_loan_summary(user_id, year, month)

    async def get_loan_summary(
        self, user_id: UUID, loan_id: Optional[UUID] = None
    ):
        return await self._analytics.get_loan_summary(user_id, loan_id)

    async def calculate_emi_impact(self, calculation_request) -> "EMIImpactAnalysis":
        return await self._analytics.calculate_emi_impact(calculation_request)

    async def analyze_prepayment(
        self, user_id: UUID, loan_id: UUID, prepayment_amount: Decimal
    ):
        return await self._analytics.analyze_prepayment(user_id, loan_id, prepayment_amount)

    async def get_comprehensive_loan_analysis(self, user_id: UUID):
        return await self._analytics.get_comprehensive_loan_analysis(user_id)

    async def configure_loan(self, user_id: UUID, loan_config):
        return await self._crud.configure_loan(user_id, loan_config)
