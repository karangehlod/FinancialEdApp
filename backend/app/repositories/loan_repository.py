"""
LoanRepository — concrete repository for Loan and LoanPayment persistence.

Responsibilities (SRP):
  - All SQLAlchemy query construction for Loan / LoanPayment models.
  - Session lifecycle delegation (the session is injected; repository does
    NOT commit — the service layer owns the transaction boundary).

Implements ILoanRepository (DIP) so LoanService depends on the
abstraction, not on SQLAlchemy directly.  Swap this implementation in
tests by providing a mock that satisfies ILoanRepository.
"""

import uuid
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.data import Loan, LoanPayment
from app.repositories.interfaces import ILoanRepository
from app.schemas.loan import LoanCreate, LoanUpdate, LoanPaymentCreate

logger = logging.getLogger(__name__)


class LoanRepository(ILoanRepository):
    """
    SQLAlchemy-backed implementation of ILoanRepository.

    All methods are ``async`` and use the injected ``AsyncSession``.
    The session is **not** committed here — callers own the transaction.
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Args:
            db: An open async SQLAlchemy session (injected per-request).
        """
        self._db = db

    # ------------------------------------------------------------------
    # Loan CRUD
    # ------------------------------------------------------------------

    async def create_loan(self, user_id: UUID, loan_data: LoanCreate) -> Loan:
        """Persist a new Loan row and flush (but do not commit)."""
        loan = Loan(
            id=uuid.uuid4(),
            user_id=user_id,
            loan_type=loan_data.loan_type.value,
            lender_name=loan_data.lender_name,
            principal_amount=loan_data.principal_amount,
            outstanding_balance=loan_data.principal_amount,
            interest_rate=loan_data.interest_rate,
            emi_amount=loan_data.emi_amount,
            loan_term_months=loan_data.loan_term_months,
            remaining_months=loan_data.loan_term_months,
            start_date=loan_data.start_date,
            next_due_date=loan_data.start_date,   # Caller sets the actual next_due_date
            status="active",
            description=loan_data.description,
        )
        self._db.add(loan)
        await self._db.flush()
        await self._db.refresh(loan)
        logger.debug("LoanRepository.create_loan: created loan %s for user %s", loan.id, user_id)
        return loan

    async def get_loan_by_id(self, loan_id: UUID, user_id: UUID) -> Optional[Loan]:
        """Return a Loan row owned by user_id, or None."""
        result = await self._db.execute(
            select(Loan).where(
                and_(Loan.id == loan_id, Loan.user_id == user_id)
            )
        )
        return result.scalars().first()

    async def get_loans_by_user(
        self,
        user_id: UUID,
        status: Optional[str] = None,
    ) -> List[Loan]:
        """Return all loans for a user ordered by creation date descending."""
        query = (
            select(Loan)
            .where(Loan.user_id == user_id)
            .order_by(desc(Loan.created_at))
        )
        if status:
            query = query.where(Loan.status == status)

        result = await self._db.execute(query)
        return list(result.scalars().all())

    async def update_loan(
        self,
        loan_id: UUID,
        user_id: UUID,
        loan_data: LoanUpdate,
    ) -> Optional[Loan]:
        """Apply partial field updates to a Loan.  Returns None if not found."""
        loan = await self.get_loan_by_id(loan_id, user_id)
        if not loan:
            return None

        update_fields = loan_data.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            setattr(loan, field, value)

        loan.updated_at = datetime.now(timezone.utc)
        await self._db.flush()
        await self._db.refresh(loan)
        logger.debug("LoanRepository.update_loan: updated loan %s", loan_id)
        return loan

    async def delete_loan(self, loan_id: UUID, user_id: UUID) -> bool:
        """Delete a Loan row.  Returns True if deleted, False if not found."""
        loan = await self.get_loan_by_id(loan_id, user_id)
        if not loan:
            return False
        await self._db.delete(loan)
        await self._db.flush()
        logger.debug("LoanRepository.delete_loan: deleted loan %s", loan_id)
        return True

    # ------------------------------------------------------------------
    # Payment operations
    # ------------------------------------------------------------------

    async def get_loan_payments(self, loan_id: UUID) -> List[LoanPayment]:
        """Return all payments for a loan ordered by payment_date ascending."""
        result = await self._db.execute(
            select(LoanPayment)
            .where(LoanPayment.loan_id == loan_id)
            .order_by(LoanPayment.payment_date)
        )
        return list(result.scalars().all())

    async def create_payment(
        self,
        loan_id: UUID,
        user_id: UUID,
        payment_data: LoanPaymentCreate,
        principal_amount: float,
        interest_amount: float,
        outstanding_balance: float,
    ) -> LoanPayment:
        """Persist a new LoanPayment and flush (caller commits)."""
        payment = LoanPayment(
            id=uuid.uuid4(),
            loan_id=loan_id,
            user_id=user_id,
            payment_date=payment_data.payment_date,
            amount_paid=payment_data.amount_paid,
            principal_amount=Decimal(str(principal_amount)),
            interest_amount=Decimal(str(interest_amount)),
            outstanding_balance=Decimal(str(outstanding_balance)),
            is_prepayment=payment_data.is_prepayment,
            notes=payment_data.notes,
        )
        self._db.add(payment)
        await self._db.flush()
        await self._db.refresh(payment)
        logger.debug(
            "LoanRepository.create_payment: created payment %s for loan %s",
            payment.id, loan_id,
        )
        return payment

    # ------------------------------------------------------------------
    # Scheduled / background query helpers
    # ------------------------------------------------------------------

    async def get_loans_due_soon(self, days_ahead: int = 7) -> List[Loan]:
        """Return active loans whose next_due_date falls within days_ahead days."""
        today = date.today()
        cutoff = date.fromordinal(today.toordinal() + days_ahead)
        result = await self._db.execute(
            select(Loan).where(
                and_(
                    Loan.status == "active",
                    Loan.next_due_date >= today,
                    Loan.next_due_date <= cutoff,
                )
            )
        )
        return list(result.scalars().all())

    async def get_overdue_loans(self) -> List[Loan]:
        """Return active loans whose next_due_date is in the past."""
        today = date.today()
        result = await self._db.execute(
            select(Loan).where(
                and_(
                    Loan.status == "active",
                    Loan.next_due_date < today,
                )
            )
        )
        return list(result.scalars().all())
