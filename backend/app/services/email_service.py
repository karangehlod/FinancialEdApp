"""Email service for sending notifications and alerts."""

import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from functools import lru_cache

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailService:
    """Service for sending emails via SMTP."""

    def __init__(
        self,
        smtp_host: str = settings.SMTP_HOST,
        smtp_port: int = settings.SMTP_PORT,
        smtp_user: str = settings.SMTP_USER,
        smtp_password: str = settings.SMTP_PASSWORD,
        from_email: str = settings.SMTP_FROM_EMAIL,
    ):
        """Initialize email service with SMTP configuration."""
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.is_configured = all([smtp_host, smtp_port, smtp_user, smtp_password])

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        """
        Send an email asynchronously.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text email body (optional)
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning("Email service not configured, skipping email send")
            return False

        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.from_email
            message["To"] = to_email

            if cc:
                message["Cc"] = ", ".join(cc)

            # Attach plain text and HTML versions
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)

            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            # Prepare recipient list
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            # Send email asynchronously
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self._send_smtp, recipients, message.as_string()
            )

            logger.info(f"Email sent successfully to {to_email}", subject=subject)
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    def _send_smtp(self, recipients: List[str], message: str) -> None:
        """Send email via SMTP (blocking operation)."""
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, recipients, message)
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error while sending email: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while sending email: {str(e)}")
            raise

    async def send_budget_alert_email(
        self,
        to_email: str,
        user_name: str,
        category: str,
        spent: float,
        allocated: float,
        utilization_percent: float,
    ) -> bool:
        """
        Send a budget alert email.

        Args:
            to_email: Recipient email
            user_name: User's name
            category: Budget category
            spent: Amount spent
            allocated: Allocated budget
            utilization_percent: Budget utilization percentage

        Returns:
            True if sent successfully
        """
        subject = f"Budget Alert: {category} Budget at {utilization_percent:.0f}%"

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #d32f2f;">⚠️ Budget Alert</h2>
                <p>Hi {user_name},</p>
                <p>Your <strong>{category}</strong> budget has reached <strong>{utilization_percent:.1f}%</strong> of the allocated amount.</p>
                
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Category:</strong> {category}</p>
                    <p><strong>Spent:</strong> ₹{spent:,.2f}</p>
                    <p><strong>Allocated:</strong> ₹{allocated:,.2f}</p>
                    <p><strong>Remaining:</strong> ₹{allocated - spent:,.2f}</p>
                    <p><strong>Utilization:</strong> <span style="color: #d32f2f; font-weight: bold;">{utilization_percent:.1f}%</span></p>
                </div>
                
                <p>Please review your spending and adjust your budget if needed.</p>
                <p>Best regards,<br>Your Financial Education App</p>
            </body>
        </html>
        """

        text_content = f"""
        Budget Alert: {category} Budget at {utilization_percent:.0f}%

        Hi {user_name},
        Your {category} budget has reached {utilization_percent:.1f}% of the allocated amount.

        Category: {category}
        Spent: ₹{spent:,.2f}
        Allocated: ₹{allocated:,.2f}
        Remaining: ₹{allocated - spent:,.2f}
        Utilization: {utilization_percent:.1f}%

        Please review your spending and adjust your budget if needed.

        Best regards,
        Your Financial Education App
        """

        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_loan_payment_reminder(
        self,
        to_email: str,
        user_name: str,
        loan_type: str,
        emi_amount: float,
        due_date: str,
        days_until_due: int,
    ) -> bool:
        """
        Send a loan payment reminder email.

        Args:
            to_email: Recipient email
            user_name: User's name
            loan_type: Type of loan
            emi_amount: EMI amount
            due_date: Payment due date
            days_until_due: Days until payment is due

        Returns:
            True if sent successfully
        """
        subject = f"Loan Payment Reminder: {loan_type} EMI Due in {days_until_due} Days"

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #1976d2;">📅 Loan Payment Reminder</h2>
                <p>Hi {user_name},</p>
                <p>This is a friendly reminder that your <strong>{loan_type}</strong> loan EMI is due soon.</p>
                
                <div style="background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #1976d2;">
                    <p><strong>Loan Type:</strong> {loan_type}</p>
                    <p><strong>EMI Amount:</strong> ₹{emi_amount:,.2f}</p>
                    <p><strong>Due Date:</strong> {due_date}</p>
                    <p><strong>Days Remaining:</strong> <span style="color: #1976d2; font-weight: bold;">{days_until_due} day(s)</span></p>
                </div>
                
                <p>Please ensure timely payment to avoid any penalties or credit score impact.</p>
                <p>Best regards,<br>Your Financial Education App</p>
            </body>
        </html>
        """

        text_content = f"""
        Loan Payment Reminder: {loan_type} EMI Due in {days_until_due} Days

        Hi {user_name},
        This is a friendly reminder that your {loan_type} loan EMI is due soon.

        Loan Type: {loan_type}
        EMI Amount: ₹{emi_amount:,.2f}
        Due Date: {due_date}
        Days Remaining: {days_until_due} day(s)

        Please ensure timely payment to avoid any penalties or credit score impact.

        Best regards,
        Your Financial Education App
        """

        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_goal_milestone_email(
        self,
        to_email: str,
        user_name: str,
        goal_name: str,
        progress_percent: float,
        current_amount: float,
        target_amount: float,
    ) -> bool:
        """
        Send a goal milestone email.

        Args:
            to_email: Recipient email
            user_name: User's name
            goal_name: Goal name
            progress_percent: Progress percentage
            current_amount: Current amount saved
            target_amount: Target amount

        Returns:
            True if sent successfully
        """
        subject = f"🎉 Goal Progress: {goal_name} at {progress_percent:.0f}%"

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #388e3c;">🎉 Goal Milestone Reached!</h2>
                <p>Hi {user_name},</p>
                <p>Great progress on your <strong>{goal_name}</strong> goal!</p>
                
                <div style="background-color: #e8f5e9; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #388e3c;">
                    <p><strong>Goal:</strong> {goal_name}</p>
                    <p><strong>Progress:</strong> ₹{current_amount:,.2f} / ₹{target_amount:,.2f}</p>
                    <p><strong>Completion:</strong> <span style="color: #388e3c; font-weight: bold;">{progress_percent:.1f}%</span></p>
                    <p><strong>Remaining:</strong> ₹{target_amount - current_amount:,.2f}</p>
                </div>
                
                <p>Keep up the great work and stay focused on your financial goals!</p>
                <p>Best regards,<br>Your Financial Education App</p>
            </body>
        </html>
        """

        text_content = f"""
        Goal Milestone Reached: {goal_name} at {progress_percent:.0f}%

        Hi {user_name},
        Great progress on your {goal_name} goal!

        Goal: {goal_name}
        Progress: ₹{current_amount:,.2f} / ₹{target_amount:,.2f}
        Completion: {progress_percent:.1f}%
        Remaining: ₹{target_amount - current_amount:,.2f}

        Keep up the great work and stay focused on your financial goals!

        Best regards,
        Your Financial Education App
        """

        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_goal_completion_email(
        self,
        to_email: str,
        user_name: str,
        goal_name: str,
        target_amount: float,
        days_to_complete: int,
    ) -> bool:
        """
        Send a goal completion congratulations email.

        Args:
            to_email: Recipient email
            user_name: User's name
            goal_name: Goal name
            target_amount: Target amount achieved
            days_to_complete: Days taken to complete

        Returns:
            True if sent successfully
        """
        subject = f"🏆 Congratulations! You Completed Your {goal_name} Goal"

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #f57f17;">🏆 Congratulations!</h2>
                <p>Hi {user_name},</p>
                <p>Fantastic achievement! You've successfully completed your <strong>{goal_name}</strong> goal!</p>
                
                <div style="background-color: #fff3e0; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #f57f17;">
                    <p><strong>Goal:</strong> {goal_name}</p>
                    <p><strong>Target Amount:</strong> ₹{target_amount:,.2f}</p>
                    <p><strong>Time to Complete:</strong> {days_to_complete} days</p>
                </div>
                
                <p>This demonstrates your dedication to financial discipline and planning. Consider setting new financial goals to continue your journey!</p>
                <p>Best regards,<br>Your Financial Education App</p>
            </body>
        </html>
        """

        text_content = f"""
        Congratulations! You Completed Your {goal_name} Goal

        Hi {user_name},
        Fantastic achievement! You've successfully completed your {goal_name} goal!

        Goal: {goal_name}
        Target Amount: ₹{target_amount:,.2f}
        Time to Complete: {days_to_complete} days

        This demonstrates your dedication to financial discipline and planning. Consider setting new financial goals to continue your journey!

        Best regards,
        Your Financial Education App
        """

        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_expense_alert_email(
        self,
        to_email: str,
        user_name: str,
        category: str,
        amount: float,
        message: str,
    ) -> bool:
        """
        Send an expense alert email.

        Args:
            to_email: Recipient email
            user_name: User's name
            category: Expense category
            amount: Expense amount
            message: Alert message

        Returns:
            True if sent successfully
        """
        subject = f"Expense Alert: {category} - ₹{amount:,.2f}"

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #c62828;">💰 Expense Alert</h2>
                <p>Hi {user_name},</p>
                <p>{message}</p>
                
                <div style="background-color: #ffebee; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #c62828;">
                    <p><strong>Category:</strong> {category}</p>
                    <p><strong>Amount:</strong> ₹{amount:,.2f}</p>
                </div>
                
                <p>Keep monitoring your expenses to stay within your budget.</p>
                <p>Best regards,<br>Your Financial Education App</p>
            </body>
        </html>
        """

        text_content = f"""
        Expense Alert: {category} - ₹{amount:,.2f}

        Hi {user_name},
        {message}

        Category: {category}
        Amount: ₹{amount:,.2f}

        Keep monitoring your expenses to stay within your budget.

        Best regards,
        Your Financial Education App
        """

        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_generic_email(
        self,
        to_email: str,
        subject: str,
        title: str,
        message: str,
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
    ) -> bool:
        """
        Send a generic notification email.

        Args:
            to_email: Recipient email
            subject: Email subject
            title: Email title/heading
            message: Email body message
            action_url: Optional action URL (optional)
            action_text: Optional action button text (optional)

        Returns:
            True if sent successfully
        """
        action_button = ""
        if action_url and action_text:
            action_button = f"""
            <div style="margin: 20px 0; text-align: center;">
                <a href="{action_url}" style="background-color: #1976d2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    {action_text}
                </a>
            </div>
            """

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #1976d2;">{title}</h2>
                <p>{message}</p>
                {action_button}
                <p>Best regards,<br>Your Financial Education App</p>
            </body>
        </html>
        """

        text_content = f"""
        {title}

        {message}

        Best regards,
        Your Financial Education App
        """

        return await self.send_email(to_email, subject, html_content, text_content)


# Create a singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create the email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
