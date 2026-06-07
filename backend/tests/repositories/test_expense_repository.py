"""Tests for expense_repository.py - comprehensive branch and code coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

from app.repositories.expense_repository import ExpenseRepository
from app.schemas.expense import ExpenseCreate, ExpenseUpdate, ExpenseFilter
from app.db.models.data import Expense
from app.core.exceptions import ExpenseNotFoundError, DatabaseError


# ============== FIXTURES ==============

@pytest.fixture
def mock_db():
    """Create a mock AsyncSession."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def user_id():
    """Generate a test user ID."""
    return uuid4()


@pytest.fixture
def expense_id():
    """Generate a test expense ID."""
    return uuid4()


@pytest.fixture
def expense_repo(mock_db):
    """Create an ExpenseRepository with mocked database."""
    return ExpenseRepository(mock_db)


@pytest.fixture
def sample_expense(user_id, expense_id):
    """Create a sample Expense object."""
    return Expense(
        id=expense_id,
        user_id=user_id,
        amount=Decimal("50.00"),
        category="Food",
        subcategory="Groceries",
        description="Weekly groceries",
        date=date(2026, 1, 15),
        merchant="Whole Foods",
        payment_method="credit_card",
        is_recurring=False
    )


# ============== TESTS FOR ExpenseRepository ==============

