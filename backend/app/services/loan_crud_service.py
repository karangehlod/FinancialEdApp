"""
Loan CRUD service — handles create, read, update, and delete operations for loans.

SOLID compliance:
  - SRP: Only responsible for loan lifecycle CRUD operations.
  - DIP: Depends on ILoanRepository abstraction, not SQLAlchemy directly.
  - OCP: New loan types / validation rules can be added without modifying this class.

Inherits BaseService for structured logging and standardised error handling.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from app.utils.datetime_utils import utcnow_naive
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DatabaseError
from app.core.transaction_decorators import transactional, with_retry
from app.db.models.data import Loan
from app.repositories.interfaces import ILoanRepository
from app.repositories.loan_repository import LoanRepository
from app.schemas.loan import (
    LoanCreate,
    LoanResponse,
    LoanStatus,
    LoanUpdate,
    PaymentStatus,
)
from app.services.base_service import BaseService
from app.services.loan_calculators import EMICalculator
from app.services.loan_domain import DueDate


class LoanCrudService(BaseService):
    """
    Handles all CRUD operations for loans.

    Responsibilities:
        - Create a loan (with EMI calculation if not supplied).
        - Retrieve a single loan or all loans for a user.
        - Update loan fields and recalculate EMI when financial fields change.
        - Delete a loan.
        - Convert ORM Loan instances to LoanResponse schemas.

    Constructor args:
        db:                       AsyncSession (used for commit/refresh and default
                                  repo construction).
        loan_repository:          ILoanRepository — injected for all DB access.
        financial_profile_service: Optional service to keep the user's financial
                                  profile in sync after mutations.
    """

    def __init__(
        self,
        db: AsyncSession,
        loan_repository: Optional[ILoanRepository] = None,
        financial_profile_service=None,
    ) -> None:
        super().__init__()
        self._repo: ILoanRepository = loan_repository or LoanRepository(db)
        self._db = db
        self.financial_profile_service = financial_profile_service

    async def validate_dependencies(self) -> bool:
        """Validate that all required dependencies are available."""
        if not self._repo:
            raise DatabaseError("LoanRepository not initialised")
        return True

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @transactional(rollback_on_error=True)
    @with_retry(max_attempts=3, backoff="exponential")
    async def create_loan(self, user_id: UUID, loan_data: LoanCreate) -> LoanResponse:
        """Create a new loan, calculating EMI if not provided."""
        self.log_operation("create_loan", {"user_id": str(user_id)})
        try:
            emi = loan_data.emi_amount
            if emi is None:
                emi = EMICalculator.calculate_emi(
                    loan_data.principal_amount,
                    loan_data.interest_rate,
                    loan_data.loan_term_months,
                )

            next_due_date = DueDate.calculate_next_due_date(loan_data.start_date)
            loan_data_with_emi = loan_data.model_copy(update={"emi_amount": emi})
            db_loan = await self._repo.create_loan(user_id, loan_data_with_emi)
            db_loan.next_due_date = next_due_date
            db_loan.status = LoanStatus.ACTIVE.value
            await self._db.commit()
            await self._db.refresh(db_loan)

            if self.financial_profile_service:
                await self.financial_profile_service.update_from_loans(user_id)

            self.log_operation("create_loan_success", {"loan_id": str(db_loan.id)})
            return await self.to_response(db_loan)
        except Exception as exc:
            self.log_error("create_loan", exc, {"user_id": str(user_id)})
            raise

    async def get_loan(self, user_id: UUID, loan_id: UUID) -> Optional[LoanResponse]:
        """Return a single loan by ID, or None if not found."""
        loan = await self._repo.get_loan_by_id(loan_id, user_id)
        if not loan:
            return None
        return await self.to_response(loan)

    async def get_user_loans(
        self, user_id: UUID, status: Optional[str] = None
    ) -> List[LoanResponse]:
        """Return all loans for a user, optionally filtered by status."""
        loans = await self._repo.get_loans_by_user(user_id, status)
        return [await self.to_response(loan) for loan in loans]

    @transactional(rollback_on_error=True)
    @with_retry(max_attempts=3, backoff="exponential")
    async def update_loan(
        self, user_id: UUID, loan_id: UUID, loan_data: LoanUpdate
    ) -> Optional[LoanResponse]:
        """Update loan fields and recalculate EMI when financial fields change."""
        self.log_operation("update_loan", {"loan_id": str(loan_id)})
        try:
            loan = await self._repo.get_loan_by_id(loan_id, user_id)
            if not loan:
                return None

            update_fields = loan_data.model_dump(exclude_unset=True)
            for field, value in update_fields.items():
                if field == "loan_type" and value:
                    setattr(loan, field, value.value)
                elif field == "status" and value:
                    setattr(loan, field, value.value)
                elif field == "start_date" and value is not None:
                    loan.start_date = value
                    loan.next_due_date = DueDate.calculate_next_due_date(value)
                    months_elapsed = max(
                        0,
                        (date.today().year - value.year) * 12
                        + (date.today().month - value.month),
                    )
                    loan.remaining_months = max(0, loan.loan_term_months - months_elapsed)
                elif value is not None:
                    setattr(loan, field, value)

            # Recalculate EMI when financial parameters change
            if any(
                f in update_fields
                for f in ("principal_amount", "interest_rate", "loan_term_months")
            ):
                loan.emi_amount = EMICalculator.calculate_emi(
                    loan.principal_amount,
                    loan.interest_rate,
                    loan.loan_term_months,
                )

            loan.updated_at = utcnow_naive()
            await self._db.commit()
            await self._db.refresh(loan)

            if self.financial_profile_service:
                await self.financial_profile_service.update_from_loans(user_id)

            return await self.to_response(loan)
        except Exception as exc:
            self.log_error("update_loan", exc, {"loan_id": str(loan_id)})
            raise

    @transactional(rollback_on_error=True)
    async def delete_loan(self, user_id: UUID, loan_id: UUID) -> bool:
        """Delete a loan and update the user's financial profile."""
        self.log_operation("delete_loan", {"loan_id": str(loan_id)})
        deleted = await self._repo.delete_loan(loan_id, user_id)
        if deleted:
            await self._db.commit()
            if self.financial_profile_service:
                await self.financial_profile_service.update_from_loans(user_id)
        return deleted

    async def configure_loan(self, user_id: UUID, loan_config) -> Optional[LoanResponse]:
        """Apply configuration changes (principal, rate, EMI, prepayment) to a loan."""
        loan = await self._repo.get_loan_by_id(loan_config.loan_id, user_id)
        if not loan:
            return None

        if loan_config.new_principal:
            loan.principal_amount = loan_config.new_principal
            loan.outstanding_balance = loan_config.new_principal
        if loan_config.new_interest_rate:
            loan.interest_rate = loan_config.new_interest_rate
        if loan_config.new_emi:
            loan.emi_amount = loan_config.new_emi
        else:
            loan.emi_amount = EMICalculator.calculate_emi(
                loan.principal_amount, loan.interest_rate, loan.loan_term_months
            )
        if loan_config.prepayment_amount:
            loan.outstanding_balance = max(
                Decimal("0"), loan.outstanding_balance - loan_config.prepayment_amount
            )
        if loan_config.effective_date:
            loan.next_due_date = DueDate.calculate_next_due_date(loan_config.effective_date)

        loan.updated_at = utcnow_naive()
        await self._db.commit()
        await self._db.refresh(loan)

        if self.financial_profile_service:
            await self.financial_profile_service.update_from_loans(user_id)

        return await self.to_response(loan)

    # ------------------------------------------------------------------
    # ORM → Schema conversion (shared with payment service via repo)
    # ------------------------------------------------------------------

    async def to_response(self, loan: Loan) -> LoanResponse:
        """Convert a Loan ORM instance to a LoanResponse schema."""
        payments = await self._repo.get_loan_payments(loan.id)
        total_paid = sum(float(p.amount_paid) for p in payments)
        total_interest_paid = sum(float(p.interest_amount) for p in payments)

        return LoanResponse(
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
            total_paid=Decimal(str(total_paid)),
            next_payment_date=(
                loan.next_due_date if loan.status == LoanStatus.ACTIVE.value else None
            ),
            payments_made=len(payments),
            payments_remaining=loan.remaining_months,
            total_interest_paid=Decimal(str(total_interest_paid)),
            created_at=loan.created_at,
            updated_at=loan.updated_at,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _determine_loan_status(self, loan: Loan) -> str:
        """Derive the current status string from loan state."""
        if loan.outstanding_balance <= 0:
            return LoanStatus.PAID_OFF.value
        if loan.next_due_date and loan.next_due_date < date.today():
            days_overdue = (date.today() - loan.next_due_date).days
            return (
                LoanStatus.DEFAULTED.value if days_overdue > 90 else LoanStatus.OVERDUE.value
            )
        return LoanStatus.ACTIVE.value
