"""Goal notification service for goal milestones and progress tracking."""

from datetime import datetime, timezone
from typing import Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.data import Goal, UserProfile
from app.services.notification_service import NotificationService
from app.services.email_service import get_email_service
from app.core.logging import get_logger
from app.config import settings

logger = get_logger(__name__)


class GoalNotificationService:
    """Service for managing goal notifications."""

    def __init__(self, db_session: AsyncSession):
        """Initialize goal notification service."""
        self.db_session = db_session
        self.notification_service = NotificationService(db_session)
        self.email_service = get_email_service()

    async def get_goal_progress_percent(
        self, goal: Goal
    ) -> float:
        """
        Calculate goal progress percentage.

        Args:
            goal: Goal object

        Returns:
            Progress percentage (0-100)
        """
        if goal.target_amount == 0 or goal.target_amount is None:
            return 0.0

        progress = (float(goal.current_amount) / float(goal.target_amount)) * 100
        return min(progress, 100.0)  # Cap at 100%

    async def check_milestone_progress(
        self,
        user_id: str,
        goal_id: str,
        goal: Optional[Goal] = None,
    ) -> tuple[float, bool]:
        """
        Check if a goal has reached a milestone (25%, 50%, 75%, 100%).

        Args:
            user_id: User UUID
            goal_id: Goal UUID
            goal: Goal object (optional, will fetch if not provided)

        Returns:
            Tuple of (progress_percent, is_milestone)
        """
        if not goal:
            result = await self.db_session.execute(
                select(Goal).where(Goal.id == goal_id)
            )
            goal = result.scalars().first()

            if not goal:
                return 0.0, False

        progress = await self.get_goal_progress_percent(goal)

        # Check for milestones
        milestones = [25, 50, 75, 100]
        is_milestone = any(abs(progress - m) < 1 for m in milestones)

        return progress, is_milestone

    async def send_milestone_notification(
        self,
        user_id: str,
        goal_id: str,
        goal_data: dict,
        progress_percent: float,
    ) -> bool:
        """
        Send a milestone achievement notification.

        Args:
            user_id: User UUID
            goal_id: Goal UUID
            goal_data: Goal data dictionary
            progress_percent: Current progress percentage

        Returns:
            True if notification was sent
        """
        if not settings.SEND_GOAL_NOTIFICATIONS:
            logger.debug("Goal notifications disabled in configuration")
            return False

        # Get user profile
        result = await self.db_session.execute(
            select(UserProfile).where(UserProfile.user_id == uuid.UUID(user_id))
        )
        user_profile = result.scalars().first()

        if not user_profile:
            logger.warning(f"User profile not found: {user_id}")
            return False

        # Determine which milestone we hit
        milestone = None
        if progress_percent >= 100:
            milestone = 100
        elif progress_percent >= 75:
            milestone = 75
        elif progress_percent >= 50:
            milestone = 50
        elif progress_percent >= 25:
            milestone = 25

        if not milestone:
            return False

        # Create notification
        if milestone == 100:
            notification_message = (
                f"Congratulations! You've completed your {goal_data['goal_name']} goal! 🎉"
            )
            notification_title = f"Goal Completed: {goal_data['goal_name']}"
        else:
            notification_message = (
                f"Great progress! You've reached {milestone}% of your {goal_data['goal_name']} goal. "
                f"Current: ₹{goal_data['current_amount']:,.2f} / Target: ₹{goal_data['target_amount']:,.2f}"
            )
            notification_title = f"Goal Milestone: {goal_data['goal_name']} - {milestone}%"

        await self.notification_service.create_notification(
            user_id=user_id,
            notification_type="goal_milestone",
            title=notification_title,
            message=notification_message,
            related_resource_id=goal_id,
            related_resource_type="goal",
        )

        # Send email
        if hasattr(user_profile, "email") and user_profile.email:
            if milestone == 100:
                await self.email_service.send_goal_completion_email(
                    to_email=user_profile.email,
                    user_name=user_profile.name or "User",
                    goal_name=goal_data["goal_name"],
                    target_amount=goal_data["target_amount"],
                    days_to_complete=(
                        datetime.now(timezone.utc).date() - goal_data["created_date"]
                    ).days,
                )
            else:
                await self.email_service.send_goal_milestone_email(
                    to_email=user_profile.email,
                    user_name=user_profile.name or "User",
                    goal_name=goal_data["goal_name"],
                    progress_percent=progress_percent,
                    current_amount=goal_data["current_amount"],
                    target_amount=goal_data["target_amount"],
                )

        logger.info(
            f"Goal milestone notification sent",
            user_id=user_id,
            goal_id=goal_id,
            milestone=milestone,
            progress=progress_percent,
        )

        return True

    async def check_goals_on_track(
        self,
        user_id: str,
    ) -> list[dict]:
        """
        Check which goals are on track and which are behind schedule.

        Args:
            user_id: User UUID

        Returns:
            List of goal status dictionaries
        """
        result = await self.db_session.execute(
            select(Goal).where(
                Goal.user_id == uuid.UUID(user_id),
                Goal.status == "active",
            )
        )

        goals = result.scalars().all()
        goal_statuses = []

        today = datetime.now(timezone.utc).date()

        for goal in goals:
            progress = await self.get_goal_progress_percent(goal)

            # Calculate expected progress based on time elapsed
            days_elapsed = (today - goal.created_at.date()).days
            days_total = (goal.target_date - goal.created_at.date()).days

            if days_total <= 0:
                expected_progress = 100.0
            else:
                expected_progress = (days_elapsed / days_total) * 100

            is_on_track = progress >= (expected_progress - 10)  # 10% buffer

            goal_statuses.append(
                {
                    "goal_id": str(goal.id),
                    "goal_name": goal.goal_name,
                    "progress": progress,
                    "expected_progress": min(expected_progress, 100.0),
                    "is_on_track": is_on_track,
                    "days_remaining": (goal.target_date - today).days,
                }
            )

        return goal_statuses

    async def send_off_track_alerts(
        self,
        user_id: str,
    ) -> int:
        """
        Send alerts for goals that are off track.

        Args:
            user_id: User UUID

        Returns:
            Number of alerts sent
        """
        goal_statuses = await self.check_goals_on_track(user_id)
        count = 0

        for status in goal_statuses:
            if not status["is_on_track"]:
                # Create alert notification
                notification_message = (
                    f"Your {status['goal_name']} goal is off track. "
                    f"Current progress: {status['progress']:.1f}% "
                    f"(Expected: {status['expected_progress']:.1f}%). "
                    f"You have {status['days_remaining']} days remaining."
                )

                await self.notification_service.create_notification(
                    user_id=user_id,
                    notification_type="goal_off_track",
                    title=f"Goal Alert: {status['goal_name']} Off Track",
                    message=notification_message,
                    related_resource_id=status["goal_id"],
                    related_resource_type="goal",
                )

                count += 1

        return count

    async def get_goal_summary(
        self,
        user_id: str,
    ) -> dict:
        """
        Get summary of all goals for a user.

        Args:
            user_id: User UUID

        Returns:
            Dictionary with goal summary
        """
        result = await self.db_session.execute(
            select(Goal).where(Goal.user_id == uuid.UUID(user_id))
        )

        goals = result.scalars().all()

        summary = {
            "total_goals": len(goals),
            "active_goals": 0,
            "completed_goals": 0,
            "paused_goals": 0,
            "total_target": 0.0,
            "total_current": 0.0,
            "avg_progress": 0.0,
        }

        progress_values = []

        for goal in goals:
            if goal.status == "active":
                summary["active_goals"] += 1
            elif goal.status == "completed":
                summary["completed_goals"] += 1
            elif goal.status == "paused":
                summary["paused_goals"] += 1

            summary["total_target"] += float(goal.target_amount)
            summary["total_current"] += float(goal.current_amount)

            progress = await self.get_goal_progress_percent(goal)
            progress_values.append(progress)

        if progress_values:
            summary["avg_progress"] = sum(progress_values) / len(progress_values)

        return summary
