"""Tests for budget_repository.py - comprehensive branch and code coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.budget_repository import BudgetRepository
from app.schemas.budget import BudgetCreate, BudgetUpdate
from app.db.models.data import Budget
from app.core.exceptions import ResourceNotFoundError


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
def budget_id():
    """Generate a test budget ID."""
    return uuid4()


@pytest.fixture
def budget_repo(mock_db):
    """Create a BudgetRepository with mocked database."""
    return BudgetRepository(mock_db)


@pytest.fixture
def sample_budget(user_id, budget_id):
    """Create a sample Budget object."""
    return Budget(
        id=budget_id,
        user_id=user_id,
        month=date(2026, 1, 1),
        category="Food",
        allocated_amount=Decimal("500.00"),
        spent_amount=Decimal("300.00"),
        recommended_amount=Decimal("400.00")
    )


# ============== TESTS FOR BudgetRepository ==============

class TestBudgetRepository:
    """Test BudgetRepository methods."""
    
    @pytest.mark.asyncio
    async def test_init(self, mock_db):
        """Test BudgetRepository initialization."""
        repo = BudgetRepository(mock_db)
        assert repo.db == mock_db
    
    # ============== CREATE TESTS ==============
    
    @pytest.mark.asyncio
    async def test_create_new_budget(self, budget_repo, user_id, budget_id):
        """Test creating a new budget."""
        budget_data = BudgetCreate(
            month=date(2026, 1, 1),
            category="Food",
            allocated_amount=Decimal("500.00")
        )
        
        # Mock get_by_user_month_category to return None (new budget)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        budget_repo.db.execute = AsyncMock(return_value=mock_result)
        
        budget_repo.db.add = MagicMock()
        budget_repo.db.commit = AsyncMock()
        budget_repo.db.refresh = AsyncMock()
        
        result = await budget_repo.create(user_id, budget_data)
        
        budget_repo.db.add.assert_called_once()
        budget_repo.db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_create_existing_budget_updates(self, budget_repo, user_id, sample_budget):
        """Test creating budget when one exists - should update."""
        budget_data = BudgetCreate(
            month=date(2026, 1, 1),
            category="Food",
            allocated_amount=Decimal("600.00")
        )
        
        # Mock get_by_user_month_category to return existing budget
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_budget
        budget_repo.db.execute = AsyncMock(return_value=mock_result)
        
        budget_repo.db.commit = AsyncMock()
        budget_repo.db.refresh = AsyncMock()
        
        result = await budget_repo.create(user_id, budget_data)
        
        assert result == sample_budget
        assert sample_budget.allocated_amount == Decimal("600.00")
        budget_repo.db.commit.assert_called()
    
    # ============== READ TESTS ==============
    
    @pytest.mark.asyncio
    async def test_get_by_id_success(self, budget_repo, user_id, budget_id, sample_budget):
        """Test getting budget by ID."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_budget
        budget_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await budget_repo.get_by_id(budget_id, user_id)
        
        assert result == sample_budget
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, budget_repo, user_id, budget_id):
        """Test getting budget by ID when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        budget_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await budget_repo.get_by_id(budget_id, user_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_by_user_month_category_success(self, budget_repo, user_id, sample_budget):
        """Test getting budget by user, month, and category."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_budget
        budget_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await budget_repo.get_by_user_month_category(
            user_id,
            date(2026, 1, 1),
            "Food"
        )
        
        assert result == sample_budget
    
    @pytest.mark.asyncio
    async def test_get_by_user_month_category_not_found(self, budget_repo, user_id):
        """Test getting budget by user, month, category when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        budget_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await budget_repo.get_by_user_month_category(
            user_id,
            date(2026, 1, 1),
            "Food"
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_by_user_all_budgets(self, budget_repo, user_id, sample_budget):
        """Test getting all budgets for a user."""
        budgets = [sample_budget]
        
        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = budgets
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_result
        budget_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await budget_repo.get_by_user(user_id)
        
        assert result == budgets
    
    @pytest.mark.asyncio
    async def test_get_by_user_with_date_range(self, budget_repo, user_id, sample_budget):
        """Test getting budgets for a user with date range."""
        budgets = [sample_budget]
        
        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = budgets
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_result
        budget_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await budget_repo.get_by_user(
            user_id,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31)
        )
        
        assert result == budgets
    
    @pytest.mark.asyncio
    async def test_get_by_user_with_only_start_date(self, budget_repo, user_id, sample_budget):
        """Test getting budgets with only start_date (no date filtering applied)."""
        budgets = [sample_budget]
        
        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = budgets
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_result
        budget_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await budget_repo.get_by_user(
            user_id,
            start_date=date(2026, 1, 1)
        )
        
        assert result == budgets
    
    @pytest.mark.asyncio
    async def test_get_by_user_with_only_end_date(self, budget_repo, user_id, sample_budget):
        """Test getting budgets with only end_date (no date filtering applied)."""
        budgets = [sample_budget]
        
        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = budgets
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_result
        budget_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await budget_repo.get_by_user(
            user_id,
            end_date=date(2026, 12, 31)
        )
        
        assert result == budgets
    
    @pytest.mark.asyncio
    async def test_get_by_user_no_budgets(self, budget_repo, user_id):
        """Test getting budgets when none exist."""
        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = []
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_result
        budget_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await budget_repo.get_by_user(user_id)
        
        assert result == []
    
    # ============== UPDATE TESTS ==============
    
    @pytest.mark.asyncio
    async def test_update_budget_success(self, budget_repo, user_id, budget_id, sample_budget):
        """Test updating a budget successfully."""
        budget_data = BudgetUpdate(
            allocated_amount=Decimal("600.00"),
            spent_amount=Decimal("350.00")
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_budget
        budget_repo.db.execute = AsyncMock(return_value=mock_result)
        
        budget_repo.db.add = MagicMock()
        budget_repo.db.commit = AsyncMock()
        budget_repo.db.refresh = AsyncMock()
        
        result = await budget_repo.update(budget_id, user_id, budget_data)
        
        assert result == sample_budget
        budget_repo.db.add.assert_called_once()
        budget_repo.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_budget_not_found(self, budget_repo, user_id, budget_id):
        """Test updating non-existent budget."""
        budget_data = BudgetUpdate(allocated_amount=Decimal("600.00"))
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        budget_repo.db.execute = AsyncMock(return_value=mock_result)
        
        with pytest.raises(ResourceNotFoundError):
            await budget_repo.update(budget_id, user_id, budget_data)
    
    @pytest.mark.asyncio
    async def test_update_budget_partial_fields(self, budget_repo, user_id, budget_id, sample_budget):
        """Test updating only specific budget fields."""
        budget_data = BudgetUpdate(allocated_amount=Decimal("750.00"))
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_budget
        budget_repo.db.execute = AsyncMock(return_value=mock_result)
        
        budget_repo.db.add = MagicMock()
        budget_repo.db.commit = AsyncMock()
        budget_repo.db.refresh = AsyncMock()
        
        result = await budget_repo.update(budget_id, user_id, budget_data)
        
        assert result == sample_budget
        budget_repo.db.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_budget_with_none_values(self, budget_repo, user_id, budget_id, sample_budget):
        """Test updating budget explicitly setting a field to None is skipped."""
        # Explicitly set spent_amount to None while setting allocated_amount
        budget_data = BudgetUpdate(
            allocated_amount=Decimal("800.00"),
            spent_amount=None
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_budget
        budget_repo.db.execute = AsyncMock(return_value=mock_result)
        
        budget_repo.db.add = MagicMock()
        budget_repo.db.commit = AsyncMock()
        budget_repo.db.refresh = AsyncMock()
        
        result = await budget_repo.update(budget_id, user_id, budget_data)
        
        assert result == sample_budget
        # Only non-None fields should be set
        budget_repo.db.add.assert_called_once()
    
    # ============== DELETE TESTS ==============
    
    @pytest.mark.asyncio
    async def test_delete_budget_success(self, budget_repo, user_id, budget_id, sample_budget):
        """Test soft-deleting a budget successfully."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_budget
        budget_repo.db.execute = AsyncMock(return_value=mock_result)

        budget_repo.db.add = MagicMock()
        budget_repo.db.flush = AsyncMock()
        budget_repo.db.commit = AsyncMock()

        result = await budget_repo.delete(budget_id, user_id)

        assert result is True
        # Soft delete: db.add() is called (not db.delete()) and commit follows
        budget_repo.db.add.assert_called_once()
        budget_repo.db.commit.assert_called_once()
        # The budget should be marked as deleted
        assert sample_budget.is_deleted
    
    @pytest.mark.asyncio
    async def test_delete_budget_not_found(self, budget_repo, user_id, budget_id):
        """Test deleting non-existent budget."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        budget_repo.db.execute = AsyncMock(return_value=mock_result)
        
        with pytest.raises(ResourceNotFoundError):
            await budget_repo.delete(budget_id, user_id)
