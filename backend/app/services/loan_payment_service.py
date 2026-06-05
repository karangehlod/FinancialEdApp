"""
Loan payment service — handles payment recording and loan status updates.

SOLID compliance:
  - SRP: Only responsible for recording payments and updating loan balances/status.
  - DIP: Depends on ILoanRepository abstraction, not SQLAlchemy directly.
  - OCP: Payment strategies (e.g. partial payment, prepayment) can be added
         without modifying this class.

Inherits BaseService for structured logging and standardised error handling.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.datetime_utils import utcnow_naive

from app.core.exceptions import DatabaseError
from app.core.transaction_decorators import transactional, with_deadlock_recovery
from app.db.models.data import LoanPayment
from app.repositories.interfaces import ILoanRepository
from app.repositories.loan_repository import LoanRepository
from app.schemas.loan import (
    LoanPaymentCreate,
    LoanPaymentResponse,
    LoanStatus,
    PaymentStatus,
)
from app.services.base_service import BaseService
from app.services.loan_domain import DueDate


class LoanPaymentService(BaseService):
    """
    Handles payment recording and loan balance/status updates.

    Responsibilities:
        - Record a payment against a loan.
        - Update loan outstanding balance, remaining months, next due date.
        - Close a loan when balance reaches zero.
        - Return payment history for a loan.

    Constructor args:
        db:              AsyncSession for commit/refresh and default repo construction.
        loan_repository: ILoanRepository — injected for all DB access.
    """

    def __init__(
        self,
        db: AsyncSession,
        loan_repository: Optional[ILoanRepository] = None,
    ) -> None:
        super().__init__()
        self._repo: ILoanRepository = loan_repository or LoanRepository(db)
        self._db = db

    async def validate_dependencies(self) -> bool:
        """Validate that all required dependencies are available."""
        if not self._repo:
            raise DatabaseError("LoanRepository not initialised")
        return True

    # ------------------------------------------------------------------
    # Payment operations
    # ------------------------------------------------------------------

    @transactional(rollback_on_error=True)
    @with_deadlock_recovery(max_attempts=3)
    async def make_payment(
        self,
        user_id: UUID,
        loan_id: UUID,
        payment_data: LoanPaymentCreate,
    ) -> Optional[LoanPaymentResponse]:
        """
        Record a payment, split into principal/interest portions, update loan state.

        Returns None if the loan is not found or is not ACTIVE.
        """
        self.log_operation("make_payment", {"loan_id": str(loan_id)})
        try:
            loan = await self._repo.get_loan_by_id(loan_id, user_id)
            if not loan or loan.status != LoanStatus.ACTIVE.value:
                return None

            monthly_rate = float(loan.interest_rate) / 12 / 100
            interest_portion = float(loan.outstanding_balance) * monthly_rate
            principal_portion = max(0.0, float(payment_data.amount) - interest_portion)
            new_balance = max(0.0, float(loan.outstanding_balance) - principal_portion)

            db_payment = await self._repo.create_payment(
                loan_id=loan_id,
                user_id=user_id,
                payment_data=payment_data,
                principal_amount=principal_portion,
                interest_amount=interest_portion,
                outstanding_balance=new_balance,
            )

            # Update loan state
            loan.outstanding_balance = Decimal(str(new_balance))
            if new_balance == 0:
                loan.status = LoanStatus.CLOSED.value
                loan.remaining_months = 0
            else:
                loan.remaining_months = max(0, loan.remaining_months - 1)
                loan.next_due_date = DueDate.calculate_next_due_date(
                    payment_data.payment_date
                )
            loan.updated_at = utcnow_naive()

            await self._db.commit()
            await self._db.refresh(db_payment)
            return self._payment_to_response(db_payment)
        except Exception as exc:
            self.log_error("make_payment", exc, {"loan_id": str(loan_id)})
            raise

    async def get_loan_payments(
        self, user_id: UUID, loan_id: UUID
    ) -> List[LoanPaymentResponse]:
        """Return all payments belonging to *user_id* for a given loan."""
        all_payments = await self._repo.get_loan_payments(loan_id)
        # Guard: only return records owned by the requesting user
        user_payments = [p for p in all_payments if p.user_id == user_id]
        return [self._payment_to_response(p) for p in user_payments]

    # ------------------------------------------------------------------
    # ORM → Schema conversion
    # ------------------------------------------------------------------

    def _payment_to_response(self, payment: LoanPayment) -> LoanPaymentResponse:
        """Convert a LoanPayment ORM instance to LoanPaymentResponse schema."""
        return LoanPaymentResponse(
            id=payment.id,
            loan_id=payment.loan_id,
            user_id=payment.user_id,
            amount=payment.amount_paid,
            payment_date=payment.payment_date,
            payment_method=None,
            notes=payment.notes,
            status=PaymentStatus.PAID.value,
            principal_portion=payment.principal_amount,
            interest_portion=payment.interest_amount,
            remaining_balance=payment.outstanding_balance,
            created_at=payment.created_at,
        )
