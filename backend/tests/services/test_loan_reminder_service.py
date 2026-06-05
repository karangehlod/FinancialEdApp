"""Tests for loan_reminder_service.py - comprehensive coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.loan_reminder_service import LoanReminderService
from app.services.notification_service import NotificationService
from app.db.models.data import Loan, UserProfile


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
def loan_id():
    """Generate a test loan ID."""
    return str(uuid4())


@pytest.fixture
def sample_loan():
    """Create a sample Loan object."""
    return MagicMock(spec=Loan)


@pytest.fixture
def sample_user_profile():
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
def loan_reminder_service(mock_db):
    """Create a LoanReminderService with mocked dependencies."""
    service = LoanReminderService(mock_db)
    # Mock the notification and email services
    service.notification_service = AsyncMock(spec=NotificationService)
    service.email_service = AsyncMock()
    return service


# ============== TESTS FOR LoanReminderService ==============

class TestLoanReminderService:
    """Test LoanReminderService methods."""
    
    def test_init(self, mock_db):
        """Test LoanReminderService initialization."""
        service = LoanReminderService(mock_db)
        
        assert service.db_session == mock_db
        assert service.notification_service is not None
        assert service.email_service is not None

    def test_days_until_due_today(self):
        """Test days_until_due with due date today."""
        service = LoanReminderService(AsyncMock())
        today = date.today()
        
        result = service.days_until_due(today)
        
        assert result == 0

    def test_days_until_due_future(self):
        """Test days_until_due with future due date."""
        service = LoanReminderService(AsyncMock())
        future_date = date.today() + timedelta(days=5)
        
        result = service.days_until_due(future_date)
        
        assert result == 5

    def test_days_until_due_past(self):
        """Test days_until_due with past due date."""
        service = LoanReminderService(AsyncMock())
        past_date = date.today() - timedelta(days=3)
        
        result = service.days_until_due(past_date)
        
        assert result == -3

    @pytest.mark.asyncio
    async def test_check_loan_due_dates_with_upcoming(self, loan_reminder_service, user_id):
        """Test checking for upcoming loan due dates."""
        today = date.today()
        
        loan1 = MagicMock(spec=Loan)
        loan1.id = uuid4()
        loan1.next_due_date = today + timedelta(days=3)
        loan1.status = "active"
        loan1.loan_type = "home"
        loan1.emi_amount = Decimal("25000.00")
        
        loan2 = MagicMock(spec=Loan)
        loan2.id = uuid4()
        loan2.next_due_date = today + timedelta(days=10)
        loan2.status = "active"
        loan2.loan_type = "auto"
        loan2.emi_amount = Decimal("15000.00")
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [loan1, loan2]
        
        loan_reminder_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await loan_reminder_service.check_loan_due_dates(user_id, reminder_days=5)
        
        assert len(result) == 1  # Only loan1 is within 5 days
        assert result[0]["loan"] == loan1
        assert result[0]["days_until_due"] == 3

    @pytest.mark.asyncio
    async def test_check_loan_due_dates_all_upcoming(self, loan_reminder_service, user_id):
        """Test checking when all loans have upcoming due dates."""
        today = date.today()
        
        loan1 = MagicMock(spec=Loan)
        loan1.id = uuid4()
        loan1.next_due_date = today + timedelta(days=2)
        
        loan2 = MagicMock(spec=Loan)
        loan2.id = uuid4()
        loan2.next_due_date = today + timedelta(days=5)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [loan1, loan2]
        
        loan_reminder_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await loan_reminder_service.check_loan_due_dates(user_id, reminder_days=5)
        
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_check_loan_due_dates_no_upcoming(self, loan_reminder_service, user_id):
        """Test checking when no loans have upcoming due dates."""
        today = date.today()
        
        loan = MagicMock(spec=Loan)
        loan.id = uuid4()
        loan.next_due_date = today + timedelta(days=10)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [loan]
        
        loan_reminder_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await loan_reminder_service.check_loan_due_dates(user_id, reminder_days=5)
        
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_check_loan_due_dates_no_loans(self, loan_reminder_service, user_id):
        """Test checking when user has no loans."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        
        loan_reminder_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await loan_reminder_service.check_loan_due_dates(user_id)
        
        assert result == []

    @pytest.mark.asyncio
    async def test_check_loan_due_dates_due_today(self, loan_reminder_service, user_id):
        """Test checking when loan is due today."""
        today = date.today()
        
        loan = MagicMock(spec=Loan)
        loan.id = uuid4()
        loan.next_due_date = today
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [loan]
        
        loan_reminder_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await loan_reminder_service.check_loan_due_dates(user_id, reminder_days=5)
        
        assert len(result) == 1
        assert result[0]["days_until_due"] == 0

    @pytest.mark.asyncio
    async def test_create_payment_reminder_disabled(self, loan_reminder_service, user_id, loan_id):
        """Test creating payment reminder when reminders are disabled."""
        loan_data = {
            "loan_type": "home",
            "emi_amount": 25000.00,
            "next_due_date": date.today() + timedelta(days=3)
        }
        
        with patch('app.services.loan_reminder_service.settings.SEND_LOAN_REMINDERS', False):
            result = await loan_reminder_service.create_payment_reminder(
                user_id, loan_id, loan_data, 3
            )
        
        assert result is False
        loan_reminder_service.notification_service.create_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_payment_reminder_user_not_found(self, loan_reminder_service, user_id, loan_id):
        """Test creating payment reminder when user profile not found."""
        loan_data = {
            "loan_type": "home",
            "emi_amount": 25000.00,
            "next_due_date": date.today() + timedelta(days=3)
        }
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        
        loan_reminder_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        with patch('app.services.loan_reminder_service.settings.SEND_LOAN_REMINDERS', True):
            result = await loan_reminder_service.create_payment_reminder(
                user_id, loan_id, loan_data, 3
            )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_create_payment_reminder_success(self, loan_reminder_service, user_id, loan_id, sample_user_profile):
        """Test successfully creating a payment reminder."""
        loan_data = {
            "loan_type": "home",
            "emi_amount": 25000.00,
            "next_due_date": date.today() + timedelta(days=3)
        }
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = sample_user_profile
        
        loan_reminder_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        with patch('app.services.loan_reminder_service.settings.SEND_LOAN_REMINDERS', True):
            result = await loan_reminder_service.create_payment_reminder(
                user_id, loan_id, loan_data, 3
            )
        
        assert result is True
        loan_reminder_service.notification_service.create_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_payment_reminder_with_email(self, loan_reminder_service, user_id, loan_id):
        """Test creating payment reminder when user has email - tests line 133."""
        loan_data = {
            "loan_type": "home",
            "emi_amount": 25000.00,
            "next_due_date": date.today() + timedelta(days=3)
        }
        
        # Create user profile with email
        user_profile = MagicMock(spec=UserProfile)
        user_profile.name = "Test User"
        user_profile.email = "test@example.com"
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = user_profile
        
        loan_reminder_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        with patch('app.services.loan_reminder_service.settings.SEND_LOAN_REMINDERS', True):
            result = await loan_reminder_service.create_payment_reminder(
                user_id, loan_id, loan_data, 3
            )
        
        assert result is True
        loan_reminder_service.notification_service.create_notification.assert_called_once()
        # Verify email service was called
        loan_reminder_service.email_service.send_loan_payment_reminder.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_loan_reminders_single_loan(self, loan_reminder_service, user_id):
        """Test sending reminders for a single loan."""
        today = date.today()
        
        loan = MagicMock(spec=Loan)
        loan.id = uuid4()
        loan.next_due_date = today + timedelta(days=3)
        loan.loan_type = "home"
        loan.emi_amount = Decimal("25000.00")
        loan.status = "active"
        
        # Mock check_loan_due_dates
        loan_reminder_service.check_loan_due_dates = AsyncMock(
            return_value=[{"loan": loan, "days_until_due": 3}]
        )
        
        # Mock create_payment_reminder
        loan_reminder_service.create_payment_reminder = AsyncMock(return_value=True)
        
        result = await loan_reminder_service.send_loan_reminders(user_id)
        
        assert result == 1

    @pytest.mark.asyncio
    async def test_send_loan_reminders_multiple_loans(self, loan_reminder_service, user_id):
        """Test sending reminders for multiple loans."""
        today = date.today()
        
        loan1 = MagicMock(spec=Loan)
        loan1.id = uuid4()
        loan1.next_due_date = today + timedelta(days=2)
        loan1.loan_type = "home"
        loan1.emi_amount = Decimal("25000.00")
        
        loan2 = MagicMock(spec=Loan)
        loan2.id = uuid4()
        loan2.next_due_date = today + timedelta(days=4)
        loan2.loan_type = "auto"
        loan2.emi_amount = Decimal("15000.00")
        
        # Mock check_loan_due_dates
        loan_reminder_service.check_loan_due_dates = AsyncMock(
            return_value=[
                {"loan": loan1, "days_until_due": 2},
                {"loan": loan2, "days_until_due": 4}
            ]
        )
        
        # Mock create_payment_reminder
        loan_reminder_service.create_payment_reminder = AsyncMock(return_value=True)
        
        result = await loan_reminder_service.send_loan_reminders(user_id)
        
        assert result == 2

    @pytest.mark.asyncio
    async def test_send_loan_reminders_no_loans(self, loan_reminder_service, user_id):
        """Test sending reminders when no loans have upcoming due dates."""
        # Mock check_loan_due_dates
        loan_reminder_service.check_loan_due_dates = AsyncMock(return_value=[])
        
        result = await loan_reminder_service.send_loan_reminders(user_id)
        
        assert result == 0

    @pytest.mark.asyncio
    async def test_send_loan_reminders_some_fail(self, loan_reminder_service, user_id):
        """Test sending reminders when some reminders fail to be created."""
        today = date.today()
        
        loan1 = MagicMock(spec=Loan)
        loan1.id = uuid4()
        loan1.next_due_date = today + timedelta(days=2)
        loan1.loan_type = "home"
        loan1.emi_amount = Decimal("25000.00")
        
        loan2 = MagicMock(spec=Loan)
        loan2.id = uuid4()
        loan2.next_due_date = today + timedelta(days=4)
        loan2.loan_type = "auto"
        loan2.emi_amount = Decimal("15000.00")
        
        # Mock check_loan_due_dates
        loan_reminder_service.check_loan_due_dates = AsyncMock(
            return_value=[
                {"loan": loan1, "days_until_due": 2},
                {"loan": loan2, "days_until_due": 4}
            ]
        )
        
        # Mock create_payment_reminder - first succeeds, second fails
        loan_reminder_service.create_payment_reminder = AsyncMock(side_effect=[True, False])
        
        result = await loan_reminder_service.send_loan_reminders(user_id)
        
        assert result == 1  # Only one reminder succeeded

    @pytest.mark.asyncio
    async def test_get_overdue_loans_single_overdue(self, loan_reminder_service, user_id):
        """Test getting overdue loans when one is overdue."""
        today = date.today()
        
        loan1 = MagicMock(spec=Loan)
        loan1.id = uuid4()
        loan1.next_due_date = today - timedelta(days=5)
        loan1.status = "active"
        loan1.loan_type = "home"
        loan1.emi_amount = Decimal("25000.00")
        
        loan2 = MagicMock(spec=Loan)
        loan2.id = uuid4()
        loan2.next_due_date = today + timedelta(days=5)
        loan2.status = "active"
        loan2.loan_type = "auto"
        loan2.emi_amount = Decimal("15000.00")
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [loan1, loan2]
        
        loan_reminder_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await loan_reminder_service.get_overdue_loans(user_id)
        
        assert len(result) == 1
        assert result[0]["loan"] == loan1
        assert result[0]["days_overdue"] == 5

    @pytest.mark.asyncio
    async def test_get_overdue_loans_multiple_overdue(self, loan_reminder_service, user_id):
        """Test getting overdue loans when multiple are overdue."""
        today = date.today()
        
        loan1 = MagicMock(spec=Loan)
        loan1.id = uuid4()
        loan1.next_due_date = today - timedelta(days=3)
        loan1.status = "active"
        
        loan2 = MagicMock(spec=Loan)
        loan2.id = uuid4()
        loan2.next_due_date = today - timedelta(days=7)
        loan2.status = "active"
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [loan1, loan2]
        
        loan_reminder_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await loan_reminder_service.get_overdue_loans(user_id)
        
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_overdue_loans_none_overdue(self, loan_reminder_service, user_id):
        """Test getting overdue loans when none are overdue."""
        today = date.today()
        
        loan = MagicMock(spec=Loan)
        loan.id = uuid4()
        loan.next_due_date = today + timedelta(days=5)
        loan.status = "active"
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [loan]
        
        loan_reminder_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await loan_reminder_service.get_overdue_loans(user_id)
        
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_overdue_loans_no_loans(self, loan_reminder_service, user_id):
        """Test getting overdue loans when user has no loans."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        
        loan_reminder_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await loan_reminder_service.get_overdue_loans(user_id)
        
        assert result == []

    @pytest.mark.asyncio
    async def test_send_overdue_alerts_with_overdue_loans(self, loan_reminder_service, user_id):
        """Test sending alerts for overdue loans."""
        today = date.today()
        
        loan1 = MagicMock(spec=Loan)
        loan1.id = uuid4()
        loan1.next_due_date = today - timedelta(days=3)
        loan1.status = "active"
        loan1.loan_type = "home"
        loan1.emi_amount = Decimal("25000.00")
        
        loan2 = MagicMock(spec=Loan)
        loan2.id = uuid4()
        loan2.next_due_date = today + timedelta(days=5)
        loan2.status = "active"
        
        # Mock get_overdue_loans
        loan_reminder_service.get_overdue_loans = AsyncMock(
            return_value=[{"loan": loan1, "days_overdue": 3}]
        )
        
        result = await loan_reminder_service.send_overdue_alerts(user_id)
        
        assert result == 1
        loan_reminder_service.notification_service.create_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_overdue_alerts_no_overdue_loans(self, loan_reminder_service, user_id):
        """Test sending alerts when no loans are overdue."""
        # Mock get_overdue_loans
        loan_reminder_service.get_overdue_loans = AsyncMock(return_value=[])
        
        result = await loan_reminder_service.send_overdue_alerts(user_id)
        
        assert result == 0
        loan_reminder_service.notification_service.create_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_loan_stats_with_multiple_loans(self, loan_reminder_service, user_id):
        """Test getting loan statistics with multiple loans in different states."""
        today = date.today()
        
        loan1 = MagicMock(spec=Loan)
        loan1.status = "active"
        loan1.emi_amount = Decimal("25000.00")
        loan1.next_due_date = today + timedelta(days=3)
        
        loan2 = MagicMock(spec=Loan)
        loan2.status = "active"
        loan2.emi_amount = Decimal("15000.00")
        loan2.next_due_date = today + timedelta(days=10)
        
        loan3 = MagicMock(spec=Loan)
        loan3.status = "closed"
        loan3.emi_amount = Decimal("20000.00")
        loan3.next_due_date = today
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [loan1, loan2, loan3]
        
        loan_reminder_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await loan_reminder_service.get_loan_stats(user_id)
        
        assert result["total_loans"] == 3
        assert result["active_loans"] == 2
        assert result["closed_loans"] == 1
        assert result["total_emi"] == 40000.00
        assert result["upcoming_reminders"] == 1
        assert result["overdue_payments"] == 0

    @pytest.mark.asyncio
    async def test_get_loan_stats_with_overdue_loans(self, loan_reminder_service, user_id):
        """Test getting loan statistics with overdue loans."""
        today = date.today()
        
        loan1 = MagicMock(spec=Loan)
        loan1.status = "active"
        loan1.emi_amount = Decimal("25000.00")
        loan1.next_due_date = today - timedelta(days=3)
        
        loan2 = MagicMock(spec=Loan)
        loan2.status = "active"
        loan2.emi_amount = Decimal("15000.00")
        loan2.next_due_date = today + timedelta(days=2)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [loan1, loan2]
        
        loan_reminder_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await loan_reminder_service.get_loan_stats(user_id)
        
        assert result["total_loans"] == 2
        assert result["active_loans"] == 2
        assert result["overdue_payments"] == 1
        assert result["upcoming_reminders"] == 1

    @pytest.mark.asyncio
    async def test_get_loan_stats_no_loans(self, loan_reminder_service, user_id):
        """Test getting loan statistics when user has no loans."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        
        loan_reminder_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await loan_reminder_service.get_loan_stats(user_id)
        
        assert result["total_loans"] == 0
        assert result["active_loans"] == 0
        assert result["closed_loans"] == 0
        assert result["total_emi"] == 0.0
        assert result["upcoming_reminders"] == 0
        assert result["overdue_payments"] == 0

    @pytest.mark.asyncio
    async def test_get_loan_stats_only_closed_loans(self, loan_reminder_service, user_id):
        """Test getting loan statistics when all loans are closed."""
        loan1 = MagicMock(spec=Loan)
        loan1.status = "closed"
        loan1.emi_amount = Decimal("25000.00")
        loan1.next_due_date = date.today()
        
        loan2 = MagicMock(spec=Loan)
        loan2.status = "closed"
        loan2.emi_amount = Decimal("15000.00")
        loan2.next_due_date = date.today()
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [loan1, loan2]
        
        loan_reminder_service.db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await loan_reminder_service.get_loan_stats(user_id)
        
        assert result["total_loans"] == 2
        assert result["active_loans"] == 0
        assert result["closed_loans"] == 2
        assert result["total_emi"] == 0.0
        assert result["upcoming_reminders"] == 0
        assert result["overdue_payments"] == 0
