"""Tests for email_service.py - 100% branch coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from app.services.email_service import EmailService, get_email_service


@pytest.fixture
def mock_settings():
    with patch('app.services.email_service.settings') as mock:
        mock.SMTP_HOST = "smtp.example.com"
        mock.SMTP_PORT = 587
        mock.SMTP_USER = "user@example.com"
        mock.SMTP_PASSWORD = "password"
        mock.SMTP_FROM_EMAIL = "noreply@example.com"
        yield mock


@pytest.fixture
def email_service(mock_settings):
    return EmailService(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="user@example.com",
        smtp_password="password",
        from_email="noreply@example.com"
    )


@pytest.fixture
def unconfigured_email_service():
    """Email service with no SMTP configuration."""
    return EmailService(
        smtp_host="",
        smtp_port=0,
        smtp_user="",
        smtp_password=""
    )


class TestInitialization:
    def test_init_with_configured_settings(self):
        service = EmailService(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="password",
            from_email="noreply@example.com"
        )
        
        assert service.smtp_host == "smtp.example.com"
        assert service.smtp_port == 587
        assert service.smtp_user == "user@example.com"
        assert service.smtp_password == "password"
        assert service.from_email == "noreply@example.com"
        assert service.is_configured is True

    def test_init_with_missing_config(self):
        service = EmailService(
            smtp_host="",
            smtp_port=0,
            smtp_user="",
            smtp_password=""
        )
        
        assert service.is_configured is False

    def test_init_with_partial_config(self):
        service = EmailService(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="",
            smtp_password="password"
        )
        
        assert service.is_configured is False


class TestSendEmail:
    @pytest.mark.asyncio
    async def test_send_email_not_configured(self, unconfigured_email_service):
        """Test that email is not sent if service is not configured."""
        result = await unconfigured_email_service.send_email(
            to_email="user@example.com",
            subject="Test",
            html_content="<p>Test</p>"
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_send_email_success_without_cc_bcc(self, email_service):
        """Test successful email sending without CC/BCC."""
        with patch('app.services.email_service.asyncio.get_event_loop') as mock_loop:
            mock_executor = AsyncMock()
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=None)
            
            result = await email_service.send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                html_content="<p>Test HTML</p>",
                text_content="Test text"
            )
            
            assert result is True
            mock_loop.return_value.run_in_executor.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_success_with_cc(self, email_service):
        """Test email sending with CC recipients."""
        with patch('app.services.email_service.asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=None)
            
            result = await email_service.send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                html_content="<p>Test HTML</p>",
                cc=["cc@example.com", "cc2@example.com"]
            )
            
            assert result is True

    @pytest.mark.asyncio
    async def test_send_email_success_with_bcc(self, email_service):
        """Test email sending with BCC recipients."""
        with patch('app.services.email_service.asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=None)
            
            result = await email_service.send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                html_content="<p>Test HTML</p>",
                bcc=["bcc@example.com"]
            )
            
            assert result is True

    @pytest.mark.asyncio
    async def test_send_email_success_with_cc_and_bcc(self, email_service):
        """Test email sending with both CC and BCC recipients."""
        with patch('app.services.email_service.asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=None)
            
            result = await email_service.send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                html_content="<p>Test HTML</p>",
                cc=["cc@example.com"],
                bcc=["bcc@example.com"]
            )
            
            assert result is True

    @pytest.mark.asyncio
    async def test_send_email_without_text_content(self, email_service):
        """Test email sending without text content (only HTML)."""
        with patch('app.services.email_service.asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=None)
            
            result = await email_service.send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                html_content="<p>Test HTML</p>"
            )
            
            assert result is True

    @pytest.mark.asyncio
    async def test_send_email_failure_exception(self, email_service):
        """Test email sending when exception occurs."""
        with patch('app.services.email_service.asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(side_effect=Exception("SMTP Error"))
            
            result = await email_service.send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                html_content="<p>Test HTML</p>"
            )
            
            assert result is False


class TestSendBudgetAlertEmail:
    @pytest.mark.asyncio
    async def test_send_budget_alert_email_success(self, email_service):
        """Test sending budget alert email."""
        with patch.object(email_service, 'send_email', new_callable=AsyncMock, return_value=True):
            result = await email_service.send_budget_alert_email(
                to_email="user@example.com",
                user_name="John Doe",
                category="Groceries",
                spent=5000.00,
                allocated=10000.00,
                utilization_percent=50.0
            )
            
            assert result is True
            email_service.send_email.assert_called_once()
            call_args = email_service.send_email.call_args[0]
            assert call_args[1] == "Budget Alert: Groceries Budget at 50%"
            assert "Budget Alert" in call_args[2]


class TestSendLoanPaymentReminder:
    @pytest.mark.asyncio
    async def test_send_loan_payment_reminder_success(self, email_service):
        """Test sending loan payment reminder email."""
        with patch.object(email_service, 'send_email', new_callable=AsyncMock, return_value=True):
            result = await email_service.send_loan_payment_reminder(
                to_email="user@example.com",
                user_name="John Doe",
                loan_type="Home Loan",
                emi_amount=50000.00,
                due_date="2024-01-15",
                days_until_due=7
            )
            
            assert result is True
            email_service.send_email.assert_called_once()
            call_args = email_service.send_email.call_args[0]
            assert "7 Days" in call_args[1]


class TestSendGoalMilestoneEmail:
    @pytest.mark.asyncio
    async def test_send_goal_milestone_email_success(self, email_service):
        """Test sending goal milestone email."""
        with patch.object(email_service, 'send_email', new_callable=AsyncMock, return_value=True):
            result = await email_service.send_goal_milestone_email(
                to_email="user@example.com",
                user_name="John Doe",
                goal_name="Car Purchase",
                progress_percent=75.0,
                current_amount=750000.00,
                target_amount=1000000.00
            )
            
            assert result is True
            email_service.send_email.assert_called_once()
            call_args = email_service.send_email.call_args[0]
            assert "75%" in call_args[1]
            assert "Goal Milestone" in call_args[2]


class TestSendGoalCompletionEmail:
    @pytest.mark.asyncio
    async def test_send_goal_completion_email_success(self, email_service):
        """Test sending goal completion congratulations email."""
        with patch.object(email_service, 'send_email', new_callable=AsyncMock, return_value=True):
            result = await email_service.send_goal_completion_email(
                to_email="user@example.com",
                user_name="John Doe",
                goal_name="Car Purchase",
                target_amount=1000000.00,
                days_to_complete=365
            )
            
            assert result is True
            email_service.send_email.assert_called_once()
            call_args = email_service.send_email.call_args[0]
            assert "Congratulations" in call_args[1]
            assert "Car Purchase" in call_args[1]


class TestSendExpenseAlertEmail:
    @pytest.mark.asyncio
    async def test_send_expense_alert_email_success(self, email_service):
        """Test sending expense alert email."""
        with patch.object(email_service, 'send_email', new_callable=AsyncMock, return_value=True):
            result = await email_service.send_expense_alert_email(
                to_email="user@example.com",
                user_name="John Doe",
                category="Dining",
                amount=5000.00,
                message="High expense detected"
            )
            
            assert result is True
            email_service.send_email.assert_called_once()
            call_args = email_service.send_email.call_args[0]
            assert "Expense Alert" in call_args[1]
            assert "Dining" in call_args[1]


class TestSendGenericEmail:
    @pytest.mark.asyncio
    async def test_send_generic_email_without_action(self, email_service):
        """Test sending generic email without action button."""
        with patch.object(email_service, 'send_email', new_callable=AsyncMock, return_value=True):
            result = await email_service.send_generic_email(
                to_email="user@example.com",
                subject="Test Subject",
                title="Test Title",
                message="Test message content"
            )
            
            assert result is True
            email_service.send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_generic_email_with_action(self, email_service):
        """Test sending generic email with action button."""
        with patch.object(email_service, 'send_email', new_callable=AsyncMock, return_value=True):
            result = await email_service.send_generic_email(
                to_email="user@example.com",
                subject="Test Subject",
                title="Test Title",
                message="Test message content",
                action_url="https://example.com/action",
                action_text="Click Here"
            )
            
            assert result is True
            email_service.send_email.assert_called_once()
            call_args = email_service.send_email.call_args[0]
            assert "Click Here" in call_args[2]
            assert "https://example.com/action" in call_args[2]

    @pytest.mark.asyncio
    async def test_send_generic_email_with_only_url(self, email_service):
        """Test sending generic email with URL but no button text."""
        with patch.object(email_service, 'send_email', new_callable=AsyncMock, return_value=True):
            result = await email_service.send_generic_email(
                to_email="user@example.com",
                subject="Test Subject",
                title="Test Title",
                message="Test message content",
                action_url="https://example.com/action"
            )
            
            assert result is True
            email_service.send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_generic_email_with_only_text(self, email_service):
        """Test sending generic email with button text but no URL."""
        with patch.object(email_service, 'send_email', new_callable=AsyncMock, return_value=True):
            result = await email_service.send_generic_email(
                to_email="user@example.com",
                subject="Test Subject",
                title="Test Title",
                message="Test message content",
                action_text="Click Here"
            )
            
            assert result is True
            email_service.send_email.assert_called_once()


class TestSendSMTP:
    def test_send_smtp_success(self, email_service):
        """Test SMTP sending with successful connection."""
        with patch('app.services.email_service.smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            email_service._send_smtp(
                recipients=["recipient@example.com"],
                message="Test message"
            )
            
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("user@example.com", "password")
            mock_server.sendmail.assert_called_once()

    def test_send_smtp_failure_smtp_exception(self, email_service):
        """Test SMTP sending with SMTP exception."""
        with patch('app.services.email_service.smtplib.SMTP') as mock_smtp:
            import smtplib
            mock_server = MagicMock()
            mock_server.login.side_effect = smtplib.SMTPException("Auth failed")
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            with pytest.raises(smtplib.SMTPException):
                email_service._send_smtp(
                    recipients=["recipient@example.com"],
                    message="Test message"
                )

    def test_send_smtp_failure_general_exception(self, email_service):
        """Test SMTP sending with general exception."""
        with patch('app.services.email_service.smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_server.sendmail.side_effect = Exception("Connection error")
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            with pytest.raises(Exception):
                email_service._send_smtp(
                    recipients=["recipient@example.com"],
                    message="Test message"
                )


class TestGetEmailService:
    def test_get_email_service_singleton(self, mock_settings):
        """Test that get_email_service returns singleton instance."""
        # Reset global instance
        import app.services.email_service as email_module
        email_module._email_service = None
        
        service1 = get_email_service()
        service2 = get_email_service()
        
        assert service1 is service2

    def test_get_email_service_creates_instance(self):
        """Test that get_email_service creates EmailService instance."""
        # Reset global instance
        import app.services.email_service as email_module
        email_module._email_service = None
        
        service = get_email_service()
        
        assert isinstance(service, EmailService)
