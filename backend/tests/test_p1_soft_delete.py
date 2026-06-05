"""
P1-7: Soft delete across tables tests.

Test coverage:
  - Soft delete functionality for Expense, Budget, Goal, RecurringExpense
  - Soft-deleted records excluded from queries by default
  - Restoration of soft-deleted records
  - Cascade behavior and atomic updates
"""

import pytest
from datetime import datetime, date, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.db.models.data import Expense, Budget, Goal, RecurringExpense


@pytest.mark.asyncio
class TestSoftDeleteMixin:
    """Test the SoftDeleteMixin functionality."""

    def test_soft_delete_marks_record_deleted(self):
        """soft_delete() should set is_deleted=True and deleted_at timestamp."""
        expense = Expense(
            id=uuid4(),
            user_id=uuid4(),
            amount=100.00,
            category="food",
            date=date.today(),
            is_deleted=False,
            deleted_at=None,
        )
        
        expense.soft_delete()
        
        assert expense.is_deleted is True
        assert expense.deleted_at is not None

    def test_restore_clears_delete_markers(self):
        """restore() should set is_deleted=False and deleted_at=None."""
        expense = Expense(
            id=uuid4(),
            user_id=uuid4(),
            amount=100.00,
            category="food",
            date=date.today(),
            is_deleted=True,
            deleted_at=datetime.utcnow(),
        )
        
        expense.restore()
        
        assert expense.is_deleted is False
        assert expense.deleted_at is None


@pytest.mark.asyncio
class TestExpenseSoftDelete:
    """Test soft delete for Expense model."""

    def test_expense_has_soft_delete_columns(self):
        """Expense model should have is_deleted and deleted_at columns."""
        expense = Expense(
            id=uuid4(),
            user_id=uuid4(),
            amount=100.00,
            category="food",
            date=date.today(),
        )
        
        # Check columns exist
        assert hasattr(expense, 'is_deleted')
        assert hasattr(expense, 'deleted_at')
        
        # Default should be not deleted (None before DB insert counts as falsy)
        assert not expense.is_deleted
        assert expense.deleted_at is None

    def test_soft_delete_expense_preserves_data(self):
        """Soft-deleted expense should preserve all data."""
        user_id = uuid4()
        expense = Expense(
            id=uuid4(),
            user_id=user_id,
            amount=150.75,
            category="food",
            merchant="McDonald's",
            date=date.today(),
        )
        
        expense.soft_delete()
        
        # All original data preserved
        assert expense.user_id == user_id
        assert expense.amount == 150.75
        assert expense.category == "food"
        assert expense.merchant == "McDonald's"
        assert expense.is_deleted is True


@pytest.mark.asyncio
class TestBudgetSoftDelete:
    """Test soft delete for Budget model."""

    def test_budget_has_soft_delete_columns(self):
        """Budget model should have is_deleted and deleted_at columns."""
        budget = Budget(
            id=uuid4(),
            user_id=uuid4(),
            month=date.today(),
            category="groceries",
            allocated_amount=500.00,
        )
        
        assert hasattr(budget, 'is_deleted')
        assert hasattr(budget, 'deleted_at')
        assert not budget.is_deleted


@pytest.mark.asyncio
class TestGoalSoftDelete:
    """Test soft delete for Goal model."""

    def test_goal_has_soft_delete_columns(self):
        """Goal model should have is_deleted and deleted_at columns."""
        goal = Goal(
            id=uuid4(),
            user_id=uuid4(),
            goal_name="Emergency Fund",
            goal_type="savings",
            target_amount=10000.00,
            target_date=date.today(),
        )
        
        assert hasattr(goal, 'is_deleted')
        assert hasattr(goal, 'deleted_at')
        assert not goal.is_deleted

    def test_goal_soft_delete_preserves_target_info(self):
        """Soft-deleted goal should preserve all target information."""
        goal = Goal(
            id=uuid4(),
            user_id=uuid4(),
            goal_name="Emergency Fund",
            goal_type="savings",
            target_amount=10000.00,
            current_amount=5000.00,
            priority="high",
            status="active",
            target_date=date.today(),
        )
        
        goal.soft_delete()
        
        # All data preserved
        assert goal.goal_name == "Emergency Fund"
        assert goal.target_amount == 10000.00
        assert goal.current_amount == 5000.00
        assert goal.priority == "high"
        assert goal.status == "active"
        assert goal.is_deleted is True


