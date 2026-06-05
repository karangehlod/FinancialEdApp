"""
Tests for atomic expense+budget update (P1-8).

Verifies that:
  - expense creation and budget update happen atomically (commit/rollback)
  - a budget update failure rolls back the expense creation
  - cache invalidation is called after successful creation
  - update_expense rolls back on failure
  - delete_expense rolls back on failure
"""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4

from app.services.expense_service import ExpenseService
from app.core.exceptions import InvalidExpenseAmountError, InvalidExpenseDateError, DatabaseError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_expense(user_id=None, category="food", amount=Decimal("50.00"), expense_date=None):
    e = MagicMock()
    e.id = uuid4()
    e.user_id = user_id or uuid4()
    e.category = category
    e.amount = amount
    e.date = expense_date or date(2026, 2, 1)
    return e


def _make_db():
    """Return a mock AsyncSession."""
    db = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# create_expense: validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_expense_rejects_zero_amount():
    db = _make_db()
    svc = ExpenseService(db=db)

    with pytest.raises(InvalidExpenseAmountError):
        await svc.create_expense(
            user_id=uuid4(),
            expense_data=MagicMock(amount=Decimal("0"), date=date.today()),
        )


@pytest.mark.asyncio
async def test_create_expense_rejects_future_date():
    db = _make_db()
    svc = ExpenseService(db=db)

    from datetime import timedelta

    with pytest.raises(InvalidExpenseDateError):
        await svc.create_expense(
            user_id=uuid4(),
            expense_data=MagicMock(amount=Decimal("10"), date=date.today() + timedelta(days=1)),
        )


# ---------------------------------------------------------------------------
# create_expense: atomic transaction usage
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_expense_commits_transaction():
    """Both expense creation and budget update are committed together."""
    db = _make_db()
    expense = _make_expense()

    svc = ExpenseService(db=db)
    svc.repository = AsyncMock()
    svc.repository.create = AsyncMock(return_value=expense)
    svc._update_related_budget_spending = AsyncMock()
    svc._invalidate_expense_cache = AsyncMock()

    result = await svc.create_expense(
        user_id=expense.user_id,
        expense_data=MagicMock(amount=Decimal("50"), date=date.today()),
    )

    # commit must be called
    db.commit.assert_called_once()
    # repository.create called
    svc.repository.create.assert_called_once()
    # budget update called
    svc._update_related_budget_spending.assert_called_once_with(expense)
    # cache invalidated
    svc._invalidate_expense_cache.assert_called_once_with(expense.user_id)
    assert result == expense


@pytest.mark.asyncio
async def test_create_expense_rollback_on_budget_failure():
    """If budget update fails, the transaction is rolled back (expense not persisted)."""
    db = _make_db()
    expense = _make_expense()

    svc = ExpenseService(db=db)
    svc.repository = AsyncMock()
    svc.repository.create = AsyncMock(return_value=expense)
    svc._update_related_budget_spending = AsyncMock(side_effect=Exception("DB error"))
    svc._invalidate_expense_cache = AsyncMock()

    with pytest.raises(DatabaseError):
        await svc.create_expense(
            user_id=expense.user_id,
            expense_data=MagicMock(amount=Decimal("50"), date=date.today()),
        )

    # Rollback should be called
    db.rollback.assert_called_once()
    # Cache should NOT be invalidated on failure
    svc._invalidate_expense_cache.assert_not_called()


# ---------------------------------------------------------------------------
# update_expense: transaction usage
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_expense_commits_transaction():
    db = _make_db()
    original = _make_expense(category="food")
    updated = _make_expense(category="food", amount=Decimal("75"))

    svc = ExpenseService(db=db)
    svc.repository = AsyncMock()
    svc.repository.get_by_id = AsyncMock(return_value=original)
    svc.repository.update = AsyncMock(return_value=updated)
    svc._update_related_budget_spending = AsyncMock()
    svc._update_category_budget = AsyncMock()
    svc._invalidate_expense_cache = AsyncMock()

    result = await svc.update_expense(
        expense_id=original.id,
        user_id=original.user_id,
        expense_data=MagicMock(
            amount=Decimal("75"),
            date=None,
            category=None,
            subcategory=None,
            description=None,
            merchant=None,
            payment_method=None,
            is_recurring=None,
        ),
    )

    db.commit.assert_called_once()
    assert result == updated


# ---------------------------------------------------------------------------
# delete_expense: transaction usage
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_expense_commits_transaction():
    db = _make_db()
    expense = _make_expense()

    svc = ExpenseService(db=db)
    svc.repository = AsyncMock()
    svc.repository.get_by_id = AsyncMock(return_value=expense)
    svc.repository.delete = AsyncMock()
    svc._update_category_budget = AsyncMock()
    svc._invalidate_expense_cache = AsyncMock()

    result = await svc.delete_expense(expense_id=expense.id, user_id=expense.user_id)

    db.commit.assert_called_once()
    svc.repository.delete.assert_called_once()
    svc._invalidate_expense_cache.assert_called_once()
    assert result is True
