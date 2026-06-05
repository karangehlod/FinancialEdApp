"""Tests for budget_alert_service.py - 100% branch coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from uuid import UUID
from datetime import datetime

from app.services.budget_alert_service import BudgetAlertService
from app.db.models.data import BudgetAlert, Budget, UserProfile


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock(return_value=None)
    db.refresh = AsyncMock(return_value=None)
    db.execute = AsyncMock()
    return db


@pytest.fixture
def budget_alert_service(mock_db):
    with patch('app.services.budget_alert_service.NotificationService'):
        with patch('app.services.budget_alert_service.get_email_service'):
            service = BudgetAlertService(mock_db)
            return service


@pytest.fixture
def sample_budget():
    from datetime import date
    return Budget(
        id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        user_id=UUID("550e8400-e29b-41d4-a716-446655440001"),
        month=date.today(),
        category="Groceries",
        allocated_amount=Decimal("10000.00"),
        spent_amount=Decimal("5000.00"),
        created_at=datetime.utcnow()
    )


@pytest.fixture
def sample_user_profile():
    profile = UserProfile(
        user_id=UUID("550e8400-e29b-41d4-a716-446655440001"),
        name="John Doe"
    )
    # Add email as dynamic attribute for testing
    profile.email = "john@example.com"
    return profile


@pytest.fixture
def sample_budget_alert():
    return BudgetAlert(
        id=UUID("550e8400-e29b-41d4-a716-446655440003"),
        budget_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        user_id=UUID("550e8400-e29b-41d4-a716-446655440001"),
        alert_level="medium",
        message="Budget alert message",
        utilization_at_alert=Decimal("50.00"),
        is_read=False,
        created_at=datetime.utcnow()
    )


class TestInitialization:
    def test_init_stores_db_session(self, mock_db):
        with patch('app.services.budget_alert_service.NotificationService'):
            with patch('app.services.budget_alert_service.get_email_service'):
                service = BudgetAlertService(mock_db)
                assert service.db_session is mock_db


class TestCheckBudgetStatus:
    @pytest.mark.asyncio
    async def test_check_budget_status_found_50_percent(self, budget_alert_service, mock_db, sample_budget):
        """Test budget status check with 50% utilization."""
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.first.return_value = sample_budget
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        utilization, alert_level = await budget_alert_service.check_budget_status(
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440000"
        )
        
        assert utilization == 50.0
        assert alert_level == "none"

    @pytest.mark.asyncio
    async def test_check_budget_status_found_75_percent(self, budget_alert_service, mock_db):
        """Test budget status check with 75% utilization (medium alert)."""
        from datetime import date
        budget = Budget(
            id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            user_id=UUID("550e8400-e29b-41d4-a716-446655440001"),
            month=date.today(),
            category="Groceries",
            allocated_amount=Decimal("10000.00"),
            spent_amount=Decimal("7500.00"),
            created_at=datetime.utcnow()
        )
        
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.first.return_value = budget
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        with patch('app.services.budget_alert_service.settings') as mock_settings:
            mock_settings.BUDGET_ALERT_THRESHOLD = 70
            
            utilization, alert_level = await budget_alert_service.check_budget_status(
                "550e8400-e29b-41d4-a716-446655440001",
                "550e8400-e29b-41d4-a716-446655440000"
            )
            
            assert utilization == 75.0
            assert alert_level == "medium"

    @pytest.mark.asyncio
    async def test_check_budget_status_found_90_percent(self, budget_alert_service, mock_db):
        """Test budget status check with 90% utilization (high alert)."""
        from datetime import date
        budget = Budget(
            id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            user_id=UUID("550e8400-e29b-41d4-a716-446655440001"),
            month=date.today(),
            category="Groceries",
            allocated_amount=Decimal("10000.00"),
            spent_amount=Decimal("9000.00"),
            created_at=datetime.utcnow()
        )
        
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.first.return_value = budget
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        utilization, alert_level = await budget_alert_service.check_budget_status(
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440000"
        )
        
        assert utilization == 90.0
        assert alert_level == "high"

    @pytest.mark.asyncio
    async def test_check_budget_status_found_100_percent(self, budget_alert_service, mock_db):
        """Test budget status check with 100% utilization (critical alert)."""
        from datetime import date
        budget = Budget(
            id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            user_id=UUID("550e8400-e29b-41d4-a716-446655440001"),
            month=date.today(),
            category="Groceries",
            allocated_amount=Decimal("10000.00"),
            spent_amount=Decimal("10000.00"),
            created_at=datetime.utcnow()
        )
        
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.first.return_value = budget
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        utilization, alert_level = await budget_alert_service.check_budget_status(
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440000"
        )
        
        assert utilization == 100.0
        assert alert_level == "critical"

    @pytest.mark.asyncio
    async def test_check_budget_status_not_found(self, budget_alert_service, mock_db):
        """Test budget status check when budget not found."""
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.first.return_value = None
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        utilization, alert_level = await budget_alert_service.check_budget_status(
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440000"
        )
        
        assert utilization == 0.0
        assert alert_level == "none"

    @pytest.mark.asyncio
    async def test_check_budget_status_zero_allocated(self, budget_alert_service, mock_db):
        """Test budget status check with zero allocated amount."""
        from datetime import date
        budget = Budget(
            id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            user_id=UUID("550e8400-e29b-41d4-a716-446655440001"),
            month=date.today(),
            category="Groceries",
            allocated_amount=Decimal("0.00"),
            spent_amount=Decimal("100.00"),
            created_at=datetime.utcnow()
        )
        
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.first.return_value = budget
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        utilization, alert_level = await budget_alert_service.check_budget_status(
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440000"
        )
        
        assert utilization == 0.0
        assert alert_level == "none"

    @pytest.mark.asyncio
    async def test_check_budget_status_none_allocated(self, budget_alert_service, mock_db):
        """Test budget status check with None allocated amount."""
        from datetime import date
        budget = Budget(
            id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            user_id=UUID("550e8400-e29b-41d4-a716-446655440001"),
            month=date.today(),
            category="Groceries",
            allocated_amount=None,
            spent_amount=Decimal("100.00"),
            created_at=datetime.utcnow()
        )
        
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.first.return_value = budget
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        utilization, alert_level = await budget_alert_service.check_budget_status(
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440000"
        )
        
        assert utilization == 0.0
        assert alert_level == "none"


class TestCreateBudgetAlert:
    @pytest.mark.asyncio
    async def test_create_budget_alert_success(self, budget_alert_service, mock_db):
        """Test creating a budget alert."""
        mock_db.commit = AsyncMock(return_value=None)
        mock_db.refresh = AsyncMock(return_value=None)
        
        alert = await budget_alert_service.create_budget_alert(
            user_id="550e8400-e29b-41d4-a716-446655440001",
            budget_id="550e8400-e29b-41d4-a716-446655440000",
            alert_level="medium",
            message="Budget alert",
            utilization=75.0
        )
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()


class TestCheckAndAlertBudget:
    @pytest.mark.asyncio
    async def test_check_and_alert_budget_disabled(self, budget_alert_service, mock_db):
        """Test check_and_alert_budget when alerts are disabled."""
        with patch('app.services.budget_alert_service.settings') as mock_settings:
            mock_settings.SEND_BUDGET_ALERTS = False
            
            result = await budget_alert_service.check_and_alert_budget(
                "550e8400-e29b-41d4-a716-446655440001",
                "550e8400-e29b-41d4-a716-446655440000"
            )
            
            assert result is False

    @pytest.mark.asyncio
    async def test_check_and_alert_budget_no_alert_needed(self, budget_alert_service, mock_db, sample_budget):
        """Test check_and_alert_budget when no alert is needed (under threshold)."""
        with patch('app.services.budget_alert_service.settings') as mock_settings:
            mock_settings.SEND_BUDGET_ALERTS = True
            mock_settings.BUDGET_ALERT_THRESHOLD = 70
            
            budget_data = {
                "category": "Groceries",
                "allocated": 10000.0,
                "spent": 5000.0
            }
            
            with patch.object(budget_alert_service, 'check_budget_status', new_callable=AsyncMock, return_value=(50.0, "none")):
                result = await budget_alert_service.check_and_alert_budget(
                    "550e8400-e29b-41d4-a716-446655440001",
                    "550e8400-e29b-41d4-a716-446655440000",
                    budget_data
                )
                
                assert result is False

    @pytest.mark.asyncio
    async def test_check_and_alert_budget_with_alert(self, budget_alert_service, mock_db, sample_budget, sample_user_profile):
        """Test check_and_alert_budget with alert needed."""
        with patch('app.services.budget_alert_service.settings') as mock_settings:
            mock_settings.SEND_BUDGET_ALERTS = True
            mock_settings.BUDGET_ALERT_THRESHOLD = 70
            
            budget_data = {
                "category": "Groceries",
                "allocated": 10000.0,
                "spent": 7500.0
            }
            
            # Setup mocks for database calls
            user_profile_scalar = MagicMock()
            user_profile_scalar.first.return_value = sample_user_profile
            user_profile_result = MagicMock()
            user_profile_result.scalars.return_value = user_profile_scalar
            
            mock_db.execute = AsyncMock(return_value=user_profile_result)
            mock_db.commit = AsyncMock(return_value=None)
            mock_db.refresh = AsyncMock(return_value=None)
            
            with patch.object(budget_alert_service, 'check_budget_status', new_callable=AsyncMock, return_value=(75.0, "medium")):
                with patch.object(budget_alert_service, 'create_budget_alert', new_callable=AsyncMock):
                    with patch.object(budget_alert_service.notification_service, 'create_notification', new_callable=AsyncMock):
                        with patch.object(budget_alert_service.email_service, 'send_budget_alert_email', new_callable=AsyncMock, return_value=True):
                            result = await budget_alert_service.check_and_alert_budget(
                                "550e8400-e29b-41d4-a716-446655440001",
                                "550e8400-e29b-41d4-a716-446655440000",
                                budget_data
                            )
                            
                            assert result is True

    @pytest.mark.asyncio
    async def test_check_and_alert_budget_budget_not_found(self, budget_alert_service, mock_db):
        """Test check_and_alert_budget when budget is not found."""
        with patch('app.services.budget_alert_service.settings') as mock_settings:
            mock_settings.SEND_BUDGET_ALERTS = True
            
            mock_scalar_obj = MagicMock()
            mock_scalar_obj.first.return_value = None
            mock_result = MagicMock()
            mock_result.scalars.return_value = mock_scalar_obj
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            result = await budget_alert_service.check_and_alert_budget(
                "550e8400-e29b-41d4-a716-446655440001",
                "550e8400-e29b-41d4-a716-446655440000"
            )
            
            assert result is False

    @pytest.mark.asyncio
    async def test_check_and_alert_budget_user_profile_not_found(self, budget_alert_service, mock_db, sample_budget):
        """Test check_and_alert_budget when user profile is not found."""
        with patch('app.services.budget_alert_service.settings') as mock_settings:
            mock_settings.SEND_BUDGET_ALERTS = True
            mock_settings.BUDGET_ALERT_THRESHOLD = 70
            
            budget_data = {
                "category": "Groceries",
                "allocated": 10000.0,
                "spent": 7500.0
            }
            
            # Setup mocks for first call (finding budget) and second call (finding user profile)
            mock_scalar_obj = MagicMock()
            mock_scalar_obj.first.return_value = None  # User profile not found
            mock_result = MagicMock()
            mock_result.scalars.return_value = mock_scalar_obj
            mock_db.execute = AsyncMock(return_value=mock_result)
            
            with patch.object(budget_alert_service, 'check_budget_status', new_callable=AsyncMock, return_value=(75.0, "medium")):
                result = await budget_alert_service.check_and_alert_budget(
                    "550e8400-e29b-41d4-a716-446655440001",
                    "550e8400-e29b-41d4-a716-446655440000",
                    budget_data
                )
                
                assert result is False

    @pytest.mark.asyncio
    async def test_check_and_alert_budget_user_without_email(self, budget_alert_service, mock_db, sample_budget, sample_user_profile):
        """Test check_and_alert_budget with user profile that has no email."""
        from datetime import date
        with patch('app.services.budget_alert_service.settings') as mock_settings:
            mock_settings.SEND_BUDGET_ALERTS = True
            mock_settings.BUDGET_ALERT_THRESHOLD = 70
            
            budget_data = {
                "category": "Groceries",
                "allocated": 10000.0,
                "spent": 7500.0
            }
            
            # User profile without email attribute
            user_profile_no_email = UserProfile(
                user_id=UUID("550e8400-e29b-41d4-a716-446655440001"),
                name="John Doe"
            )
            
            # Setup mocks for database calls
            user_profile_scalar = MagicMock()
            user_profile_scalar.first.return_value = user_profile_no_email
            user_profile_result = MagicMock()
            user_profile_result.scalars.return_value = user_profile_scalar
            
            mock_db.execute = AsyncMock(return_value=user_profile_result)
            mock_db.commit = AsyncMock(return_value=None)
            mock_db.refresh = AsyncMock(return_value=None)
            
            with patch.object(budget_alert_service, 'check_budget_status', new_callable=AsyncMock, return_value=(75.0, "medium")):
                with patch.object(budget_alert_service, 'create_budget_alert', new_callable=AsyncMock):
                    with patch.object(budget_alert_service.notification_service, 'create_notification', new_callable=AsyncMock):
                        with patch.object(budget_alert_service.email_service, 'send_budget_alert_email', new_callable=AsyncMock, return_value=True) as mock_send_email:
                            result = await budget_alert_service.check_and_alert_budget(
                                "550e8400-e29b-41d4-a716-446655440001",
                                "550e8400-e29b-41d4-a716-446655440000",
                                budget_data
                            )
                            
                            assert result is True
                            # Email should not be sent if no email attribute
                            mock_send_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_and_alert_budget_fetches_budget_data(self, budget_alert_service, mock_db, sample_budget, sample_user_profile):
        """Test check_and_alert_budget fetches budget when not provided (line 153 False branch)."""
        with patch('app.services.budget_alert_service.settings') as mock_settings:
            mock_settings.SEND_BUDGET_ALERTS = True
            mock_settings.BUDGET_ALERT_THRESHOLD = 70
            
            # No budget_data provided - force fetch from DB
            
            # Setup mocks for database calls - first for fetching budget, then for fetching user profile
            budget_scalar = MagicMock()
            budget_scalar.first.return_value = sample_budget
            budget_result = MagicMock()
            budget_result.scalars.return_value = budget_scalar
            
            user_profile_scalar = MagicMock()
            user_profile_scalar.first.return_value = sample_user_profile
            user_profile_result = MagicMock()
            user_profile_result.scalars.return_value = user_profile_scalar
            
            # Setup execute to return budget_result first time, user_profile_result second time
            mock_db.execute = AsyncMock(side_effect=[budget_result, user_profile_result])
            mock_db.commit = AsyncMock(return_value=None)
            mock_db.refresh = AsyncMock(return_value=None)
            
            with patch.object(budget_alert_service, 'check_budget_status', new_callable=AsyncMock, return_value=(75.0, "medium")):
                with patch.object(budget_alert_service, 'create_budget_alert', new_callable=AsyncMock):
                    with patch.object(budget_alert_service.notification_service, 'create_notification', new_callable=AsyncMock):
                        with patch.object(budget_alert_service.email_service, 'send_budget_alert_email', new_callable=AsyncMock, return_value=True):
                            # Call WITHOUT budget_data to force database fetch
                            result = await budget_alert_service.check_and_alert_budget(
                                str(sample_user_profile.user_id),
                                str(sample_budget.id)
                                # No budget_data parameter
                            )
                            
                            assert result is True
                            # Verify budget was fetched from DB (not provided)
                            assert mock_db.execute.call_count >= 1


class TestGetRecentAlerts:
    @pytest.mark.asyncio
    async def test_get_recent_alerts_success(self, budget_alert_service, mock_db, sample_budget_alert):
        """Test getting recent alerts."""
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.all.return_value = [sample_budget_alert]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        alerts = await budget_alert_service.get_recent_alerts(
            "550e8400-e29b-41d4-a716-446655440001"
        )
        
        assert len(alerts) == 1
        assert alerts[0] == sample_budget_alert

    @pytest.mark.asyncio
    async def test_get_recent_alerts_with_limit(self, budget_alert_service, mock_db, sample_budget_alert):
        """Test getting recent alerts with custom limit."""
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.all.return_value = [sample_budget_alert]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        alerts = await budget_alert_service.get_recent_alerts(
            "550e8400-e29b-41d4-a716-446655440001",
            limit=5
        )
        
        assert len(alerts) == 1


class TestGetUnreadAlertsCount:
    @pytest.mark.asyncio
    async def test_get_unread_alerts_count_success(self, budget_alert_service, mock_db, sample_budget_alert):
        """Test getting unread alerts count."""
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.all.return_value = [sample_budget_alert]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        count = await budget_alert_service.get_unread_alerts_count(
            "550e8400-e29b-41d4-a716-446655440001"
        )
        
        assert count == 1

    @pytest.mark.asyncio
    async def test_get_unread_alerts_count_zero(self, budget_alert_service, mock_db):
        """Test getting unread alerts count when no unread alerts."""
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        count = await budget_alert_service.get_unread_alerts_count(
            "550e8400-e29b-41d4-a716-446655440001"
        )
        
        assert count == 0


class TestMarkAlertAsRead:
    @pytest.mark.asyncio
    async def test_mark_alert_as_read_success(self, budget_alert_service, mock_db, sample_budget_alert):
        """Test marking an alert as read."""
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.first.return_value = sample_budget_alert
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock(return_value=None)
        mock_db.refresh = AsyncMock(return_value=None)
        
        alert = await budget_alert_service.mark_alert_as_read(
            "550e8400-e29b-41d4-a716-446655440003",
            "550e8400-e29b-41d4-a716-446655440001"
        )
        
        assert sample_budget_alert.is_read is True
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_alert_as_read_not_found(self, budget_alert_service, mock_db):
        """Test marking alert as read when alert not found."""
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.first.return_value = None
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        with pytest.raises(ValueError):
            await budget_alert_service.mark_alert_as_read(
                "550e8400-e29b-41d4-a716-446655440003",
                "550e8400-e29b-41d4-a716-446655440001"
            )
