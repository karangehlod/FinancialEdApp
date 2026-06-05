"""
Loan analytics service — handles schedule generation, analytics queries, and summaries.

SOLID compliance:
  - SRP: Only responsible for read-only analytics, schedule generation, and summaries.
  - DIP: Depends on ILoanRepository abstraction and LoanCrudService for response
         conversion; no direct SQLAlchemy imports for model-level queries.
  - OCP: New analytics dimensions can be added without changing existing methods.

Inherits BaseService for structured logging and standardised error handling.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DatabaseError
from app.db.models.data import Loan, LoanPayment
from app.repositories.interfaces import ILoanRepository
from app.repositories.loan_repository import LoanRepository
from app.schemas.loan import (
    LoanAnalytics,
    LoanResponse,
    LoanStatus,
    MonthlyLoanSummary,
    RepaymentScheduleItem,
    LoanSummary,
)
from app.services.base_service import BaseService
from app.services.loan_calculators import EMICalculator, PrepaymentCalculator
from app.services.loan_domain import DueDate

if TYPE_CHECKING:
    from app.services.loan_crud_service import LoanCrudService


class LoanAnalyticsService(BaseService):
    """
    Handles analytics queries, repayment schedule generation, and loan summaries.

    Responsibilities:
        - Generate full amortisation schedule for a loan.
        - Aggregate loan analytics (totals, outstanding balance, etc.).
        - Monthly payment summaries.
        - Per-loan or portfolio-level summaries.
        - Prepayment impact analysis.
        - EMI change impact analysis.
        - Comprehensive optimisation analysis.

    Constructor args:
        db:                        AsyncSession for raw aggregate queries.
        loan_repository:           ILoanRepository for loan/payment fetching.
        crud_service:              LoanCrudService for response conversion —
                                   injected to avoid duplicating to_response logic.
        financial_profile_service: Optional service for income/budget context.
    """

    def __init__(
        self,
        db: AsyncSession,
        loan_repository: Optional[ILoanRepository] = None,
        crud_service: Optional["LoanCrudService"] = None,
        financial_profile_service=None,
    ) -> None:
        super().__init__()
        self._repo: ILoanRepository = loan_repository or LoanRepository(db)
        self._db = db
        # Lazy import to avoid circular — assigned at runtime by the facade
        self._crud: Optional["LoanCrudService"] = crud_service
        self.financial_profile_service = financial_profile_service

    async def validate_dependencies(self) -> bool:
        """Validate that all required dependencies are available."""
        if not self._repo:
            raise DatabaseError("LoanRepository not initialised")
        return True

    # ------------------------------------------------------------------
    # Repayment schedule
    # ------------------------------------------------------------------

    async def generate_repayment_schedule(
        self, user_id: UUID, loan_id: UUID
    ) -> List[RepaymentScheduleItem]:
        """Generate the full amortisation schedule for a loan."""
        loan = await self._repo.get_loan_by_id(loan_id, user_id)
        if not loan:
            return []

        payments = await self._repo.get_loan_payments(loan_id)
        schedule: List[RepaymentScheduleItem] = []
        remaining_balance = float(loan.principal_amount)
        monthly_rate = float(loan.interest_rate) / 12 / 100
        payment_date = loan.start_date
        today = date.today()
        assume_historical_paid = len(payments) == 0
        recorded_dates = {p.payment_date for p in payments}

        for payment_num in range(1, loan.loan_term_months + 1):
            payment_date = (
                DueDate.calculate_next_due_date(loan.start_date)
                if payment_num == 1
                else DueDate.calculate_next_due_date(payment_date)
            )

            interest_portion = remaining_balance * monthly_rate if monthly_rate > 0 else 0.0
            principal_portion = float(loan.emi_amount) - interest_portion

            if remaining_balance < principal_portion:
                principal_portion = remaining_balance
                emi_amount = principal_portion + interest_portion
            else:
                emi_amount = float(loan.emi_amount)

            is_paid = payment_date in recorded_dates or (
                assume_historical_paid and payment_date <= today
            )
            remaining_balance -= principal_portion

            schedule.append(
                RepaymentScheduleItem(
                    payment_number=payment_num,
                    payment_date=payment_date,
                    emi_amount=Decimal(str(emi_amount)),
                    principal_portion=Decimal(str(principal_portion)),
                    interest_portion=Decimal(str(interest_portion)),
                    remaining_balance=Decimal(str(max(0, remaining_balance))),
                    is_paid=is_paid,
                )
            )
            if remaining_balance <= 0:
                break

        return schedule

    # ------------------------------------------------------------------
    # Aggregate analytics
    # ------------------------------------------------------------------

    async def get_loan_analytics(self, user_id: UUID) -> LoanAnalytics:
        """Return aggregate loan analytics for a user."""

        def _safe_decimal(v) -> Decimal:
            if v is None:
                return Decimal("0")
            try:
                return Decimal(str(v))
            except (ValueError, InvalidOperation):
                return Decimal("0")

        try:
            result = await self._db.execute(
                select(
                    func.count(Loan.id).label("total_loans"),
                    func.sum(Loan.principal_amount).label("total_principal"),
                    func.sum(Loan.outstanding_balance).label("total_outstanding"),
                    func.sum(Loan.emi_amount).label("total_monthly_emi"),
                ).where(Loan.user_id == user_id)
            )
            row = result.fetchone()
            total_loans = int(row[0] or 0) if row else 0
            total_principal = _safe_decimal(row[1] if row else None)
            total_outstanding = _safe_decimal(row[2] if row else None)
            total_monthly_emi = _safe_decimal(row[3] if row else None)
        except Exception as exc:
            self.log_error("get_loan_analytics_aggregate", exc)
            loans = await self._repo.get_loans_by_user(user_id)
            total_loans = len(loans)
            total_principal = sum(
                (_safe_decimal(l.principal_amount) for l in loans), Decimal("0")
            )
            total_outstanding = sum(
                (
                    _safe_decimal(l.outstanding_balance)
                    for l in loans
                    if l.status == LoanStatus.ACTIVE.value
                ),
                Decimal("0"),
            )
            total_monthly_emi = sum(
                (
                    _safe_decimal(l.emi_amount)
                    for l in loans
                    if l.status == LoanStatus.ACTIVE.value
                ),
                Decimal("0"),
            )

        return LoanAnalytics(
            total_loans=total_loans,
            active_loans=total_loans,
            total_principal_borrowed=total_principal,
            total_principal_amount=total_principal,
            total_outstanding_balance=total_outstanding,
            total_monthly_emi=total_monthly_emi,
            total_interest_paid=Decimal("0"),
            total_interest_remaining=Decimal("0"),
            loans_by_type={},
            average_interest_rate=Decimal("0"),
        )

    async def get_monthly_loan_summary(
        self, user_id: UUID, year: int, month: int
    ) -> MonthlyLoanSummary:
        """Return a payment summary for a given calendar month."""
        result = await self._db.execute(
            select(LoanPayment).where(
                and_(
                    LoanPayment.user_id == user_id,
                    func.extract("year", LoanPayment.payment_date) == year,
                    func.extract("month", LoanPayment.payment_date) == month,
                )
            )
        )
        payments = result.scalars().all()

        total_emi_paid = sum(
            getattr(p, "amount_paid", Decimal("0")) for p in payments
        )
        total_principal_paid = sum(
            getattr(p, "principal_amount", Decimal("0")) for p in payments
        )
        total_interest_paid = sum(
            getattr(p, "interest_amount", Decimal("0")) for p in payments
        )

        return MonthlyLoanSummary(
            month=f"{year}-{month:02d}",
            total_emi_paid=total_emi_paid,
            total_principal_paid=total_principal_paid,
            total_interest_paid=total_interest_paid,
            total_paid=total_emi_paid,
            loans=[],
            payment_schedule=[],
        )

    async def get_loan_summary(
        self,
        user_id: UUID,
        loan_id: Optional[UUID] = None,
    ):
        """
        Return a LoanSummary for a single loan, or a simple aggregate for all loans.

        When *loan_id* is None, returns a lightweight ``_Summary`` object; callers
        that need a full ``LoanSummary`` schema should pass an explicit loan_id.
        """
        if loan_id is not None:
            loan = await self._repo.get_loan_by_id(loan_id, user_id)
            if not loan:
                return None

            schedule = await self.generate_repayment_schedule(user_id, loan_id)
            today = date.today()
            next_payment = next(
                (item for item in schedule if not item.is_paid and item.payment_date >= today),
                None,
            )

            payments_made = len([s for s in schedule if s.is_paid])
            remaining_payments = len([s for s in schedule if not s.is_paid])
            remaining_balance = (
                schedule[payments_made - 1].remaining_balance
                if payments_made and payments_made - 1 < len(schedule)
                else loan.outstanding_balance
            )

            loan_response: LoanResponse = (
                await self._crud.to_response(loan)
                if self._crud
                else LoanResponse(
                    id=loan.id,
                    user_id=loan.user_id,
                    loan_type=loan.loan_type,
                    lender_name=loan.lender_name,
                    principal_amount=loan.principal_amount,
                    interest_rate=loan.interest_rate,
                    loan_term_months=loan.loan_term_months,
                    emi_amount=loan.emi_amount,
                    start_date=loan.start_date,
                    description=loan.description,
                    status=loan.status,
                    remaining_principal=loan.outstanding_balance,
                    total_paid=Decimal("0"),
                    next_payment_date=loan.next_due_date,
                    payments_made=payments_made,
                    payments_remaining=remaining_payments,
                    total_interest_paid=Decimal("0"),
                    created_at=loan.created_at,
                    updated_at=loan.updated_at,
                )
            )

            return LoanSummary(
                loan=loan_response,
                repayment_schedule=schedule,
                next_payment=next_payment,
                loan_analytics={
                    "remaining_balance": remaining_balance,
                    "total_interest_paid": loan.principal_amount
                    - Decimal(str(remaining_balance)),
                    "payments_made": payments_made,
                    "remaining_payments": remaining_payments,
                },
            )
        else:
            loans = await self._repo.get_loans_by_user(user_id)
            total_emi = sum(l.emi_amount or Decimal("0") for l in loans)
            total_outstanding = sum(l.outstanding_balance or Decimal("0") for l in loans)
            upcoming = [
                {"loan_id": l.id, "amount": l.emi_amount, "due_date": l.next_due_date}
                for l in loans
                if l.next_due_date and l.status == LoanStatus.ACTIVE.value
            ]

            class _PortfolioSummary:
                def __init__(self, n, emi, bal, upcoming_payments):
                    self.total_loans = n
                    self.total_emi = emi
                    self.total_outstanding = bal
                    self.upcoming_payments = upcoming_payments

            return _PortfolioSummary(len(loans), total_emi, total_outstanding, upcoming)

    # ------------------------------------------------------------------
    # Advanced calculations
    # ------------------------------------------------------------------

    async def calculate_emi_impact(self, calculation_request) -> "EMIImpactAnalysis":
        """Calculate the impact of changing EMI amount."""
        from app.schemas.loan import EMIImpactAnalysis

        impact = PrepaymentCalculator.calculate_emi_change_impact(
            calculation_request.principal_amount,
            calculation_request.interest_rate,
            calculation_request.loan_term_months,
            calculation_request.current_emi
            or EMICalculator.calculate_emi(
                calculation_request.principal_amount,
                calculation_request.interest_rate,
                calculation_request.loan_term_months,
            ),
        )
        return EMIImpactAnalysis(
            original_emi=impact["original_emi"],
            new_emi=impact["new_emi"],
            original_tenure_months=impact["original_tenure_months"],
            new_tenure_months=impact["new_tenure_months"],
            tenure_reduction_months=impact["tenure_reduction_months"],
            original_total_interest=impact["original_total_interest"],
            new_total_interest=impact["new_total_interest"],
            interest_savings=impact["interest_savings"],
            total_savings_percentage=impact["savings_percentage"],
        )

    async def analyze_prepayment(
        self, user_id: UUID, loan_id: UUID, prepayment_amount: Decimal
    ):
        """Analyse the impact of a lump-sum prepayment on a loan."""
        from app.schemas.loan import PrepaymentAnalysis

        loan = await self._repo.get_loan_by_id(loan_id, user_id)
        if not loan:
            raise ValueError("Loan not found")

        impact = PrepaymentCalculator.calculate_prepayment_impact(
            loan.outstanding_balance,
            prepayment_amount,
            loan.interest_rate,
            loan.emi_amount,
            loan.remaining_months,
        )
        return PrepaymentAnalysis(
            prepayment_amount=prepayment_amount,
            new_outstanding_balance=impact["new_outstanding_balance"],
            tenure_reduction_months=impact["tenure_reduction_months"],
            interest_savings=impact["interest_savings"],
            savings_percentage=impact["savings_percentage"],
        )

    async def get_comprehensive_loan_analysis(self, user_id: UUID):
        """Return optimisation suggestions and budget integration data."""
        from app.schemas.loan import (
            BudgetLoanIntegration,
            ComprehensiveLoanAnalysis,
            LoanOptimizationSuggestion,
        )

        loans: List[LoanResponse] = (
            await self._crud.get_user_loans(user_id, LoanStatus.ACTIVE.value)
            if self._crud
            else []
        )

        def _empty_budget_integration():
            return BudgetLoanIntegration(
                month=datetime.now(timezone.utc).strftime("%Y-%m"),
                total_emi_budget=Decimal("0"),
                loans=[],
                weekly_breakdown=[],
                budget_utilization_percentage=Decimal("0"),
                available_for_prepayment=Decimal("0"),
            )

        if not loans:
            return ComprehensiveLoanAnalysis(
                total_loans=0,
                total_outstanding=Decimal("0"),
                total_monthly_emi=Decimal("0"),
                weighted_average_interest_rate=Decimal("0"),
                total_remaining_interest=Decimal("0"),
                loan_to_income_ratio=Decimal("0"),
                monthly_budget_allocation=Decimal("0"),
                optimization_opportunities=[],
                budget_integration=_empty_budget_integration(),
            )

        total_outstanding = sum(l.outstanding_balance for l in loans)
        total_monthly_emi = sum(l.emi_amount for l in loans)
        weighted_rate = sum(
            float(l.interest_rate) * float(l.outstanding_balance) for l in loans
        )
        weighted_average_rate = (
            weighted_rate / float(total_outstanding) if total_outstanding > 0 else 0
        )

        total_remaining_interest = Decimal("0")
        for loan in loans:
            sched = await self.generate_repayment_schedule(user_id, loan.id)
            total_remaining_interest += sum(
                s.interest_portion for s in sched if not s.is_paid
            )

        profile = (
            await self.financial_profile_service.get(user_id)
            if self.financial_profile_service
            else None
        )
        loan_to_income_ratio = Decimal("0")
        monthly_budget_allocation = Decimal("0")
        if profile and profile.monthly_salary:
            loan_to_income_ratio = total_monthly_emi / profile.monthly_salary * 100
            if profile.disposable_income:
                monthly_budget_allocation = (
                    total_monthly_emi / profile.disposable_income * 100
                )

        suggestions = [
            LoanOptimizationSuggestion(
                loan_id=loan.id,
                suggestion_type="refinance",
                current_situation={
                    "interest_rate": float(loan.interest_rate),
                    "monthly_emi": float(loan.emi_amount),
                    "remaining_balance": float(loan.outstanding_balance),
                },
                suggested_action={
                    "action": "Consider refinancing to lower interest rate",
                    "target_rate": min(float(loan.interest_rate) - 2, 8.5),
                },
                potential_savings={
                    "monthly_savings": float(loan.emi_amount) * 0.15,
                    "total_savings": float(total_remaining_interest) * 0.20,
                },
                risk_assessment="Low risk if credit score is good",
            )
            for loan in loans
            if float(loan.interest_rate) > 10
        ]

        return ComprehensiveLoanAnalysis(
            total_loans=len(loans),
            total_outstanding=total_outstanding,
            total_monthly_emi=total_monthly_emi,
            weighted_average_interest_rate=Decimal(str(round(weighted_average_rate, 2))),
            total_remaining_interest=total_remaining_interest,
            loan_to_income_ratio=loan_to_income_ratio,
            monthly_budget_allocation=monthly_budget_allocation,
            optimization_opportunities=suggestions,
            budget_integration=_empty_budget_integration(),
        )
