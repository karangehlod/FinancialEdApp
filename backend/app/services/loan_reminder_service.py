"""Loan reminder service for payment reminders and notifications."""

from datetime import datetime, timedelta, date
from typing import Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.models.data import Loan, UserProfile
from app.services.notification_service import NotificationService
from app.services.email_service import get_email_service
from app.core.logging import get_logger
from app.config import settings

logger = get_logger(__name__)


class LoanReminderService:
    """Service for managing loan payment reminders and notifications."""

    def __init__(self, db_session: AsyncSession):
        """Initialize loan reminder service."""
        self.db_session = db_session
        self.notification_service = NotificationService(db_session)
        self.email_service = get_email_service()

    def days_until_due(self, due_date: date) -> int:
        """
        Calculate days until a due date.

        Args:
            due_date: The due date

        Returns:
            Number of days until due date (can be negative if overdue)
        """
        today = date.today()
        delta = due_date - today
        return delta.days

    async def check_loan_due_dates(
        self,
        user_id: str,
        reminder_days: int = 5,
    ) -> list[dict]:
        """
        Check for loans with upcoming due dates.

        Args:
            user_id: User UUID
            reminder_days: Number of days ahead to check for reminders

        Returns:
            List of loans with upcoming due dates
        """
        result = await self.db_session.execute(
            select(Loan).where(
                and_(
                    Loan.user_id == uuid.UUID(user_id),
                    Loan.status == "active",
                )
            )
        )

        loans = result.scalars().all()
        upcoming_loans = []

        today = date.today()
        check_date = today + timedelta(days=reminder_days)

        for loan in loans:
            days_left = self.days_until_due(loan.next_due_date)
            if 0 <= days_left <= reminder_days:
                upcoming_loans.append(
                    {
                        "loan": loan,
                        "days_until_due": days_left,
                    }
                )

        return upcoming_loans

    async def create_payment_reminder(
        self,
        user_id: str,
        loan_id: str,
        loan_data: dict,
        days_until_due: int,
    ) -> bool:
        """
        Create a payment reminder notification for a loan.

        Args:
            user_id: User UUID
            loan_id: Loan UUID
            loan_data: Loan data dictionary
            days_until_due: Days until payment is due

        Returns:
            True if reminder was created
        """
        if not settings.SEND_LOAN_REMINDERS:
            logger.debug("Loan reminders disabled in configuration")
            return False

        # Get user profile
        result = await self.db_session.execute(
            select(UserProfile).where(UserProfile.user_id == uuid.UUID(user_id))
        )
        user_profile = result.scalars().first()

        if not user_profile:
            logger.warning(f"User profile not found: {user_id}")
            return False

        # Create in-app notification
        notification_message = (
            f"Your {loan_data['loan_type']} loan EMI of ₹{loan_data['emi_amount']:,.2f} "
            f"is due on {loan_data['next_due_date']}."
        )

        await self.notification_service.create_notification(
            user_id=user_id,
            notification_type="loan_reminder",
            title=f"Loan Payment Reminder: {loan_data['loan_type']}",
            message=notification_message,
            related_resource_id=loan_id,
            related_resource_type="loan",
        )

        # Send email if user has email
        if hasattr(user_profile, "email") and user_profile.email:
            await self.email_service.send_loan_payment_reminder(
                to_email=user_profile.email,
                user_name=user_profile.name or "User",
                loan_type=loan_data["loan_type"],
                emi_amount=loan_data["emi_amount"],
                due_date=loan_data["next_due_date"].isoformat(),
                days_until_due=days_until_due,
            )

        logger.info(
            f"Loan payment reminder sent",
            user_id=user_id,
            loan_id=loan_id,
            days_until_due=days_until_due,
        )

        return True

    async def send_loan_reminders(
        self,
        user_id: str,
        reminder_days: int = 5,
    ) -> int:
        """
        Check all loans and send reminders for upcoming payments.

        Args:
            user_id: User UUID
            reminder_days: Number of days ahead to send reminders

        Returns:
            Number of reminders sent
        """
        upcoming_loans = await self.check_loan_due_dates(user_id, reminder_days)
        count = 0

        for loan_info in upcoming_loans:
            loan = loan_info["loan"]
            days_until_due = loan_info["days_until_due"]

            loan_data = {
                "loan_type": loan.loan_type,
                "emi_amount": float(loan.emi_amount),
                "next_due_date": loan.next_due_date,
            }

            if await self.create_payment_reminder(
                user_id, str(loan.id), loan_data, days_until_due
            ):
                count += 1

        return count

    async def get_overdue_loans(self, user_id: str) -> list[dict]:
        """
        Get overdue loans for a user.

        Args:
            user_id: User UUID

        Returns:
            List of overdue loans
        """
        result = await self.db_session.execute(
            select(Loan).where(
                and_(
                    Loan.user_id == uuid.UUID(user_id),
                    Loan.status == "active",
                )
            )
        )

        loans = result.scalars().all()
        overdue_loans = []

        for loan in loans:
            days_overdue = self.days_until_due(loan.next_due_date)
            if days_overdue < 0:  # Negative means overdue
                overdue_loans.append(
                    {
                        "loan": loan,
                        "days_overdue": abs(days_overdue),
                    }
                )

        return overdue_loans

    async def send_overdue_alerts(self, user_id: str) -> int:
        """
        Send alerts for overdue loan payments.

        Args:
            user_id: User UUID

        Returns:
            Number of alerts sent
        """
        overdue_loans = await self.get_overdue_loans(user_id)
        count = 0

        for loan_info in overdue_loans:
            loan = loan_info["loan"]
            days_overdue = loan_info["days_overdue"]

            # Create critical notification
            notification_message = (
                f"Your {loan.loan_type} loan payment of ₹{loan.emi_amount:,.2f} "
                f"is OVERDUE by {days_overdue} day(s). Please make the payment immediately."
            )

            await self.notification_service.create_notification(
                user_id=user_id,
                notification_type="loan_overdue_alert",
                title=f"OVERDUE: {loan.loan_type} Loan Payment",
                message=notification_message,
                related_resource_id=str(loan.id),
                related_resource_type="loan",
            )

            count += 1

        return count

    async def get_loan_stats(self, user_id: str) -> dict:
        """
        Get loan statistics for a user.

        Args:
            user_id: User UUID

        Returns:
            Dictionary with loan statistics
        """
        result = await self.db_session.execute(
            select(Loan).where(Loan.user_id == uuid.UUID(user_id))
        )

        loans = result.scalars().all()

        total_emi = 0.0
        active_loans = 0
        upcoming_reminders = 0
        overdue_count = 0

        today = date.today()
        reminder_date = today + timedelta(days=5)

        for loan in loans:
            if loan.status == "active":
                active_loans += 1
                total_emi += float(loan.emi_amount)

                days_left = self.days_until_due(loan.next_due_date)
                if 0 <= days_left <= 5:
                    upcoming_reminders += 1
                elif days_left < 0:
                    overdue_count += 1

        return {
            "total_loans": len(loans),
            "active_loans": active_loans,
            "closed_loans": len([l for l in loans if l.status == "closed"]),
            "total_emi": total_emi,
            "upcoming_reminders": upcoming_reminders,
            "overdue_payments": overdue_count,
        }
