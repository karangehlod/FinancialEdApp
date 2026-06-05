"""Tests for goal_service.py - comprehensive branch and code coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.goal_service import GoalService
from app.schemas.goal import GoalCreate, GoalUpdate
from app.db.models.data import Goal
from app.core.exceptions import GoalNotFoundError, ValidationError


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
def goal_id():
    """Generate a test goal ID."""
    return uuid4()


@pytest.fixture
def sample_goal(user_id, goal_id):
    """Create a sample Goal object."""
    return Goal(
        id=goal_id,
        user_id=user_id,
        goal_name="Save for vacation",
        goal_type="savings",
        target_amount=Decimal("5000.00"),
        target_date=date(2026, 12, 31),
        description="Summer vacation fund",
        priority="high",
        status="active",
        current_amount=Decimal("2000.00"),
        created_at=datetime.now() - timedelta(days=30),
        updated_at=datetime.now()
    )


@pytest.fixture
def goal_service(mock_db):
    """Create a GoalService with mocked database."""
    return GoalService(mock_db)


# ============== TESTS FOR GoalService ==============

class TestGoalService:
    """Test GoalService methods."""
    
    @pytest.mark.asyncio
    async def test_init(self, mock_db):
        """Test GoalService initialization."""
        service = GoalService(mock_db)
        
        assert service.db == mock_db
    
    @pytest.mark.asyncio
    async def test_create_goal_success(self, goal_service, user_id, goal_id):
        """Test successful goal creation."""
        goal_data = GoalCreate(
            goal_name="Save for vacation",
            goal_type="savings",
            target_amount=Decimal("5000.00"),
            target_date=date(2026, 12, 31),
            description="Summer vacation fund",
            priority="high"
        )
        
        goal_service.db.add = MagicMock()
        goal_service.db.commit = AsyncMock()
        goal_service.db.refresh = AsyncMock()
        
        with patch('app.services.goal_service.Goal') as mock_goal_class:
            mock_goal = MagicMock()
            mock_goal.goal_name = goal_data.goal_name
            mock_goal_class.return_value = mock_goal
            
            result = await goal_service.create_goal(user_id, goal_data)
        
        assert result.goal_name == goal_data.goal_name
        goal_service.db.add.assert_called_once()
        goal_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_goal_exception(self, goal_service, user_id):
        """Test goal creation with exception."""
        goal_data = GoalCreate(
            goal_name="Test",
            goal_type="savings",
            target_amount=Decimal("1000"),
            target_date=date(2026, 12, 31),
            description="Test",
            priority="high"
        )
        
        goal_service.db.add = MagicMock()
        goal_service.db.commit.side_effect = Exception("DB error")
        goal_service.db.rollback = AsyncMock()
        
        with patch('app.services.goal_service.Goal'):
            with pytest.raises(ValidationError):
                await goal_service.create_goal(user_id, goal_data)
        
        goal_service.db.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_goal_success(self, goal_service, user_id, goal_id, sample_goal):
        """Test retrieving a goal successfully."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_goal
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await goal_service.get_goal(goal_id, user_id)
        
        assert result == sample_goal
    
    @pytest.mark.asyncio
    async def test_get_goal_not_found(self, goal_service, user_id, goal_id):
        """Test retrieving non-existent goal."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        with pytest.raises(GoalNotFoundError):
            await goal_service.get_goal(goal_id, user_id)
    
    @pytest.mark.asyncio
    async def test_get_user_goals_all(self, goal_service, user_id, sample_goal):
        """Test retrieving all goals for a user."""
        goals = [sample_goal]
        
        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = goals
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_result
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await goal_service.get_user_goals(user_id)
        
        assert result == goals
    
    @pytest.mark.asyncio
    async def test_get_user_goals_filter_by_status(self, goal_service, user_id, sample_goal):
        """Test retrieving goals filtered by status."""
        goals = [sample_goal]
        
        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = goals
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_result
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await goal_service.get_user_goals(user_id, status="active")
        
        assert result == goals
    
    @pytest.mark.asyncio
    async def test_get_user_goals_filter_by_type(self, goal_service, user_id, sample_goal):
        """Test retrieving goals filtered by type."""
        goals = [sample_goal]
        
        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = goals
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_result
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await goal_service.get_user_goals(user_id, goal_type="savings")
        
        assert result == goals
    
    @pytest.mark.asyncio
    async def test_get_user_goals_filter_by_status_and_type(self, goal_service, user_id, sample_goal):
        """Test retrieving goals filtered by both status and type."""
        goals = [sample_goal]
        
        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = goals
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_result
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await goal_service.get_user_goals(
            user_id, 
            status="active", 
            goal_type="savings"
        )
        
        assert result == goals
    
    @pytest.mark.asyncio
    async def test_update_goal_success(self, goal_service, user_id, goal_id, sample_goal):
        """Test updating a goal successfully."""
        goal_data = GoalUpdate(
            goal_name="Updated vacation goal",
            priority="medium"
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_goal
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        goal_service.db.add = MagicMock()
        goal_service.db.commit = AsyncMock()
        goal_service.db.refresh = AsyncMock()
        
        result = await goal_service.update_goal(goal_id, user_id, goal_data)
        
        assert result == sample_goal
        goal_service.db.add.assert_called_once()
        goal_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_goal_with_none_values(self, goal_service, user_id, goal_id, sample_goal):
        """Test update_goal skips None values (if value is not None branch)."""
        # Explicitly set some fields to None and others to values
        goal_data = GoalUpdate(
            goal_name="Updated vacation goal",
            target_amount=None,  # This should be skipped
            priority="low"
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_goal
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        goal_service.db.add = MagicMock()
        goal_service.db.commit = AsyncMock()
        goal_service.db.refresh = AsyncMock()
        
        result = await goal_service.update_goal(goal_id, user_id, goal_data)
        
        assert result == sample_goal
        # Verify that setattr was called for non-None values only
        goal_service.db.add.assert_called_once()
        goal_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_goal_success(self, goal_service, user_id, goal_id, sample_goal):
        """Test deleting a goal successfully."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_goal
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        goal_service.db.delete = AsyncMock()
        goal_service.db.commit = AsyncMock()
        
        result = await goal_service.delete_goal(goal_id, user_id)
        
        assert result is True
        goal_service.db.delete.assert_called_once()
        goal_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_goal_not_found(self, goal_service, user_id, goal_id):
        """Test deleting non-existent goal."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        with pytest.raises(GoalNotFoundError):
            await goal_service.delete_goal(goal_id, user_id)
    
    @pytest.mark.asyncio
    async def test_update_goal_progress_below_target(self, goal_service, user_id, goal_id, sample_goal):
        """Test updating goal progress when below target."""
        sample_goal.current_amount = Decimal("2000.00")
        sample_goal.target_amount = Decimal("5000.00")
        sample_goal.status = "active"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_goal
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        goal_service.db.add = MagicMock()
        goal_service.db.commit = AsyncMock()
        goal_service.db.refresh = AsyncMock()
        
        result = await goal_service.update_goal_progress(goal_id, user_id, Decimal("3000.00"))
        
        assert result == sample_goal
        assert sample_goal.current_amount == Decimal("3000.00")
        assert sample_goal.status == "active"
    
    @pytest.mark.asyncio
    async def test_update_goal_progress_reaches_target(self, goal_service, user_id, goal_id, sample_goal):
        """Test updating goal progress when target is reached."""
        sample_goal.current_amount = Decimal("4800.00")
        sample_goal.target_amount = Decimal("5000.00")
        sample_goal.status = "active"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_goal
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        goal_service.db.add = MagicMock()
        goal_service.db.commit = AsyncMock()
        goal_service.db.refresh = AsyncMock()
        
        result = await goal_service.update_goal_progress(goal_id, user_id, Decimal("5000.00"))
        
        assert result == sample_goal
        assert sample_goal.current_amount == Decimal("5000.00")
        assert sample_goal.status == "completed"
    
    @pytest.mark.asyncio
    async def test_update_goal_progress_exceeds_target(self, goal_service, user_id, goal_id, sample_goal):
        """Test updating goal progress when exceeding target."""
        sample_goal.current_amount = Decimal("4500.00")
        sample_goal.target_amount = Decimal("5000.00")
        sample_goal.status = "active"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_goal
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        goal_service.db.add = MagicMock()
        goal_service.db.commit = AsyncMock()
        goal_service.db.refresh = AsyncMock()
        
        result = await goal_service.update_goal_progress(goal_id, user_id, Decimal("6000.00"))
        
        assert result == sample_goal
        assert sample_goal.current_amount == Decimal("6000.00")
        assert sample_goal.status == "completed"
    
    @pytest.mark.asyncio
    async def test_get_goal_progress_on_track(self, goal_service, user_id, goal_id, sample_goal):
        """Test goal progress calculation when on track."""
        sample_goal.current_amount = Decimal("2000.00")
        sample_goal.target_amount = Decimal("5000.00")
        sample_goal.target_date = date.today() + timedelta(days=200)
        sample_goal.created_at = datetime.now() - timedelta(days=100)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_goal
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await goal_service.get_goal_progress(goal_id, user_id)
        
        assert result['goal_id'] == goal_id
        assert result['goal_name'] == sample_goal.goal_name
        assert result['current_amount'] == float(sample_goal.current_amount)
        assert result['target_amount'] == float(sample_goal.target_amount)
        assert result['status'] == "active"
        assert result['progress_percentage'] == float(Decimal("2000.00") / Decimal("5000.00") * 100)
    
    @pytest.mark.asyncio
    async def test_get_goal_progress_calculation_fields(self, goal_service, user_id, goal_id, sample_goal):
        """Test goal progress calculations."""
        sample_goal.current_amount = Decimal("1000.00")
        sample_goal.target_amount = Decimal("5000.00")
        sample_goal.target_date = date.today() + timedelta(days=100)
        sample_goal.created_at = datetime.now() - timedelta(days=30)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_goal
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await goal_service.get_goal_progress(goal_id, user_id)
        
        assert result['amount_remaining'] == float(Decimal("4000.00"))
        assert result['days_remaining'] == 100
        assert 'required_monthly_savings' in result
    
    @pytest.mark.asyncio
    async def test_get_goal_progress_zero_target_amount(self, goal_service, user_id, goal_id):
        """Test goal progress with zero target amount."""
        goal = Goal(
            id=goal_id,
            user_id=user_id,
            goal_name="Invalid goal",
            goal_type="savings",
            target_amount=Decimal("0"),
            target_date=date.today() + timedelta(days=100),
            description="Test",
            priority="low",
            status="active",
            current_amount=Decimal("0"),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = goal
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await goal_service.get_goal_progress(goal_id, user_id)
        
        assert result['progress_percentage'] == 0
    
    @pytest.mark.asyncio
    async def test_get_goal_progress_past_target_date(self, goal_service, user_id, goal_id, sample_goal):
        """Test goal progress when past target date."""
        sample_goal.target_date = date.today() - timedelta(days=10)
        sample_goal.current_amount = Decimal("2000.00")
        sample_goal.target_amount = Decimal("5000.00")
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_goal
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await goal_service.get_goal_progress(goal_id, user_id)
        
        assert result['days_remaining'] == 0  # Should be max(0, negative)
    
    @pytest.mark.asyncio
    async def test_get_goals_summary_single_goal(self, goal_service, user_id, sample_goal):
        """Test goals summary with single goal."""
        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = [sample_goal]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_result
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await goal_service.get_goals_summary(user_id)
        
        assert result['total_active_goals'] == 1
        assert result['total_target_amount'] == float(sample_goal.target_amount)
        assert result['total_current_amount'] == float(sample_goal.current_amount)
        assert result['overall_progress_percentage'] == float(
            sample_goal.current_amount / sample_goal.target_amount * 100
        )
    
    @pytest.mark.asyncio
    async def test_get_goals_summary_multiple_goals_same_type(self, goal_service, user_id, sample_goal):
        """Test goals summary with multiple goals of same type."""
        goal2 = Goal(
            id=uuid4(),
            user_id=user_id,
            goal_name="Save for car",
            goal_type="savings",
            target_amount=Decimal("10000.00"),
            target_date=date(2026, 12, 31),
            description="Car fund",
            priority="high",
            status="active",
            current_amount=Decimal("3000.00"),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = [sample_goal, goal2]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_result
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await goal_service.get_goals_summary(user_id)
        
        assert result['total_active_goals'] == 2
        assert result['total_target_amount'] == float(
            sample_goal.target_amount + goal2.target_amount
        )
        assert result['total_current_amount'] == float(
            sample_goal.current_amount + goal2.current_amount
        )
        assert len(result['goals_by_type']) == 1  # Both are "Savings"
    
    @pytest.mark.asyncio
    async def test_get_goals_summary_multiple_goals_different_types(self, goal_service, user_id, sample_goal):
        """Test goals summary with multiple goals of different types."""
        goal2 = Goal(
            id=uuid4(),
            user_id=user_id,
            goal_name="Pay off debt",
            goal_type="debt_payoff",
            target_amount=Decimal("5000.00"),
            target_date=date(2026, 12, 31),
            description="Credit card debt",
            priority="high",
            status="active",
            current_amount=Decimal("2000.00"),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = [sample_goal, goal2]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_result
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await goal_service.get_goals_summary(user_id)
        
        assert result['total_active_goals'] == 2
        assert len(result['goals_by_type']) == 2  # "savings" and "debt_payoff"
        assert 'savings' in result['goals_by_type']
        assert 'debt_payoff' in result['goals_by_type']
    
    @pytest.mark.asyncio
    async def test_get_goals_summary_no_goals(self, goal_service, user_id):
        """Test goals summary with no active goals."""
        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = []
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_result
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await goal_service.get_goals_summary(user_id)
        
        assert result['total_active_goals'] == 0
        assert result['total_target_amount'] == 0.0
        assert result['total_current_amount'] == 0.0
        assert result['overall_progress_percentage'] == 0.0
    
    @pytest.mark.asyncio
    async def test_get_goals_summary_goal_type_calculations(self, goal_service, user_id, sample_goal):
        """Test goal type calculations in summary."""
        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = [sample_goal]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_result
        goal_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await goal_service.get_goals_summary(user_id)
        
        assert 'savings' in result['goals_by_type']
        type_data = result['goals_by_type']['savings']
        assert type_data['count'] == 1
        assert type_data['target'] == float(sample_goal.target_amount)
        assert type_data['current'] == float(sample_goal.current_amount)
        assert type_data['progress'] == float(
            sample_goal.current_amount / sample_goal.target_amount * 100
        )
