"""Tests for goal schema validation."""
import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from pydantic import ValidationError
from app.schemas.goal import GoalCreate, GoalUpdate, GoalResponse


class TestGoalCreate:
    """Test GoalCreate schema validation."""
    
    def test_valid_goal_creation(self):
        """Test creating a goal with valid data."""
        data = {
            "goal_name": "Save for house",
            "goal_type": "savings",
            "target_amount": Decimal("100000"),
            "target_date": date.today() + timedelta(days=365),
        }
        goal = GoalCreate(**data)
        assert goal.goal_name == "Save for house"
        assert goal.goal_type == "savings"
        assert goal.priority == "medium"  # default value
    
    def test_goal_with_custom_priority(self):
        """Test goal creation with custom priority."""
        data = {
            "goal_name": "Emergency fund",
            "goal_type": "emergency_fund",
            "target_amount": Decimal("50000"),
            "target_date": date.today() + timedelta(days=180),
            "priority": "high",
        }
        goal = GoalCreate(**data)
        assert goal.priority == "high"
    
    def test_goal_with_description(self):
        """Test goal creation with description."""
        data = {
            "goal_name": "Pay off credit card",
            "goal_type": "debt_payoff",
            "target_amount": Decimal("10000"),
            "target_date": date.today() + timedelta(days=90),
            "description": "Pay off all credit card debt",
        }
        goal = GoalCreate(**data)
        assert goal.description == "Pay off all credit card debt"
    
    def test_invalid_goal_name_empty(self):
        """Test that empty goal name is rejected."""
        data = {
            "goal_name": "",
            "goal_type": "savings",
            "target_amount": Decimal("50000"),
            "target_date": date.today() + timedelta(days=365),
        }
        with pytest.raises(ValidationError) as exc_info:
            GoalCreate(**data)
        assert "at least 1 character" in str(exc_info.value).lower()
    
    def test_invalid_goal_name_too_long(self):
        """Test that a goal name > 255 chars is sanitized/truncated (not rejected).

        The sanitize_name() validator runs before Pydantic's max_length check and
        truncates the value to 150 chars, so no ValidationError is raised.
        """
        long_name = "a" * 256
        data = {
            "goal_name": long_name,
            "goal_type": "savings",
            "target_amount": Decimal("50000"),
            "target_date": date.today() + timedelta(days=365),
        }
        goal = GoalCreate(**data)
        # sanitize_name truncates to _MAX_NAME_LEN (150), well within max_length=255
        assert len(goal.goal_name) <= 255
    
    def test_invalid_goal_type(self):
        """Test that invalid goal type is rejected."""
        data = {
            "goal_name": "My goal",
            "goal_type": "invalid_type",
            "target_amount": Decimal("50000"),
            "target_date": date.today() + timedelta(days=365),
        }
        with pytest.raises(ValidationError):
            GoalCreate(**data)
    
    def test_all_valid_goal_types(self):
        """Test all valid goal types."""
        valid_types = ["savings", "debt_payoff", "investment", "emergency_fund", "other"]
        for goal_type in valid_types:
            data = {
                "goal_name": f"Goal {goal_type}",
                "goal_type": goal_type,
                "target_amount": Decimal("50000"),
                "target_date": date.today() + timedelta(days=365),
            }
            goal = GoalCreate(**data)
            assert goal.goal_type == goal_type
    
    def test_negative_target_amount(self):
        """Test that negative target amount is rejected."""
        data = {
            "goal_name": "My goal",
            "goal_type": "savings",
            "target_amount": Decimal("-100"),
            "target_date": date.today() + timedelta(days=365),
        }
        with pytest.raises(ValidationError):
            GoalCreate(**data)
    
    def test_zero_target_amount(self):
        """Test that zero target amount is rejected."""
        data = {
            "goal_name": "My goal",
            "goal_type": "savings",
            "target_amount": Decimal("0"),
            "target_date": date.today() + timedelta(days=365),
        }
        with pytest.raises(ValidationError):
            GoalCreate(**data)
    
    def test_target_date_in_past(self):
        """Test that target date in past is rejected."""
        data = {
            "goal_name": "My goal",
            "goal_type": "savings",
            "target_amount": Decimal("50000"),
            "target_date": date.today() - timedelta(days=1),
        }
        with pytest.raises(ValidationError) as exc_info:
            GoalCreate(**data)
        assert "future" in str(exc_info.value).lower()
    
    def test_target_date_today(self):
        """Test that target date as today is rejected."""
        data = {
            "goal_name": "My goal",
            "goal_type": "savings",
            "target_amount": Decimal("50000"),
            "target_date": date.today(),
        }
        with pytest.raises(ValidationError) as exc_info:
            GoalCreate(**data)
        assert "future" in str(exc_info.value).lower()
    
    def test_invalid_priority(self):
        """Test that invalid priority is rejected."""
        data = {
            "goal_name": "My goal",
            "goal_type": "savings",
            "target_amount": Decimal("50000"),
            "target_date": date.today() + timedelta(days=365),
            "priority": "critical",
        }
        with pytest.raises(ValidationError):
            GoalCreate(**data)
    
    def test_all_valid_priorities(self):
        """Test all valid priorities."""
        valid_priorities = ["high", "medium", "low"]
        for priority in valid_priorities:
            data = {
                "goal_name": "My goal",
                "goal_type": "savings",
                "target_amount": Decimal("50000"),
                "target_date": date.today() + timedelta(days=365),
                "priority": priority,
            }
            goal = GoalCreate(**data)
            assert goal.priority == priority
    
    def test_large_target_amount(self):
        """Test very large target amounts."""
        data = {
            "goal_name": "Billionaire goal",
            "goal_type": "investment",
            "target_amount": Decimal("1000000000"),
            "target_date": date.today() + timedelta(days=3650),
        }
        goal = GoalCreate(**data)
        assert goal.target_amount == Decimal("1000000000")
    
    def test_very_small_target_amount(self):
        """Test very small but positive target amounts."""
        data = {
            "goal_name": "Small goal",
            "goal_type": "savings",
            "target_amount": Decimal("0.01"),
            "target_date": date.today() + timedelta(days=30),
        }
        goal = GoalCreate(**data)
        assert goal.target_amount == Decimal("0.01")