class TestExpenseRepository:
    """Test ExpenseRepository methods."""
    
    @pytest.mark.asyncio
    async def test_init(self, mock_db):
        """Test ExpenseRepository initialization."""
        repo = ExpenseRepository(mock_db)
        assert repo.db == mock_db
    
    # ============== CREATE TESTS ==============
    
    @pytest.mark.asyncio
    async def test_create_expense_success(self, expense_repo, user_id):
        """Test creating a new expense successfully."""
        expense_data = ExpenseCreate(
            amount=Decimal("50.00"),
            category="Food",
            subcategory="Groceries",
            description="Weekly groceries",
            date=date(2026, 1, 15),
            merchant="Whole Foods",
            payment_method="credit_card",
            is_recurring=False
        )
        
        created_expense = Expense(
            id=uuid4(),
            user_id=user_id,
            **expense_data.model_dump()
        )
        
        expense_repo.db.add = MagicMock()
        expense_repo.db.commit = AsyncMock()
        expense_repo.db.refresh = AsyncMock()
        
        result = await expense_repo.create(user_id, expense_data)
        
        expense_repo.db.add.assert_called_once()
        expense_repo.db.commit.assert_called_once()
        expense_repo.db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_expense_with_recurring_true(self, expense_repo, user_id):
        """Test creating recurring expense."""
        expense_data = ExpenseCreate(
            amount=Decimal("100.00"),
            category="Utilities",
            subcategory="Electric",
            description="Monthly electric bill",
            date=date(2026, 1, 1),
            merchant="Power Company",
            payment_method="bank_transfer",
            is_recurring=True
        )
        
        expense_repo.db.add = MagicMock()
        expense_repo.db.commit = AsyncMock()
        expense_repo.db.refresh = AsyncMock()
        
        await expense_repo.create(user_id, expense_data)
        
        expense_repo.db.add.assert_called_once()
        expense_repo.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_expense_with_all_optional_fields(self, expense_repo, user_id):
        """Test creating expense with all optional fields provided."""
        expense_data = ExpenseCreate(
            amount=Decimal("25.00"),
            category="Entertainment",
            subcategory="Movies",
            description="Movie ticket",
            date=date(2026, 1, 10),
            merchant="AMC",
            payment_method="credit_card",
            is_recurring=False
        )
        
        expense_repo.db.add = MagicMock()
        expense_repo.db.commit = AsyncMock()
        expense_repo.db.refresh = AsyncMock()
        
        await expense_repo.create(user_id, expense_data)
        
        # Verify all fields were added correctly
        call_args = expense_repo.db.add.call_args[0][0]
        assert call_args.amount == Decimal("25.00")
        assert call_args.category == "Entertainment"
        assert call_args.is_recurring is False
    
    @pytest.mark.asyncio
    async def test_create_expense_database_error(self, expense_repo, user_id):
        """Test create raises DatabaseError on database failure."""
        expense_data = ExpenseCreate(
            amount=Decimal("50.00"),
            category="Food",
            subcategory="Groceries",
            description="Weekly groceries",
            date=date(2026, 1, 15),
            merchant="Whole Foods",
            payment_method="credit_card"
        )
        
        expense_repo.db.add = MagicMock(side_effect=Exception("DB Error"))
        expense_repo.db.rollback = AsyncMock()
        
        with pytest.raises(DatabaseError):
            await expense_repo.create(user_id, expense_data)
        
        expense_repo.db.rollback.assert_called_once()
    
    # ============== GET_BY_ID TESTS ==============
    
    @pytest.mark.asyncio
    async def test_get_by_id_success(self, expense_repo, sample_expense, user_id, expense_id):
        """Test retrieving expense by ID successfully."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_expense
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await expense_repo.get_by_id(expense_id, user_id)
        
        assert result == sample_expense
        expense_repo.db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, expense_repo, user_id, expense_id):
        """Test get_by_id raises ExpenseNotFoundError when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        
        with pytest.raises(ExpenseNotFoundError):
            await expense_repo.get_by_id(expense_id, user_id)
    
    @pytest.mark.asyncio
    async def test_get_by_id_wrong_user(self, expense_repo, user_id):
        """Test get_by_id raises ExpenseNotFoundError for wrong user."""
        expense_id = uuid4()
        different_user_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        
        with pytest.raises(ExpenseNotFoundError):
            await expense_repo.get_by_id(expense_id, different_user_id)
    
    @pytest.mark.asyncio
    async def test_get_by_id_database_error(self, expense_repo, user_id, expense_id):
        """Test get_by_id raises DatabaseError on database failure."""
        expense_repo.db.execute = AsyncMock(side_effect=Exception("DB Error"))
        
        with pytest.raises(DatabaseError):
            await expense_repo.get_by_id(expense_id, user_id)
    
    # ============== GET_BY_USER TESTS ==============
    
    @pytest.mark.asyncio
    async def test_get_by_user_all_expenses(self, expense_repo, user_id, sample_expense):
        """Test retrieving all expenses for a user."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_expense]
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        expense_repo.db.scalar = AsyncMock(return_value=1)
        
        expenses, total = await expense_repo.get_by_user(user_id)
        
        assert expenses == [sample_expense]
        assert total == 1
    
    @pytest.mark.asyncio
    async def test_get_by_user_with_pagination(self, expense_repo, user_id, sample_expense):
        """Test get_by_user with skip and limit."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_expense]
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        expense_repo.db.scalar = AsyncMock(return_value=5)
        
        expenses, total = await expense_repo.get_by_user(user_id, skip=10, limit=25)
        
        assert expenses == [sample_expense]
        assert total == 5
    
    @pytest.mark.asyncio
    async def test_get_by_user_no_expenses(self, expense_repo, user_id):
        """Test get_by_user returns empty list when no expenses."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        expense_repo.db.scalar = AsyncMock(return_value=0)
        
        expenses, total = await expense_repo.get_by_user(user_id)
        
        assert expenses == []
        assert total == 0
    
    @pytest.mark.asyncio
    async def test_get_by_user_with_category_filter(self, expense_repo, user_id, sample_expense):
        """Test get_by_user with category filter."""
        filters = ExpenseFilter(category="Food")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_expense]
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        expense_repo.db.scalar = AsyncMock(return_value=1)
        
        expenses, total = await expense_repo.get_by_user(user_id, filters=filters)
        
        assert expenses == [sample_expense]
        assert total == 1
    
    @pytest.mark.asyncio
    async def test_get_by_user_with_date_range_filter(self, expense_repo, user_id, sample_expense):
        """Test get_by_user with date range filter."""
        filters = ExpenseFilter(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31)
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_expense]
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        expense_repo.db.scalar = AsyncMock(return_value=1)
        
        expenses, total = await expense_repo.get_by_user(user_id, filters=filters)
        
        assert expenses == [sample_expense]
    
    @pytest.mark.asyncio
    async def test_get_by_user_with_amount_range_filter(self, expense_repo, user_id, sample_expense):
        """Test get_by_user with min and max amount filter."""
        filters = ExpenseFilter(
            min_amount=Decimal("25.00"),
            max_amount=Decimal("100.00")
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_expense]
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        expense_repo.db.scalar = AsyncMock(return_value=1)
        
        expenses, total = await expense_repo.get_by_user(user_id, filters=filters)
        
        assert expenses == [sample_expense]
    
    @pytest.mark.asyncio
    async def test_get_by_user_with_merchant_filter(self, expense_repo, user_id, sample_expense):
        """Test get_by_user with merchant filter (ILIKE search)."""
        filters = ExpenseFilter(merchant="Whole")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_expense]
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        expense_repo.db.scalar = AsyncMock(return_value=1)
        
        expenses, total = await expense_repo.get_by_user(user_id, filters=filters)
        
        assert expenses == [sample_expense]
    
    @pytest.mark.asyncio
    async def test_get_by_user_with_payment_method_filter(self, expense_repo, user_id, sample_expense):
        """Test get_by_user with payment_method filter."""
        filters = ExpenseFilter(payment_method="credit_card")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_expense]
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        expense_repo.db.scalar = AsyncMock(return_value=1)
        
        expenses, total = await expense_repo.get_by_user(user_id, filters=filters)
        
        assert expenses == [sample_expense]
    
    @pytest.mark.asyncio
    async def test_get_by_user_with_multiple_filters(self, expense_repo, user_id, sample_expense):
        """Test get_by_user with multiple filters combined."""
        filters = ExpenseFilter(
            category="Food",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            min_amount=Decimal("25.00"),
            max_amount=Decimal("100.00"),
            merchant="Whole",
            payment_method="credit_card"
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_expense]
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        expense_repo.db.scalar = AsyncMock(return_value=1)
        
        expenses, total = await expense_repo.get_by_user(user_id, filters=filters)
        
        assert expenses == [sample_expense]
    
    @pytest.mark.asyncio
    async def test_get_by_user_total_count_none(self, expense_repo, user_id):
        """Test get_by_user returns 0 when total count is None."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        expense_repo.db.scalar = AsyncMock(return_value=None)
        
        expenses, total = await expense_repo.get_by_user(user_id)
        
        assert total == 0
    
    @pytest.mark.asyncio
    async def test_get_by_user_database_error(self, expense_repo, user_id):
        """Test get_by_user raises DatabaseError on database failure."""
        expense_repo.db.execute = AsyncMock(side_effect=Exception("DB Error"))
        
        with pytest.raises(DatabaseError):
            await expense_repo.get_by_user(user_id)
    
    # ============== UPDATE TESTS ==============
    
    @pytest.mark.asyncio
    async def test_update_expense_success(self, expense_repo, sample_expense, user_id, expense_id):
        """Test updating an expense successfully."""
        expense_data = ExpenseUpdate(
            amount=Decimal("75.00"),
            category="Dining"
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_expense
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        expense_repo.db.commit = AsyncMock()
        expense_repo.db.refresh = AsyncMock()
        
        result = await expense_repo.update(expense_id, user_id, expense_data)
        
        expense_repo.db.execute.assert_called_once()
        expense_repo.db.commit.assert_called_once()
        expense_repo.db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_expense_partial_fields(self, expense_repo, sample_expense, user_id, expense_id):
        """Test updating only specific fields of an expense."""
        expense_data = ExpenseUpdate(description="Updated groceries")
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_expense
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        expense_repo.db.commit = AsyncMock()
        expense_repo.db.refresh = AsyncMock()
        
        await expense_repo.update(expense_id, user_id, expense_data)
        
        expense_repo.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_expense_not_found(self, expense_repo, user_id, expense_id):
        """Test update raises ExpenseNotFoundError when expense not found."""
        expense_data = ExpenseUpdate(amount=Decimal("100.00"))
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        
        with pytest.raises(ExpenseNotFoundError):
            await expense_repo.update(expense_id, user_id, expense_data)
    
    @pytest.mark.asyncio
    async def test_update_expense_wrong_user(self, expense_repo, user_id):
        """Test update raises ExpenseNotFoundError for wrong user."""
        expense_id = uuid4()
        different_user_id = uuid4()
        expense_data = ExpenseUpdate(amount=Decimal("100.00"))
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        
        with pytest.raises(ExpenseNotFoundError):
            await expense_repo.update(expense_id, different_user_id, expense_data)
    
    @pytest.mark.asyncio
    async def test_update_expense_database_error(self, expense_repo, user_id, expense_id):
        """Test update raises DatabaseError on database failure."""
        expense_data = ExpenseUpdate(amount=Decimal("100.00"))
        expense_repo.db.execute = AsyncMock(side_effect=Exception("DB Error"))
        
        with pytest.raises(DatabaseError):
            await expense_repo.update(expense_id, user_id, expense_data)
    
    # ============== DELETE TESTS ==============
    
    @pytest.mark.asyncio
    async def test_delete_expense_success(self, expense_repo, sample_expense, user_id, expense_id):
        """Test deleting an expense successfully."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_expense
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        expense_repo.db.delete = AsyncMock()
        expense_repo.db.commit = AsyncMock()
        
        result = await expense_repo.delete(expense_id, user_id)
        
        assert result is True
        expense_repo.db.delete.assert_called_once()
        expense_repo.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_expense_not_found(self, expense_repo, user_id, expense_id):
        """Test delete raises ExpenseNotFoundError when expense not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        
        with pytest.raises(ExpenseNotFoundError):
            await expense_repo.delete(expense_id, user_id)
    
    @pytest.mark.asyncio
    async def test_delete_expense_wrong_user(self, expense_repo, user_id):
        """Test delete raises ExpenseNotFoundError for wrong user."""
        expense_id = uuid4()
        different_user_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        
        with pytest.raises(ExpenseNotFoundError):
            await expense_repo.delete(expense_id, different_user_id)
    
    @pytest.mark.asyncio
    async def test_delete_expense_database_error(self, expense_repo, user_id, expense_id):
        """Test delete raises DatabaseError on database failure."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        expense_repo.db.delete = AsyncMock(side_effect=Exception("DB Error"))
        expense_repo.db.rollback = AsyncMock()
        
        with pytest.raises(DatabaseError):
            await expense_repo.delete(expense_id, user_id)
        
        expense_repo.db.rollback.assert_called_once()
    
    # ============== GET_SUMMARY TESTS ==============
    
    @pytest.mark.asyncio
    async def test_get_summary_with_default_dates(self, expense_repo, user_id):
        """Test get_summary with default dates (current month)."""
        mock_result = MagicMock()
        mock_result.one.return_value = MagicMock(total=Decimal("500.00"), count=10)
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await expense_repo.get_summary(user_id)
        
        assert result["total_amount"] == Decimal("500.00")
        assert result["count"] == 10
        assert "start_date" in result
        assert "end_date" in result
    
    @pytest.mark.asyncio
    async def test_get_summary_with_custom_dates(self, expense_repo, user_id):
        """Test get_summary with custom date range."""
        mock_result = MagicMock()
        mock_result.one.return_value = MagicMock(total=Decimal("250.00"), count=5)
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        
        start = date(2026, 1, 1)
        end = date(2026, 1, 15)
        
        result = await expense_repo.get_summary(user_id, start_date=start, end_date=end)
        
        assert result["total_amount"] == Decimal("250.00")
        assert result["count"] == 5
        assert result["start_date"] == start
        assert result["end_date"] == end
    
    @pytest.mark.asyncio
    async def test_get_summary_with_category_filter(self, expense_repo, user_id):
        """Test get_summary filtered by category."""
        mock_result = MagicMock()
        mock_result.one.return_value = MagicMock(total=Decimal("100.00"), count=3)
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await expense_repo.get_summary(user_id, category="Food")
        
        assert result["total_amount"] == Decimal("100.00")
        assert result["count"] == 3
    
    @pytest.mark.asyncio
    async def test_get_summary_no_expenses(self, expense_repo, user_id):
        """Test get_summary returns zero when no expenses found."""
        mock_result = MagicMock()
        mock_result.one.return_value = MagicMock(total=None, count=None)
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await expense_repo.get_summary(user_id)
        
        assert result["total_amount"] == Decimal(0)
        assert result["count"] == 0
    
    @pytest.mark.asyncio
    async def test_get_summary_database_error(self, expense_repo, user_id):
        """Test get_summary raises DatabaseError on database failure."""
        expense_repo.db.execute = AsyncMock(side_effect=Exception("DB Error"))
        
        with pytest.raises(DatabaseError):
            await expense_repo.get_summary(user_id)
    
    # ============== GET_BY_DATE_RANGE TESTS ==============
    
    @pytest.mark.asyncio
    async def test_get_by_date_range_success(self, expense_repo, user_id, sample_expense):
        """Test retrieving expenses within date range."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_expense]
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        
        start = date(2026, 1, 1)
        end = date(2026, 1, 31)
        
        expenses = await expense_repo.get_by_date_range(user_id, start, end)
        
        assert expenses == [sample_expense]
    
    @pytest.mark.asyncio
    async def test_get_by_date_range_no_expenses(self, expense_repo, user_id):
        """Test get_by_date_range returns empty list when no expenses."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        
        start = date(2026, 1, 1)
        end = date(2026, 1, 10)
        
        expenses = await expense_repo.get_by_date_range(user_id, start, end)
        
        assert expenses == []
    
    @pytest.mark.asyncio
    async def test_get_by_date_range_database_error(self, expense_repo, user_id):
        """Test get_by_date_range raises DatabaseError on database failure."""
        expense_repo.db.execute = AsyncMock(side_effect=Exception("DB Error"))
        
        with pytest.raises(DatabaseError):
            await expense_repo.get_by_date_range(user_id, date(2026, 1, 1), date(2026, 1, 31))
    
    # ============== GET_BY_CATEGORY TESTS ==============
    
    @pytest.mark.asyncio
    async def test_get_by_category_success(self, expense_repo, user_id, sample_expense):
        """Test retrieving expenses by category."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_expense]
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        
        expenses = await expense_repo.get_by_category(user_id, "Food")
        
        assert expenses == [sample_expense]
    
    @pytest.mark.asyncio
    async def test_get_by_category_with_date_range(self, expense_repo, user_id, sample_expense):
        """Test get_by_category with date range filters."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_expense]
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        
        expenses = await expense_repo.get_by_category(
            user_id,
            "Food",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31)
        )
        
        assert expenses == [sample_expense]
    
    @pytest.mark.asyncio
    async def test_get_by_category_with_start_date_only(self, expense_repo, user_id, sample_expense):
        """Test get_by_category with only start_date filter."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_expense]
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        
        expenses = await expense_repo.get_by_category(
            user_id,
            "Food",
            start_date=date(2026, 1, 1)
        )
        
        assert expenses == [sample_expense]
    
    @pytest.mark.asyncio
    async def test_get_by_category_with_end_date_only(self, expense_repo, user_id, sample_expense):
        """Test get_by_category with only end_date filter."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_expense]
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        
        expenses = await expense_repo.get_by_category(
            user_id,
            "Food",
            end_date=date(2026, 1, 31)
        )
        
        assert expenses == [sample_expense]
    
    @pytest.mark.asyncio
    async def test_get_by_category_no_expenses(self, expense_repo, user_id):
        """Test get_by_category returns empty list when no expenses."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        expense_repo.db.execute = AsyncMock(return_value=mock_result)
        
        expenses = await expense_repo.get_by_category(user_id, "Transport")
        
        assert expenses == []
    
    @pytest.mark.asyncio
    async def test_get_by_category_database_error(self, expense_repo, user_id):
        """Test get_by_category raises DatabaseError on database failure."""
        expense_repo.db.execute = AsyncMock(side_effect=Exception("DB Error"))
        
        with pytest.raises(DatabaseError):
            await expense_repo.get_by_category(user_id, "Food")
