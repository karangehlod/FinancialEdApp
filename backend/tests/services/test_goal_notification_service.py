"""Tests for goal_notification_service.py - comprehensive coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.goal_notification_service import GoalNotificationService
from app.services.notification_service import NotificationService
from app.db.models.data import Goal, UserProfile


# ============== FIXTURES ==============

@pytest.fixture
def mock_db():
    """Create a mock AsyncSession."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def user_id():
    """Generate a test user ID."""
    return str(uuid4())


@pytest.fixture
def goal_id():
    """Generate a test goal ID."""
    return str(uuid4())


@pytest.fixture
def sample_goal(user_id):
    """Create a sample Goal object."""
    return Goal(
        id=uuid4(),
        user_id=uuid4(),
        goal_name="Save for vacation",
        goal_type="savings",
        target_amount=Decimal("5000.00"),
        current_amount=Decimal("2500.00"),
        target_date=date(2024, 6, 30),
        description="Summer vacation fund",
        priority="high",
        status="active"
    )


@pytest.fixture
def sample_user_profile(user_id):
    """Create a sample UserProfile object."""
    return UserProfile(
        user_id=uuid4(),
        name="Test User",
        country="IN",
        currency="INR",
        knowledge_level="beginner",
        risk_tolerance="moderate"
    )


@pytest.fixture
def goal_notification_service(mock_db):
    """Create a GoalNotificationService with mocked dependencies."""
    service = GoalNotificationService(mock_db)
    # Mock the notification and email services
    service.notification_service = AsyncMock(spec=NotificationService)
    service.email_service = AsyncMock()
    return service


# ============== TESTS FOR GoalNotificationService ==============