class TestGoalUpdate:
    """Test GoalUpdate schema validation."""
    
    def test_update_goal_name_only(self):
        """Test updating only goal name."""
        data = {"goal_name": "New name"}
        update = GoalUpdate(**data)
        assert update.goal_name == "New name"
        assert update.target_amount is None
    
    def test_update_multiple_fields(self):
        """Test updating multiple fields."""
        data = {
            "goal_name": "Updated name",
            "target_amount": Decimal("75000"),
            "current_amount": Decimal("25000"),
        }
        update = GoalUpdate(**data)
        assert update.goal_name == "Updated name"
        assert update.target_amount == Decimal("75000")
        assert update.current_amount == Decimal("25000")
    
    def test_update_all_fields(self):
        """Test updating all fields."""
        future_date = date.today() + timedelta(days=365)
        data = {
            "goal_name": "New name",
            "target_amount": Decimal("100000"),
            "current_amount": Decimal("50000"),
            "target_date": future_date,
        }
        update = GoalUpdate(**data)
        assert update.goal_name == "New name"
        assert update.target_amount == Decimal("100000")
        assert update.current_amount == Decimal("50000")
        assert update.target_date == future_date
    
    def test_update_empty_object(self):
        """Test empty update object (all None)."""
        update = GoalUpdate()
        assert update.goal_name is None
        assert update.target_amount is None
        assert update.current_amount is None
        assert update.target_date is None
    
    def test_update_current_amount_zero(self):
        """Test updating current amount to zero."""
        data = {"current_amount": Decimal("0")}
        update = GoalUpdate(**data)
        assert update.current_amount == Decimal("0")
    
    def test_update_current_amount_negative(self):
        """Test that negative current amount is allowed on update."""
        # Note: Schema might allow this, but service should validate
        data = {"current_amount": Decimal("-100")}
        update = GoalUpdate(**data)
        assert update.current_amount == Decimal("-100")
    
    def test_update_target_date_past(self):
        """Test that past target date is allowed on update."""
        # Note: Schema might allow this, but service should validate
        data = {"target_date": date.today() - timedelta(days=1)}
        update = GoalUpdate(**data)
        assert update.target_date == date.today() - timedelta(days=1)


class TestGoalResponse:
    """Test GoalResponse schema."""
    
    def test_response_with_all_fields(self):
        """Test complete goal response."""
        from uuid import uuid4
        goal_id = uuid4()
        user_id = uuid4()
        now = datetime.utcnow().isoformat()
        
        data = {
            "id": goal_id,
            "user_id": user_id,
            "goal_name": "Save for house",
            "goal_type": "savings",
            "target_amount": Decimal("100000"),
            "current_amount": Decimal("25000"),
            "target_date": date.today() + timedelta(days=365),
            "description": "Save for a dream house",
            "priority": "high",
            "status": "active",
            "progress_percentage": 25.0,
            "days_remaining": 365,
            "created_at": now,
            "updated_at": now,
        }
        response = GoalResponse(**data)
        assert response.id == goal_id
        assert response.goal_name == "Save for house"
        assert response.current_amount == Decimal("25000")
        assert response.progress_percentage == 25.0
        assert response.days_remaining == 365
    
    def test_response_with_completed_status(self):
        """Test goal response with completed status."""
        from uuid import uuid4
        now = datetime.utcnow().isoformat()
        
        data = {
            "id": uuid4(),
            "user_id": uuid4(),
            "goal_name": "Emergency fund",
            "goal_type": "emergency_fund",
            "target_amount": Decimal("50000"),
            "current_amount": Decimal("50000"),
            "target_date": date.today() + timedelta(days=100),
            "description": "Build emergency fund",
            "priority": "high",
            "status": "completed",
            "progress_percentage": 100.0,
            "days_remaining": 100,
            "created_at": now,
            "updated_at": now,
        }
        response = GoalResponse(**data)
        assert response.status == "completed"
        assert response.progress_percentage == 100.0
    
    def test_response_with_all_valid_statuses(self):
        """Test goal response with all valid statuses."""
        from uuid import uuid4
        now = datetime.utcnow().isoformat()
        
        valid_statuses = ["active", "completed", "paused", "abandoned"]
        for status in valid_statuses:
            data = {
                "id": uuid4(),
                "user_id": uuid4(),
                "goal_name": "Test goal",
                "goal_type": "savings",
                "target_amount": Decimal("50000"),
                "current_amount": Decimal("10000"),
                "target_date": date.today() + timedelta(days=365),
                "description": "Test",
                "priority": "medium",
                "status": status,
                "progress_percentage": 20.0,
                "days_remaining": 365,
                "created_at": now,
                "updated_at": now,
            }
            response = GoalResponse(**data)
            assert response.status == status