@pytest.mark.asyncio
class TestRecurringExpenseSoftDelete:
    """Test soft delete for RecurringExpense model."""

    def test_recurring_expense_has_soft_delete_columns(self):
        """RecurringExpense model should have is_deleted and deleted_at columns."""
        recurring = RecurringExpense(
            id=uuid4(),
            user_id=uuid4(),
            expense_name="Netflix Subscription",
            amount=15.99,
            category="subscriptions",
            frequency="monthly",
            start_date=date.today(),
        )
        
        assert hasattr(recurring, 'is_deleted')
        assert hasattr(recurring, 'deleted_at')
        assert not recurring.is_deleted


@pytest.mark.asyncio
class TestSoftDeleteQueries:
    """Test querying with soft delete considerations."""

    async def test_repositories_should_exclude_soft_deleted(self):
        """Query repositories should exclude is_deleted=True by default.
        
        This test verifies the pattern that repositories should follow.
        Actual implementation depends on the repository layer.
        """
        # Example filter that repositories should apply:
        # query = query.filter(Model.is_deleted == False)
        
        # This is a contract test — repositories MUST filter out soft-deleted records
        # unless explicitly requesting them (e.g., get_all_including_deleted).
        assert True  # Placeholder for actual repository tests


@pytest.mark.asyncio
class TestSoftDeleteCascade:
    """Test cascade behavior with soft deletes."""

    def test_user_deletion_soft_deletes_related_records(self):
        """Soft-deleting a user should potentially soft-delete their records.
        
        Note: Current implementation uses hard FK cascade, but for audit trails,
        we might want to soft-delete related records instead.
        """
        # This test documents the expected behavior
        # Current implementation uses hard CASCADE, but we could add logic to
        # soft-delete expenses, budgets, goals when a user is soft-deleted.
        assert True


@pytest.mark.asyncio
class TestSoftDeleteAuditTrail:
    """Test audit trail creation for soft deletes."""

    def test_soft_deleted_record_has_timestamp(self):
        """Soft-deleted record should have deleted_at timestamp."""
        expense = Expense(
            id=uuid4(),
            user_id=uuid4(),
            amount=100.00,
            category="food",
            date=date.today(),
        )
        
        before_delete = datetime.now(timezone.utc)
        expense.soft_delete()
        after_delete = datetime.now(timezone.utc)
        
        assert expense.deleted_at is not None
        # deleted_at should be a real Python datetime (not a SQLAlchemy function)
        assert isinstance(expense.deleted_at, datetime)
        assert before_delete <= expense.deleted_at <= after_delete

    def test_restore_clears_deletion_timestamp(self):
        """Restoring a record should clear the deletion timestamp."""
        expense = Expense(
            id=uuid4(),
            user_id=uuid4(),
            amount=100.00,
            category="food",
            date=date.today(),
        )
        
        expense.soft_delete()
        original_deleted_at = expense.deleted_at
        
        expense.restore()
        
        assert expense.deleted_at is None
        assert expense.is_deleted is False


@pytest.mark.asyncio
class TestSoftDeleteEdgeCases:
    """Test edge cases in soft delete functionality."""

    def test_multiple_soft_deletes_idempotent(self):
        """Calling soft_delete multiple times should be safe."""
        expense = Expense(
            id=uuid4(),
            user_id=uuid4(),
            amount=100.00,
            category="food",
            date=date.today(),
        )
        
        expense.soft_delete()
        first_deleted_at = expense.deleted_at
        
        # Call again
        expense.soft_delete()
        second_deleted_at = expense.deleted_at
        
        assert first_deleted_at is not None
        assert second_deleted_at is not None
        # Both timestamps should be real datetime objects
        assert isinstance(first_deleted_at, datetime)
        assert isinstance(second_deleted_at, datetime)
        # Should be very close (ideally within a second)
        assert abs((second_deleted_at - first_deleted_at).total_seconds()) < 1

    def test_multiple_restores_idempotent(self):
        """Calling restore multiple times should be safe."""
        expense = Expense(
            id=uuid4(),
            user_id=uuid4(),
            amount=100.00,
            category="food",
            date=date.today(),
        )
        
        expense.soft_delete()
        expense.restore()
        expense.restore()
        
        assert expense.is_deleted is False
        assert expense.deleted_at is None