class TestGoalNotificationService:
    """Test GoalNotificationService methods."""
    
    def test_init(self, mock_db):
        """Test GoalNotificationService initialization."""
        service = GoalNotificationService(mock_db)
        
        assert service.db_session == mock_db
        assert service.notification_service is not None
        assert service.email_service is not None
    
    @pytest.mark.asyncio
    async def test_get_goal_progress_percent_normal(self, goal_notification_service, sample_goal):
        """Test calculating progress percentage with normal data."""
        sample_goal.current_amount = Decimal("2500.00")
        sample_goal.target_amount = Decimal("5000.00")
        
        result = await goal_notification_service.get_goal_progress_percent(sample_goal)
        
        assert result == 50.0
    
    @pytest.mark.asyncio
    async def test_get_goal_progress_percent_zero_target(self, goal_notification_service):
        """Test progress calculation with zero target amount."""
        goal = MagicMock(spec=Goal)
        goal.target_amount = 0
        goal.current_amount = Decimal("0")
        
        result = await goal_notification_service.get_goal_progress_percent(goal)
        
        assert result == 0.0
    
    @pytest.mark.asyncio
    async def test_get_goal_progress_percent_none_target(self, goal_notification_service):
        """Test progress calculation with None target amount."""
        goal = MagicMock(spec=Goal)
        goal.target_amount = None
        goal.current_amount = Decimal("0")
        
        result = await goal_notification_service.get_goal_progress_percent(goal)
        
        assert result == 0.0
    
    @pytest.mark.asyncio
    async def test_get_goal_progress_percent_over_100(self, goal_notification_service):
        """Test progress calculation capped at 100%."""
        goal = MagicMock(spec=Goal)
        goal.target_amount = Decimal("1000.00")
        goal.current_amount = Decimal("1500.00")  # 150%
        
        result = await goal_notification_service.get_goal_progress_percent(goal)
        
        assert result == 100.0  # Should be capped at 100%
    
    @pytest.mark.asyncio
    async def test_check_milestone_progress_with_goal_object(self, goal_notification_service, user_id, goal_id):
        """Test milestone check with goal object provided."""
        goal = MagicMock(spec=Goal)
        goal.target_amount = Decimal("4000.00")
        goal.current_amount = Decimal("2000.00")  # 50% - milestone
        
        progress, is_milestone = await goal_notification_service.check_milestone_progress(
            user_id, goal_id, goal=goal
        )
        
        assert progress == 50.0
        assert is_milestone is True
    
    @pytest.mark.asyncio
    async def test_check_milestone_progress_25_percent(self, goal_notification_service, user_id, goal_id):
        """Test milestone detection at 25%."""
        goal = MagicMock(spec=Goal)
        goal.target_amount = Decimal("4000.00")
        goal.current_amount = Decimal("1000.00")  # 25%
        
        progress, is_milestone = await goal_notification_service.check_milestone_progress(
            user_id, goal_id, goal=goal
        )
        
        assert progress == 25.0
        assert is_milestone is True
    
    @pytest.mark.asyncio
    async def test_check_milestone_progress_75_percent(self, goal_notification_service, user_id, goal_id):
        """Test milestone detection at 75%."""
        goal = MagicMock(spec=Goal)
        goal.target_amount = Decimal("4000.00")
        goal.current_amount = Decimal("3000.00")  # 75%
        
        progress, is_milestone = await goal_notification_service.check_milestone_progress(
            user_id, goal_id, goal=goal
        )
        
        assert progress == 75.0
        assert is_milestone is True
    
    @pytest.mark.asyncio
    async def test_check_milestone_progress_100_percent(self, goal_notification_service, user_id, goal_id):
        """Test milestone detection at 100%."""
        goal = MagicMock(spec=Goal)
        goal.target_amount = Decimal("4000.00")
        goal.current_amount = Decimal("4000.00")  # 100%
        
        progress, is_milestone = await goal_notification_service.check_milestone_progress(
            user_id, goal_id, goal=goal
        )
        
        assert progress == 100.0
        assert is_milestone is True
    
    @pytest.mark.asyncio
    async def test_check_milestone_progress_no_milestone(self, goal_notification_service, user_id, goal_id):
        """Test milestone check when no milestone is reached."""
        goal = MagicMock(spec=Goal)
        goal.target_amount = Decimal("4000.00")
        goal.current_amount = Decimal("800.00")  # 20% - not a milestone
        
        progress, is_milestone = await goal_notification_service.check_milestone_progress(
            user_id, goal_id, goal=goal
        )
        
        assert progress == 20.0
        assert is_milestone is False
    
    @pytest.mark.asyncio
    async def test_check_milestone_progress_fetch_from_db(self, goal_notification_service, user_id, goal_id):
        """Test milestone check fetching goal from database."""
        goal = MagicMock(spec=Goal)
        goal.target_amount = Decimal("4000.00")
        goal.current_amount = Decimal("2000.00")  # 50%
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = goal
        
        goal_notification_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        progress, is_milestone = await goal_notification_service.check_milestone_progress(
            user_id, goal_id
        )
        
        assert progress == 50.0
        assert is_milestone is True
    
    @pytest.mark.asyncio
    async def test_check_milestone_progress_goal_not_found(self, goal_notification_service, user_id, goal_id):
        """Test milestone check when goal doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        
        goal_notification_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        progress, is_milestone = await goal_notification_service.check_milestone_progress(
            user_id, goal_id
        )
        
        assert progress == 0.0
        assert is_milestone is False
    
    @pytest.mark.asyncio
    async def test_send_milestone_notification_disabled(self, goal_notification_service, user_id, goal_id):
        """Test milestone notification when disabled in config."""
        with patch('app.services.goal_notification_service.settings.SEND_GOAL_NOTIFICATIONS', False):
            result = await goal_notification_service.send_milestone_notification(
                user_id, goal_id, {"goal_name": "Test"}, 50.0
            )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_milestone_notification_user_not_found(self, goal_notification_service, user_id, goal_id):
        """Test milestone notification when user profile not found."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        
        goal_notification_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        with patch('app.services.goal_notification_service.settings.SEND_GOAL_NOTIFICATIONS', True):
            result = await goal_notification_service.send_milestone_notification(
                user_id, goal_id, {"goal_name": "Test"}, 50.0
            )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_milestone_notification_100_percent(self, goal_notification_service, user_id, goal_id, sample_user_profile):
        """Test sending milestone notification for 100% completion."""
        goal_data = {
            "goal_name": "Save for vacation",
            "current_amount": 5000.00,
            "target_amount": 5000.00,
            "created_date": date(2024, 1, 1)
        }
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = sample_user_profile
        
        goal_notification_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        with patch('app.services.goal_notification_service.settings.SEND_GOAL_NOTIFICATIONS', True):
            result = await goal_notification_service.send_milestone_notification(
                user_id, goal_id, goal_data, 100.0
            )
        
        assert result is True
        goal_notification_service.notification_service.create_notification.assert_called_once()
        # Email service is not called since UserProfile doesn't have email attribute
    
    @pytest.mark.asyncio
    async def test_send_milestone_notification_50_percent(self, goal_notification_service, user_id, goal_id, sample_user_profile):
        """Test sending milestone notification for 50% progress."""
        goal_data = {
            "goal_name": "Save for vacation",
            "current_amount": 2500.00,
            "target_amount": 5000.00,
            "created_date": date(2024, 1, 1)
        }
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = sample_user_profile
        
        goal_notification_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        with patch('app.services.goal_notification_service.settings.SEND_GOAL_NOTIFICATIONS', True):
            result = await goal_notification_service.send_milestone_notification(
                user_id, goal_id, goal_data, 50.0
            )
        
        assert result is True
        goal_notification_service.notification_service.create_notification.assert_called_once()
        # Email service is not called since UserProfile doesn't have email attribute
    
    @pytest.mark.asyncio
    async def test_send_milestone_notification_75_percent(self, goal_notification_service, user_id, goal_id, sample_user_profile):
        """Test sending milestone notification for 75% progress."""
        goal_data = {
            "goal_name": "Save for vacation",
            "current_amount": 3750.00,
            "target_amount": 5000.00,
            "created_date": date(2024, 1, 1)
        }
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = sample_user_profile
        
        goal_notification_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        with patch('app.services.goal_notification_service.settings.SEND_GOAL_NOTIFICATIONS', True):
            result = await goal_notification_service.send_milestone_notification(
                user_id, goal_id, goal_data, 75.0
            )
        
        assert result is True
        goal_notification_service.notification_service.create_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_milestone_notification_25_percent(self, goal_notification_service, user_id, goal_id, sample_user_profile):
        """Test sending milestone notification for 25% progress."""
        goal_data = {
            "goal_name": "Save for vacation",
            "current_amount": 1250.00,
            "target_amount": 5000.00,
            "created_date": date(2024, 1, 1)
        }
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = sample_user_profile
        
        goal_notification_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        with patch('app.services.goal_notification_service.settings.SEND_GOAL_NOTIFICATIONS', True):
            result = await goal_notification_service.send_milestone_notification(
                user_id, goal_id, goal_data, 25.0
            )
        
        assert result is True
        goal_notification_service.notification_service.create_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_off_track_alerts_with_off_track_goals(self, goal_notification_service, user_id):
        """Test sending alerts for goals that are off track."""
        goal_statuses = [
            {
                "goal_id": str(uuid4()),
                "goal_name": "Save for car",
                "progress": 20.0,
                "expected_progress": 50.0,
                "is_on_track": False,
                "days_remaining": 180
            },
            {
                "goal_id": str(uuid4()),
                "goal_name": "Emergency fund",
                "progress": 70.0,
                "expected_progress": 60.0,
                "is_on_track": True,
                "days_remaining": 100
            }
        ]
        
        goal_notification_service.check_goals_on_track = AsyncMock(return_value=goal_statuses)
        
        result = await goal_notification_service.send_off_track_alerts(user_id)
        
        assert result == 1  # Only one goal is off track
        goal_notification_service.notification_service.create_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_off_track_alerts_all_on_track(self, goal_notification_service, user_id):
        """Test sending alerts when all goals are on track."""
        goal_statuses = [
            {
                "goal_id": str(uuid4()),
                "goal_name": "Save for car",
                "progress": 70.0,
                "expected_progress": 50.0,
                "is_on_track": True,
                "days_remaining": 180
            }
        ]
        
        goal_notification_service.check_goals_on_track = AsyncMock(return_value=goal_statuses)
        
        result = await goal_notification_service.send_off_track_alerts(user_id)
        
        assert result == 0
        goal_notification_service.notification_service.create_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_off_track_alerts_no_goals(self, goal_notification_service, user_id):
        """Test sending alerts when user has no goals."""
        goal_notification_service.check_goals_on_track = AsyncMock(return_value=[])
        
        result = await goal_notification_service.send_off_track_alerts(user_id)
        
        assert result == 0
        goal_notification_service.notification_service.create_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_goal_summary_with_multiple_goals(self, goal_notification_service, user_id):
        """Test getting goal summary with multiple goals in different states."""
        goals = [
            MagicMock(spec=Goal, status="active", target_amount=Decimal("5000.00"), current_amount=Decimal("2500.00")),
            MagicMock(spec=Goal, status="active", target_amount=Decimal("3000.00"), current_amount=Decimal("1500.00")),
            MagicMock(spec=Goal, status="completed", target_amount=Decimal("2000.00"), current_amount=Decimal("2000.00")),
            MagicMock(spec=Goal, status="paused", target_amount=Decimal("10000.00"), current_amount=Decimal("1000.00")),
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = goals
        
        goal_notification_service.db_session.execute = AsyncMock(return_value=mock_result)
        goal_notification_service.get_goal_progress_percent = AsyncMock(side_effect=[50.0, 50.0, 100.0, 10.0])
        
        result = await goal_notification_service.get_goal_summary(user_id)
        
        assert result["total_goals"] == 4
        assert result["active_goals"] == 2
        assert result["completed_goals"] == 1
        assert result["paused_goals"] == 1
        assert result["total_target"] == 20000.00
        assert result["total_current"] == 7000.00
        assert result["avg_progress"] == 52.5

    @pytest.mark.asyncio
    async def test_get_goal_summary_no_goals(self, goal_notification_service, user_id):
        """Test getting goal summary when user has no goals."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        
        goal_notification_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await goal_notification_service.get_goal_summary(user_id)
        
        assert result["total_goals"] == 0
        assert result["active_goals"] == 0
        assert result["completed_goals"] == 0
        assert result["paused_goals"] == 0
        assert result["total_target"] == 0.0
        assert result["total_current"] == 0.0
        assert result["avg_progress"] == 0.0

    @pytest.mark.asyncio
    async def test_check_goals_on_track_on_track_goal(self, goal_notification_service, user_id):
        """Test checking goals when goal is on track."""
        # Set up dates so that expected progress is around 50% and actual is 50%
        today = date.today()
        start_date = today - timedelta(days=50)
        end_date = today + timedelta(days=50)
        
        goal = MagicMock(spec=Goal)
        goal.id = uuid4()
        goal.goal_name = "On Track Goal"
        goal.created_at = datetime.combine(start_date, datetime.min.time())
        goal.target_date = end_date
        goal.current_amount = Decimal("500.00")
        goal.target_amount = Decimal("1000.00")
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [goal]
        
        goal_notification_service.db_session.execute = AsyncMock(return_value=mock_result)
        goal_notification_service.get_goal_progress_percent = AsyncMock(return_value=55.0)  # Slightly above expected 50%
        
        result = await goal_notification_service.check_goals_on_track(user_id)
        
        assert len(result) == 1
        assert result[0]["is_on_track"] is True

    @pytest.mark.asyncio
    async def test_check_goals_on_track_goal_deadline_passed(self, goal_notification_service, user_id):
        """Test checking goals when goal deadline has passed."""
        today = date.today()
        start_date = today - timedelta(days=100)
        end_date = today - timedelta(days=10)  # Already passed
        
        goal = MagicMock(spec=Goal)
        goal.id = uuid4()
        goal.goal_name = "Overdue Goal"
        goal.created_at = datetime.combine(start_date, datetime.min.time())
        goal.target_date = end_date
        goal.current_amount = Decimal("100.00")
        goal.target_amount = Decimal("1000.00")
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [goal]
        
        goal_notification_service.db_session.execute = AsyncMock(return_value=mock_result)
        goal_notification_service.get_goal_progress_percent = AsyncMock(return_value=10.0)  # Only 10% progress with deadline passed
        
        result = await goal_notification_service.check_goals_on_track(user_id)
        
        assert len(result) == 1
        # Expected progress should be 100% (days_total <= 0), so actual 10% is off track
        assert result[0]["is_on_track"] is False

    @pytest.mark.asyncio
    async def test_check_goals_on_track_goal_negative_days_total(self, goal_notification_service, user_id):
        """Test check_goals_on_track when goal target date is in the past (days_total <= 0)."""
        today = date.today()
        start_date = today - timedelta(days=50)
        end_date = today - timedelta(days=30)  # 30 days in the past
        
        goal = MagicMock(spec=Goal)
        goal.id = uuid4()
        goal.goal_name = "Past Deadline Goal"
        goal.created_at = datetime.combine(start_date, datetime.min.time())
        goal.target_date = end_date
        goal.current_amount = Decimal("500.00")
        goal.target_amount = Decimal("1000.00")
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [goal]
        
        goal_notification_service.db_session.execute = AsyncMock(return_value=mock_result)
        goal_notification_service.get_goal_progress_percent = AsyncMock(return_value=50.0)
        
        result = await goal_notification_service.check_goals_on_track(user_id)
        
        assert len(result) == 1
        # When days_total <= 0, expected_progress should be 100.0
        assert result[0]["expected_progress"] == 100.0

    @pytest.mark.asyncio
    async def test_send_milestone_notification_no_milestone_branch(self, goal_notification_service, user_id, goal_id, sample_user_profile):
        """Test milestone notification when no milestone is reached (progress between milestones)."""
        goal_data = {
            "goal_name": "Save for vacation",
            "current_amount": 600.00,  # 12% progress - no milestone
            "target_amount": 5000.00,
            "created_date": date(2024, 1, 1)
        }
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = sample_user_profile
        
        goal_notification_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        with patch('app.services.goal_notification_service.settings.SEND_GOAL_NOTIFICATIONS', True):
            result = await goal_notification_service.send_milestone_notification(
                user_id, goal_id, goal_data, 12.0
            )
        
        # Should return False because no milestone was reached
        assert result is False
        goal_notification_service.notification_service.create_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_milestone_notification_with_email_service_100(self, goal_notification_service, user_id, goal_id):
        """Test milestone notification with email service for 100% completion."""
        user_profile = MagicMock(spec=UserProfile)
        user_profile.user_id = uuid4()
        user_profile.name = "Test User"
        user_profile.email = "test@example.com"
        
        goal_data = {
            "goal_name": "Save for vacation",
            "current_amount": 5000.00,
            "target_amount": 5000.00,
            "created_date": date(2024, 1, 1)
        }
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = user_profile
        
        goal_notification_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        with patch('app.services.goal_notification_service.settings.SEND_GOAL_NOTIFICATIONS', True):
            result = await goal_notification_service.send_milestone_notification(
                user_id, goal_id, goal_data, 100.0
            )
        
        assert result is True
        goal_notification_service.notification_service.create_notification.assert_called_once()
        # Email service should be called for 100% completion
        goal_notification_service.email_service.send_goal_completion_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_milestone_notification_with_email_service_50(self, goal_notification_service, user_id, goal_id):
        """Test milestone notification with email service for 50% milestone."""
        user_profile = MagicMock(spec=UserProfile)
        user_profile.user_id = uuid4()
        user_profile.name = "Test User"
        user_profile.email = "test@example.com"
        
        goal_data = {
            "goal_name": "Save for vacation",
            "current_amount": 2500.00,
            "target_amount": 5000.00,
            "created_date": date(2024, 1, 1)
        }
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = user_profile
        
        goal_notification_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        with patch('app.services.goal_notification_service.settings.SEND_GOAL_NOTIFICATIONS', True):
            result = await goal_notification_service.send_milestone_notification(
                user_id, goal_id, goal_data, 50.0
            )
        
        assert result is True
        goal_notification_service.notification_service.create_notification.assert_called_once()
        # Email service should be called for milestone (non-100%)
        goal_notification_service.email_service.send_goal_milestone_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_goal_summary_single_goal_with_progress(self, goal_notification_service, user_id):
        """Test goal summary with a single goal and specific status transitions."""
        goal = MagicMock(spec=Goal)
        goal.status = "completed"
        goal.target_amount = Decimal("5000.00")
        goal.current_amount = Decimal("5000.00")
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [goal]
        
        goal_notification_service.db_session.execute = AsyncMock(return_value=mock_result)
        goal_notification_service.get_goal_progress_percent = AsyncMock(return_value=100.0)
        
        result = await goal_notification_service.get_goal_summary(user_id)
        
        assert result["total_goals"] == 1
        assert result["completed_goals"] == 1
        assert result["avg_progress"] == 100.0

    @pytest.mark.asyncio
    async def test_get_goal_summary_with_each_status_type(self, goal_notification_service, user_id):
        """Test goal summary explicitly hitting each status branch."""
        active_goal = MagicMock(spec=Goal, status="active", target_amount=Decimal("1000.00"), current_amount=Decimal("500.00"))
        completed_goal = MagicMock(spec=Goal, status="completed", target_amount=Decimal("1000.00"), current_amount=Decimal("1000.00"))
        paused_goal = MagicMock(spec=Goal, status="paused", target_amount=Decimal("1000.00"), current_amount=Decimal("100.00"))
        other_status_goal = MagicMock(spec=Goal, status="other", target_amount=Decimal("1000.00"), current_amount=Decimal("200.00"))
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [active_goal, completed_goal, paused_goal, other_status_goal]
        
        goal_notification_service.db_session.execute = AsyncMock(return_value=mock_result)
        goal_notification_service.get_goal_progress_percent = AsyncMock(side_effect=[50.0, 100.0, 10.0, 20.0])
        
        result = await goal_notification_service.get_goal_summary(user_id)
        
        assert result["total_goals"] == 4
        assert result["active_goals"] == 1
        assert result["completed_goals"] == 1
        assert result["paused_goals"] == 1
        # The "other" status goal should just count in totals but not in status counts
        assert result["total_target"] == 4000.00
        assert result["total_current"] == 1800.00

    @pytest.mark.asyncio
    async def test_check_goals_on_track_with_days_calculation(self, goal_notification_service, user_id):
        """Test check_goals_on_track explicitly exercises the days_elapsed calculation."""
        today = date.today()
        # Create a goal that started 25 days ago, ends in 75 days (25% of 100 day period)
        start_date = today - timedelta(days=25)
        end_date = today + timedelta(days=75)
        
        goal = MagicMock(spec=Goal)
        goal.id = uuid4()
        goal.goal_name = "Progress Goal"
        goal.created_at = datetime.combine(start_date, datetime.min.time())
        goal.target_date = end_date
        goal.current_amount = Decimal("250.00")
        goal.target_amount = Decimal("1000.00")
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [goal]
        
        goal_notification_service.db_session.execute = AsyncMock(return_value=mock_result)
        goal_notification_service.get_goal_progress_percent = AsyncMock(return_value=25.0)  # Exactly 25% - on track
        
        result = await goal_notification_service.check_goals_on_track(user_id)
        
        assert len(result) == 1
        assert result[0]["progress"] == 25.0
        assert result[0]["expected_progress"] == 25.0  # (25 days / 100 days) * 100
        assert result[0]["is_on_track"] is True

    @pytest.mark.asyncio
    async def test_check_goals_on_track_else_branch_days_total(self, goal_notification_service, user_id):
        """Test check_goals_on_track with positive days_total to cover else branch."""
        today = date.today()
        start_date = today - timedelta(days=10)
        end_date = today + timedelta(days=20)  # Positive days_total = 30
        
        goal = MagicMock(spec=Goal)
        goal.id = uuid4()
        goal.goal_name = "Future Goal"
        goal.created_at = datetime.combine(start_date, datetime.min.time())
        goal.target_date = end_date
        goal.current_amount = Decimal("300.00")
        goal.target_amount = Decimal("1000.00")
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [goal]
        
        goal_notification_service.db_session.execute = AsyncMock(return_value=mock_result)
        goal_notification_service.get_goal_progress_percent = AsyncMock(return_value=30.0)
        
        result = await goal_notification_service.check_goals_on_track(user_id)
        
        assert len(result) == 1
        # days_elapsed = 10, days_total = 30, expected_progress = (10/30)*100 ≈ 33.3%
        assert result[0]["expected_progress"] > 0
        assert result[0]["expected_progress"] < 100

    @pytest.mark.asyncio
    async def test_check_goals_on_track_positive_days_total_calculation(self, goal_notification_service, user_id):
        """Test check_goals_on_track calculates expected_progress correctly when days_total > 0."""
        today = date.today()
        # Create a goal that started 20 days ago and will end in 30 days
        # So days_elapsed = 20, days_total = 50, expected_progress = (20/50)*100 = 40%
        start_date = today - timedelta(days=20)
        end_date = today + timedelta(days=30)
        
        goal = MagicMock(spec=Goal)
        goal.id = uuid4()
        goal.goal_name = "Test Goal"
        goal.created_at = datetime.combine(start_date, datetime.min.time())
        goal.target_date = end_date
        goal.current_amount = Decimal("400.00")
        goal.target_amount = Decimal("1000.00")
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [goal]
        
        goal_notification_service.db_session.execute = AsyncMock(return_value=mock_result)
        goal_notification_service.get_goal_progress_percent = AsyncMock(return_value=40.0)
        
        result = await goal_notification_service.check_goals_on_track(user_id)
        
        assert len(result) == 1
        assert result[0]["expected_progress"] == 40.0
        assert result[0]["is_on_track"] is True

    @pytest.mark.asyncio
    async def test_check_goals_on_track_past_target_date(self, goal_notification_service, user_id):
        """Test check_goals_on_track when target_date is before created_at (days_total <= 0)."""
        today = datetime.utcnow().date()
        
        goal = MagicMock()
        goal.id = uuid4()
        goal.user_id = uuid4()
        goal.name = "Test Goal"
        goal.description = "Test"
        goal.goal_type = "savings"
        goal.current_amount = Decimal("500.00")
        goal.target_amount = Decimal("1000.00")
        goal.created_at = datetime.utcnow()
        goal.target_date = today - timedelta(days=10)  # Target date is in the past
        goal.status = "active"
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [goal]
        
        goal_notification_service.db_session.execute = AsyncMock(return_value=mock_result)
        goal_notification_service.get_goal_progress_percent = AsyncMock(return_value=50.0)
        
        result = await goal_notification_service.check_goals_on_track(user_id)
        
        assert len(result) == 1
        # When days_total <= 0, expected_progress should be 100.0
        assert result[0]["expected_progress"] == 100.0
        # Current progress 50% is not >= (100% - 10% buffer), so is_on_track is False
        assert result[0]["is_on_track"] is False
