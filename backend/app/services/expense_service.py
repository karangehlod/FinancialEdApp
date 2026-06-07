"""Service for expense CRUD and business logic operations."""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import date
from decimal import Decimal
from calendar import monthrange

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, text

from app.db.models.data import Expense, Budget, BudgetAlert
from app.schemas.expense import ExpenseCreate, ExpenseUpdate, ExpenseFilter
from app.core.exceptions import (
    ExpenseNotFoundError,
    InvalidExpenseAmountError,
    InvalidExpenseDateError,
    DatabaseError
)
from app.core.logging import get_logger
from app.repositories.expense_repository import ExpenseRepository

logger = get_logger(__name__)


class ExpenseService:
    """
    Service for expense CRUD and business logic operations.

    Responsibilities:
    - CRUD operations for expenses
    - Business logic (validation, budget updates)
    - Coordination between repositories and other services
    - Cache invalidation on every mutating operation (P0-9)

    Uses the Repository Pattern for data access abstraction.
    Instance-based design supports dependency injection and testing.
    """

    def __init__(self, db: AsyncSession, cache_service=None):
        """
        Initialize ExpenseService.

        Args:
            db:            Async SQLAlchemy session.
            cache_service: Optional CacheService for Redis invalidation.
        """
        self.db = db
        self.repository = ExpenseRepository(db)
        self._cache = cache_service  # May be None or NullCacheService

    # ============== INSTANCE METHODS ==============

    async def create_expense(
        self,
        user_id: UUID,
        expense_data: ExpenseCreate,
    ) -> Expense:
        """
        Create a new expense and update the related budget atomically.

        Validation → repository INSERT + flush → budget recalc → commit.
        The repository handles commit/rollback within the session's autobegin
        transaction, so a failure at any step rolls everything back.
        """
        if expense_data.amount <= 0:
            raise InvalidExpenseAmountError("Amount must be greater than 0")
        if expense_data.date > date.today():
            raise InvalidExpenseDateError("Expense date cannot be in the future")

        try:
            new_expense = await self.repository.create(user_id, expense_data)
            await self._update_related_budget_spending(new_expense)
            # Commit the budget update (expense already committed by repository)
            await self.db.commit()
        except (InvalidExpenseAmountError, InvalidExpenseDateError):
            raise
        except Exception as exc:
            await self.db.rollback()
            logger.error(f"Expense creation failed: {exc}", exc_info=True)
            raise DatabaseError(f"Failed to create expense: {exc}") from exc

        # Cache invalidation is non-fatal — happens outside the transaction
        await self._invalidate_expense_cache(user_id)
        logger.info(f"Expense created successfully for user {user_id}")
        return new_expense

    async def get_expense(self, expense_id: UUID, user_id: UUID) -> Optional[Expense]:
        """Get a specific expense by ID."""
        return await self.repository.get_by_id(expense_id, user_id)

    async def get_user_expenses(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
        filters: Optional[ExpenseFilter] = None,
    ) -> tuple[List[Expense], int]:
        """Get all expenses for a user with optional filtering."""
        return await self.repository.get_by_user(user_id, skip, limit, filters)

    async def update_expense(
        self,
        expense_id: UUID,
        user_id: UUID,
        expense_data: ExpenseUpdate,
    ) -> Expense:
        """Update an expense with validation, atomic budget recalculation, and cache invalidation."""
        if expense_data.amount is not None:
            if expense_data.amount <= 0:
                raise InvalidExpenseAmountError("Amount must be greater than 0")
            expense_data.amount = Decimal(str(expense_data.amount)).quantize(Decimal("0.01"))

        if expense_data.date is not None:
            if expense_data.date > date.today():
                raise InvalidExpenseDateError("Expense date cannot be in the future")

        if expense_data.category is not None:
            valid_categories = [
                "food", "transport", "utilities", "entertainment",
                "health", "education", "shopping", "other",
            ]
            if expense_data.category.lower() not in valid_categories:
                raise ValueError(f"Invalid category: {expense_data.category}")

        try:
            current = await self.repository.get_by_id(expense_id, user_id)
            updated = await self.repository.update(expense_id, user_id, expense_data)

            # Recalculate budgets if cost-related fields changed
            if (
                current.category != updated.category
                or current.amount != updated.amount
                or current.date != updated.date
            ):
                await self._update_related_budget_spending(updated)
                if current.category != updated.category:
                    # Also recalculate the old category's budget
                    await self._update_category_budget(
                        current.user_id, current.category, current.date
                    )
                await self.db.commit()
        except (InvalidExpenseAmountError, InvalidExpenseDateError, ValueError):
            raise
        except Exception as exc:
            await self.db.rollback()
            logger.error(f"Expense update failed: {exc}", exc_info=True)
            raise DatabaseError(f"Failed to update expense: {exc}") from exc

        await self._invalidate_expense_cache(user_id)
        return updated

    async def delete_expense(self, expense_id: UUID, user_id: UUID) -> bool:
        """Delete an expense, recalculate budgets, and invalidate cache."""
        try:
            expense = await self.repository.get_by_id(expense_id, user_id)
            await self.repository.delete(expense_id, user_id)
            await self._update_category_budget(expense.user_id, expense.category, expense.date)
            await self.db.commit()
        except Exception as exc:
            await self.db.rollback()
            logger.error(f"Expense delete failed: {exc}", exc_info=True)
            raise DatabaseError(f"Failed to delete expense: {exc}") from exc

        await self._invalidate_expense_cache(user_id)
        logger.info(f"Expense {expense_id} deleted for user {user_id}")
        return True

    async def get_expense_summary(
        self,
        user_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get expense summary for a period."""
        return await self.repository.get_summary(user_id, start_date, end_date, category)

    # ============== CACHE HELPERS ==============

    async def _invalidate_expense_cache(self, user_id: UUID) -> None:
        """Invalidate all cached expense data for this user."""
        if self._cache is None:
            return
        try:
            await self._cache.invalidate_user_expenses(str(user_id))
            # Budget summaries are affected by expense changes too
            await self._cache.invalidate_user_budgets(str(user_id))
        except Exception as exc:
            logger.warning(f"Cache invalidation failed (non-fatal): {exc}")

    # ============== PRIVATE HELPER METHODS ==============

    async def _update_related_budget_spending(self, expense: Expense) -> None:
        """
        Recalculate and update budget.spent_amount for the expense's category/month.

        Called inside a savepoint (create_expense) or standalone (update_expense,
        delete_expense). Does NOT call self.db.commit() — the caller manages
        the transaction boundary.
        """
        expense_month = expense.date.replace(day=1)
        result = await self.db.execute(
            select(Budget).where(
                and_(
                    Budget.user_id == expense.user_id,
                    Budget.category == expense.category,
                    Budget.month == expense_month,
                )
            )
        )
        budget = result.scalar_one_or_none()
        if not budget:
            return

        year = expense_month.year
        month = expense_month.month
        _, last_day = monthrange(year, month)

        result = await self.db.execute(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                and_(
                    Expense.user_id == expense.user_id,
                    Expense.category == expense.category,
                    Expense.date >= expense_month,
                    Expense.date <= expense_month.replace(day=last_day),
                )
            )
        )
        total_spent = result.scalar() or Decimal("0")
        budget.spent_amount = total_spent

        # Evaluate alerts — still inside the same transaction
        await self._check_budget_alert(budget, expense.user_id, total_spent)

    async def _update_category_budget(self, user_id: UUID, category: str, expense_date: date) -> None:
        """Recalculate spent_amount for a category budget (standalone, caller commits)."""
        expense_month = expense_date.replace(day=1)
        result = await self.db.execute(
            select(Budget).where(
                and_(
                    Budget.user_id == user_id,
                    Budget.category == category,
                    Budget.month == expense_month,
                )
            )
        )
        budget = result.scalar_one_or_none()
        if not budget:
            return

        year = expense_month.year
        month = expense_month.month
        _, last_day = monthrange(year, month)

        result = await self.db.execute(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                and_(
                    Expense.user_id == user_id,
                    Expense.category == category,
                    Expense.date >= expense_month,
                    Expense.date <= expense_month.replace(day=last_day),
                )
            )
        )
        total_spent = result.scalar() or Decimal("0")
        budget.spent_amount = total_spent
        # No commit here — caller is responsible for transaction management

    async def _check_budget_alert(self, budget: Budget, user_id: UUID, total_spent: Decimal) -> None:
        """Check and create budget alert if needed."""
        if budget.allocated_amount and budget.allocated_amount > 0:
            utilization = (total_spent / budget.allocated_amount) * 100
            if utilization >= 90:
                existing = await self.db.execute(
                    select(BudgetAlert).where(
                        and_(
                            BudgetAlert.budget_id == budget.id,
                            BudgetAlert.alert_level == "HIGH",
                            ~BudgetAlert.is_read,
                        )
                    )
                )
                if not existing.scalar_one_or_none():
                    alert = BudgetAlert(
                        budget_id=budget.id,
                        user_id=user_id,
                        alert_level="HIGH",
                        message=f"You've spent {utilization:.1f}% of your {budget.category} budget",
                        utilization_at_alert=utilization,
                        is_read=False,
                    )
                    self.db.add(alert)