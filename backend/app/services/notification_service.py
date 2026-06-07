"""Notification service for managing in-app and email notifications."""

import uuid
from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.data import Notification
from app.core.logging import get_logger
from app.core.exceptions import ResourceNotFoundError

logger = get_logger(__name__)


class NotificationService:
    """Service for managing notifications."""

    def __init__(self, db_session: AsyncSession):
        """Initialize notification service."""
        self.db_session = db_session

    async def create_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        related_resource_id: Optional[str] = None,
        related_resource_type: Optional[str] = None,
    ) -> Notification:
        """
        Create a new notification.

        Args:
            user_id: User UUID
            notification_type: Type of notification (budget_alert, loan_reminder, etc.)
            title: Notification title
            message: Notification message
            related_resource_id: Related resource ID (optional)
            related_resource_type: Type of related resource (optional)

        Returns:
            Created notification
        """
        notification = Notification(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            notification_type=notification_type,
            title=title,
            message=message,
            related_resource_id=uuid.UUID(related_resource_id) if related_resource_id else None,
            related_resource_type=related_resource_type,
            is_read=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db_session.add(notification)
        await self.db_session.commit()
        await self.db_session.refresh(notification)

        logger.info(
            f"Notification created",
            user_id=user_id,
            notification_type=notification_type,
            notification_id=str(notification.id),
        )

        return notification

    async def get_notification(
        self, notification_id: str, user_id: str
    ) -> Notification:
        """
        Get a specific notification.

        Args:
            notification_id: Notification UUID
            user_id: User UUID (for authorization)

        Returns:
            Notification object

        Raises:
            ResourceNotFoundError: If notification not found or user unauthorized
        """
        result = await self.db_session.execute(
            select(Notification).where(
                and_(
                    Notification.id == uuid.UUID(notification_id),
                    Notification.user_id == uuid.UUID(user_id),
                )
            )
        )

        notification = result.scalars().first()
        if not notification:
            raise ResourceNotFoundError("Notification", notification_id)

        return notification

    async def get_notifications(
        self,
        user_id: str,
        notification_type: Optional[str] = None,
        is_read: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[Notification], int]:
        """
        Get notifications for a user with filtering and pagination.

        Args:
            user_id: User UUID
            notification_type: Filter by notification type (optional)
            is_read: Filter by read status (optional)
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            Tuple of (notifications list, total count)
        """
        # Build query
        query = select(Notification).where(Notification.user_id == uuid.UUID(user_id))

        if notification_type:
            query = query.where(Notification.notification_type == notification_type)

        if is_read is not None:
            query = query.where(Notification.is_read == is_read)

        # Get total count
        count_query = select(func.count()).select_from(
            select(Notification).where(Notification.user_id == uuid.UUID(user_id)).subquery()
        )
        count_result = await self.db_session.execute(count_query)
        total = count_result.scalar()

        # Get paginated results (ordered by created_at DESC)
        result = await self.db_session.execute(
            query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        )

        notifications = result.scalars().all()
        return notifications, total

    async def mark_as_read(
        self, notification_id: str, user_id: str
    ) -> Notification:
        """
        Mark a notification as read.

        Args:
            notification_id: Notification UUID
            user_id: User UUID

        Returns:
            Updated notification
        """
        notification = await self.get_notification(notification_id, user_id)
        notification.is_read = True
        notification.updated_at = datetime.utcnow()

        self.db_session.add(notification)
        await self.db_session.commit()
        await self.db_session.refresh(notification)

        logger.info(f"Notification marked as read", notification_id=notification_id)

        return notification

    async def mark_all_as_read(self, user_id: str) -> int:
        """
        Mark all unread notifications as read.

        Args:
            user_id: User UUID

        Returns:
            Number of notifications updated
        """
        result = await self.db_session.execute(
            select(Notification).where(
                and_(
                    Notification.user_id == uuid.UUID(user_id),
                    Notification.is_read == False,
                )
            )
        )

        notifications = result.scalars().all()
        count = len(notifications)

        for notification in notifications:
            notification.is_read = True
            notification.updated_at = datetime.utcnow()

        self.db_session.add_all(notifications)
        await self.db_session.commit()

        logger.info(f"Marked {count} notifications as read for user {user_id}")

        return count

    async def delete_notification(
        self, notification_id: str, user_id: str
    ) -> bool:
        """
        Delete a notification.

        Args:
            notification_id: Notification UUID
            user_id: User UUID

        Returns:
            True if deleted successfully
        """
        notification = await self.get_notification(notification_id, user_id)

        await self.db_session.delete(notification)
        await self.db_session.commit()

        logger.info(f"Notification deleted", notification_id=notification_id)

        return True

    async def delete_old_notifications(
        self, user_id: str, days: int = 30
    ) -> int:
        """
        Delete old notifications older than specified days.

        Args:
            user_id: User UUID
            days: Age threshold in days

        Returns:
            Number of notifications deleted
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = await self.db_session.execute(
            select(Notification).where(
                and_(
                    Notification.user_id == uuid.UUID(user_id),
                    Notification.created_at < cutoff_date,
                )
            )
        )

        notifications = result.scalars().all()
        count = len(notifications)

        for notification in notifications:
            await self.db_session.delete(notification)

        await self.db_session.commit()

        logger.info(f"Deleted {count} old notifications for user {user_id}")

        return count

    async def get_unread_count(self, user_id: str) -> int:
        """
        Get count of unread notifications.

        Args:
            user_id: User UUID

        Returns:
            Number of unread notifications
        """
        result = await self.db_session.execute(
            select(Notification).where(
                and_(
                    Notification.user_id == uuid.UUID(user_id),
                    Notification.is_read == False,
                )
            )
        )

        return len(result.scalars().all())

    async def get_notification_summary(self, user_id: str) -> dict:
        """
        Get notification summary for a user.

        Args:
            user_id: User UUID

        Returns:
            Dictionary with notification summary
        """
        result = await self.db_session.execute(
            select(Notification).where(Notification.user_id == uuid.UUID(user_id))
        )

        notifications = result.scalars().all()

        # Count by type
        by_type = {}
        unread_count = 0

        for notification in notifications:
            # Count by type
            notif_type = notification.notification_type
            if notif_type not in by_type:
                by_type[notif_type] = 0
            by_type[notif_type] += 1

            # Count unread
            if not notification.is_read:
                unread_count += 1

        return {
            "total": len(notifications),
            "unread": unread_count,
            "by_type": by_type,
        }
