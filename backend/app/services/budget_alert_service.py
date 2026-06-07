"""Budget alert service for monitoring and alerting on budget overages."""

from datetime import datetime
from typing import Optional
from decimal import Decimal
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.models.data import BudgetAlert, Budget, UserProfile
from app.models.budget import FinancialProfile
from app.services.notification_service import NotificationService
from app.services.email_service import get_email_service
from app.core.logging import get_logger
from app.config import settings

logger = get_logger(__name__)


class BudgetAlertService:
    """Service for managing budget alerts and notifications."""

    def __init__(self, db_session: AsyncSession):
        """Initialize budget alert service."""
        self.db_session = db_session
        self.notification_service = NotificationService(db_session)
        self.email_service = get_email_service()

    async def check_budget_status(
        self, user_id: str, budget_id: str
    ) -> tuple[float, str]:
        """
        Check current budget utilization status.

        Args:
            user_id: User UUID
            budget_id: Budget UUID

        Returns:
            Tuple of (utilization_percentage, alert_level)
        """
        result = await self.db_session.execute(
            select(Budget).where(
                and_(
                    Budget.id == uuid.UUID(budget_id),
                    Budget.user_id == uuid.UUID(user_id),
                )
            )
        )

        budget = result.scalars().first()
        if not budget:
            return 0.0, "none"

        if budget.allocated_amount == 0 or budget.allocated_amount is None:
            return 0.0, "none"

        # Calculate utilization percentage
        utilization = (
            float(budget.spent_amount) / float(budget.allocated_amount) * 100
        )

        # Determine alert level
        alert_level = "none"
        if utilization >= 100:
            alert_level = "critical"
        elif utilization >= 90:
            alert_level = "high"
        elif utilization >= settings.BUDGET_ALERT_THRESHOLD:
            alert_level = "medium"

        return utilization, alert_level

    async def create_budget_alert(
        self,
        user_id: str,
        budget_id: str,
        alert_level: str,
        message: str,
        utilization: float,
    ) -> BudgetAlert:
        """
        Create a budget alert.

        Args:
            user_id: User UUID
            budget_id: Budget UUID
            alert_level: Alert level (low, medium, high, critical)
            message: Alert message
            utilization: Budget utilization percentage

        Returns:
            Created BudgetAlert object
        """
        budget_alert = BudgetAlert(
            budget_id=uuid.UUID(budget_id),
            user_id=uuid.UUID(user_id),
            alert_level=alert_level,
            message=message,
            utilization_at_alert=Decimal(str(utilization)),
            is_read=False,
        )

        self.db_session.add(budget_alert)
        await self.db_session.commit()
        await self.db_session.refresh(budget_alert)

        logger.info(
            f"Budget alert created",
            user_id=user_id,
            budget_id=budget_id,
            alert_level=alert_level,
        )

        return budget_alert

    async def check_and_alert_budget(
        self,
        user_id: str,
        budget_id: str,
        budget_data: Optional[dict] = None,
    ) -> bool:
        """
        Check budget status and send alerts if needed.

        Args:
            user_id: User UUID
            budget_id: Budget UUID
            budget_data: Optional budget data dict (for efficiency)

        Returns:
            True if alert was sent, False otherwise
        """
        if not settings.SEND_BUDGET_ALERTS:
            logger.debug("Budget alerts disabled in configuration")
            return False

        # Get budget data if not provided
        if not budget_data:
            result = await self.db_session.execute(
                select(Budget).where(
                    and_(
                        Budget.id == uuid.UUID(budget_id),
                        Budget.user_id == uuid.UUID(user_id),
                    )
                )
            )
            budget = result.scalars().first()
            if not budget:
                logger.warning(f"Budget not found: {budget_id}")
                return False

            budget_data = {
                "category": budget.category,
                "allocated": float(budget.allocated_amount),
                "spent": float(budget.spent_amount),
            }

        # Check status
        utilization, alert_level = await self.check_budget_status(user_id, budget_id)

        if alert_level == "none":
            return False

        # Get user profile for notification
        result = await self.db_session.execute(
            select(UserProfile).where(UserProfile.user_id == uuid.UUID(user_id))
        )
        user_profile = result.scalars().first()

        if not user_profile:
            logger.warning(f"User profile not found: {user_id}")
            return False

        # Create in-app notification
        notification_message = f"Your {budget_data['category']} budget has reached {utilization:.1f}% of the allocated amount."

        await self.notification_service.create_notification(
            user_id=user_id,
            notification_type="budget_alert",
            title=f"Budget Alert: {budget_data['category']}",
            message=notification_message,
            related_resource_id=budget_id,
            related_resource_type="budget",
        )

        # Create alert record
        await self.create_budget_alert(
            user_id=user_id,
            budget_id=budget_id,
            alert_level=alert_level,
            message=notification_message,
            utilization=utilization,
        )

        # Send email if notifications are enabled
        if hasattr(user_profile, "email") and user_profile.email:
            await self.email_service.send_budget_alert_email(
                to_email=user_profile.email,
                user_name=user_profile.name or "User",
                category=budget_data["category"],
                spent=budget_data["spent"],
                allocated=budget_data["allocated"],
                utilization_percent=utilization,
            )

        logger.info(
            f"Budget alert sent",
            user_id=user_id,
            budget_id=budget_id,
            utilization=utilization,
            alert_level=alert_level,
        )

        return True

    async def get_recent_alerts(
        self, user_id: str, limit: int = 10
    ) -> list[BudgetAlert]:
        """
        Get recent budget alerts for a user.

        Args:
            user_id: User UUID
            limit: Number of alerts to retrieve

        Returns:
            List of BudgetAlert objects
        """
        result = await self.db_session.execute(
            select(BudgetAlert)
            .where(BudgetAlert.user_id == uuid.UUID(user_id))
            .order_by(BudgetAlert.created_at.desc())
            .limit(limit)
        )

        return result.scalars().all()

    async def get_unread_alerts_count(self, user_id: str) -> int:
        """
        Get count of unread budget alerts.

        Args:
            user_id: User UUID

        Returns:
            Number of unread alerts
        """
        result = await self.db_session.execute(
            select(BudgetAlert).where(
                and_(
                    BudgetAlert.user_id == uuid.UUID(user_id),
                    ~BudgetAlert.is_read,
                )
            )
        )

        return len(result.scalars().all())

    async def mark_alert_as_read(self, alert_id: str, user_id: str) -> BudgetAlert:
        """
        Mark a budget alert as read.

        Args:
            alert_id: Alert UUID
            user_id: User UUID (for authorization)

        Returns:
            Updated BudgetAlert object
        """
        result = await self.db_session.execute(
            select(BudgetAlert).where(
                and_(
                    BudgetAlert.id == uuid.UUID(alert_id),
                    BudgetAlert.user_id == uuid.UUID(user_id),
                )
            )
        )

        alert = result.scalars().first()
        if not alert:
            raise ValueError(f"Alert not found: {alert_id}")

        alert.is_read = True
        self.db_session.add(alert)
        await self.db_session.commit()
        await self.db_session.refresh(alert)

        return alert
