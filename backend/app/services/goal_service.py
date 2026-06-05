"""Goal service for managing financial goals."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID
import logging

from app.db.models.data import Goal
from app.schemas.goal import GoalCreate, GoalUpdate, GoalResponse
from app.core.exceptions import GoalNotFoundError, ValidationError
from app.core.logging import get_logger
from app.core.cache_decorator import cache_response, goal_list_key
from app.core.cache_service import CacheTTL
from app.core.transaction_decorators import transactional, with_retry

logger = get_logger(__name__)


class GoalService:
    """
    Service for managing financial goals.

    Responsibilities:
    - CRUD operations for goals
    - Goal progress tracking and analytics
    - Summary calculations and reporting
    - Cache invalidation on all mutating operations (P0-9)

    Instance-based design supports dependency injection and testing.
    """

    def __init__(self, db: AsyncSession, cache_service=None):
        """
        Initialize GoalService.

        Args:
            db:            Async SQLAlchemy session.
            cache_service: Optional CacheService for Redis invalidation.
        """
        self.db = db
        self._cache = cache_service

    # ============== CRUD OPERATIONS ==============

    @transactional(rollback_on_error=True)
    @with_retry(max_attempts=3, backoff="exponential")
    async def create_goal(self, user_id: UUID, goal_data: GoalCreate) -> Goal:
        """Create a new goal for the user and invalidate the goals cache."""
        try:
            goal = Goal(
                user_id=user_id,
                goal_name=goal_data.goal_name,
                goal_type=goal_data.goal_type,
                target_amount=goal_data.target_amount,
                target_date=goal_data.target_date,
                description=goal_data.description,
                priority=goal_data.priority,
                status="active",
                current_amount=Decimal(0),
            )

            self.db.add(goal)
            await self.db.commit()
            await self.db.refresh(goal)

            await self._invalidate_goal_cache(user_id)
            logger.info(f"Goal created for user {user_id}: {goal.goal_name}")
            return goal
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating goal: {str(e)}")
            raise ValidationError(f"Failed to create goal: {str(e)}")

    async def get_goal(self, goal_id: UUID, user_id: UUID) -> Goal:
        """Get a goal by ID."""
        result = await self.db.execute(
            select(Goal).where(and_(Goal.id == goal_id, Goal.user_id == user_id))
        )
        goal = result.scalar_one_or_none()
        if not goal:
            raise GoalNotFoundError(str(goal_id))
        return goal

    async def _serialize_goals(self, goals: list[Goal]) -> list:
        return [
            {
                "id": str(g.id),
                "user_id": str(g.user_id),
                "goal_name": g.goal_name,
                "goal_type": g.goal_type,
                "target_amount": float(g.target_amount),
                "current_amount": float(g.current_amount),
                "status": g.status,
                "priority": g.priority,
            }
            for g in goals
        ]

    def _deserialize_goals(self, data: list):
        return data

    @cache_response(ttl=CacheTTL.GOAL_LIST, key_func=goal_list_key, serializer_attr="_serialize_goals", deserializer_attr="_deserialize_goals", namespace="goals")
    async def get_user_goals(
        self,
        user_id: UUID,
        status: str = None,
        goal_type: str = None,
    ) -> list[Goal]:
        """Get all goals for a user with optional filters."""
        query = select(Goal).where(Goal.user_id == user_id)
        if status:
            query = query.where(Goal.status == status)
        if goal_type:
            query = query.where(Goal.goal_type == goal_type)
        result = await self.db.execute(query.order_by(Goal.created_at.desc()))
        goals = result.scalars().all()
        return goals

    @transactional(rollback_on_error=True)
    @with_retry(max_attempts=3, backoff="exponential")
    async def update_goal(self, goal_id: UUID, user_id: UUID, goal_data: GoalUpdate) -> Goal:
        """Update a goal and invalidate the goals cache."""
        goal = await self.get_goal(goal_id, user_id)

        update_data = goal_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(goal, key, value)

        goal.updated_at = datetime.now()
        self.db.add(goal)
        await self.db.commit()
        await self.db.refresh(goal)

        await self._invalidate_goal_cache(user_id)
        logger.info(f"Goal updated: {goal_id}")
        return goal

    @transactional(rollback_on_error=True)
    async def delete_goal(self, goal_id: UUID, user_id: UUID) -> bool:
        """Delete a goal and invalidate the goals cache."""
        goal = await self.get_goal(goal_id, user_id)

        await self.db.delete(goal)
        await self.db.flush()
        await self.db.commit()

        await self._invalidate_goal_cache(user_id)
        logger.info(f"Goal deleted: {goal_id}")
        return True

    # ============== ANALYTICS OPERATIONS ==============

    @transactional(rollback_on_error=True)
    @with_retry(max_attempts=3, backoff="exponential")
    async def update_goal_progress(
        self, goal_id: UUID, user_id: UUID, current_amount: Decimal
    ) -> Goal:
        """Update goal progress and invalidate the goals cache."""
        goal = await self.get_goal(goal_id, user_id)

        goal.current_amount = current_amount
        goal.updated_at = datetime.now()

        if goal.current_amount >= goal.target_amount:
            goal.status = "completed"
            logger.info(f"Goal completed: {goal.goal_name}")

        self.db.add(goal)
        await self.db.commit()
        await self.db.refresh(goal)

        await self._invalidate_goal_cache(user_id)
        return goal

    async def get_goal_progress(self, goal_id: UUID, user_id: UUID) -> dict:
        """Get detailed goal progress."""
        goal = await self.get_goal(goal_id, user_id)

        progress_percentage = (
            (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0
        )
        days_remaining = max(0, (goal.target_date - date.today()).days)
        amount_remaining = max(Decimal(0), goal.target_amount - goal.current_amount)
        months_remaining = max(1, days_remaining // 30)
        required_monthly = float(amount_remaining / months_remaining)

        lifespan_days = (goal.target_date - goal.created_at.date()).days
        on_track = (
            progress_percentage >= (days_remaining / lifespan_days * 100)
            if lifespan_days > 0
            else False
        )

        return {
            "goal_id": goal.id,
            "goal_name": goal.goal_name,
            "progress_percentage": float(progress_percentage),
            "current_amount": float(goal.current_amount),
            "target_amount": float(goal.target_amount),
            "amount_remaining": float(amount_remaining),
            "days_remaining": days_remaining,
            "status": goal.status,
            "required_monthly_savings": required_monthly,
            "on_track": on_track,
        }

    async def get_goals_summary(self, user_id: UUID) -> dict:
        """Get summary of all goals for a user."""
        goals = await self.get_user_goals(user_id, status="active")

        total_target = sum(goal.target_amount for goal in goals)
        total_current = sum(goal.current_amount for goal in goals)

        goals_by_type: dict = {}
        for goal in goals:
            if goal.goal_type not in goals_by_type:
                goals_by_type[goal.goal_type] = {
                    "count": 0,
                    "target": Decimal(0),
                    "current": Decimal(0),
                }
            goals_by_type[goal.goal_type]["count"] += 1
            goals_by_type[goal.goal_type]["target"] += goal.target_amount
            goals_by_type[goal.goal_type]["current"] += goal.current_amount

        return {
            "total_active_goals": len(goals),
            "total_target_amount": float(total_target),
            "total_current_amount": float(total_current),
            "overall_progress_percentage": float(
                total_current / total_target * 100
            ) if total_target > 0 else 0,
            "goals_by_type": {
                k: {
                    "count": v["count"],
                    "target": float(v["target"]),
                    "current": float(v["current"]),
                    "progress": float(v["current"] / v["target"] * 100) if v["target"] > 0 else 0,
                }
                for k, v in goals_by_type.items()
            },
        }

    # ============== CACHE HELPERS ==============

    async def _invalidate_goal_cache(self, user_id: UUID) -> None:
        """Invalidate all cached goal data for this user."""
        if self._cache is None:
            return
        try:
            await self._cache.invalidate_user_goals(str(user_id))
        except Exception as exc:
            logger.warning("Goal cache invalidation failed (non-fatal): %s", exc)

    
    # ============== CRUD OPERATIONS ==============
    
    async def create_goal(self, user_id: UUID, goal_data: GoalCreate) -> Goal:
        """Create a new goal for the user."""
        try:
            goal = Goal(
                user_id=user_id,
                goal_name=goal_data.goal_name,
                goal_type=goal_data.goal_type,
                target_amount=goal_data.target_amount,
                target_date=goal_data.target_date,
                description=goal_data.description,
                priority=goal_data.priority,
                status="active",
                current_amount=Decimal(0)
            )
            
            self.db.add(goal)
            await self.db.commit()
            await self.db.refresh(goal)
            
            logger.info(f"Goal created for user {user_id}: {goal.goal_name}")
            return goal
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating goal: {str(e)}")
            raise ValidationError(f"Failed to create goal: {str(e)}")
    
    async def get_goal(self, goal_id: UUID, user_id: UUID) -> Goal:
        """Get a goal by ID."""
        result = await self.db.execute(
            select(Goal).where(
                and_(Goal.id == goal_id, Goal.user_id == user_id)
            )
        )
        goal = result.scalar_one_or_none()
        
        if not goal:
            raise GoalNotFoundError(str(goal_id))
        
        return goal
    
    async def _serialize_goals(self, goals: list[Goal]) -> list:
        return [
            {
                "id": str(g.id),
                "user_id": str(g.user_id),
                "goal_name": g.goal_name,
                "goal_type": g.goal_type,
                "target_amount": float(g.target_amount),
                "current_amount": float(g.current_amount),
                "status": g.status,
                "priority": g.priority,
            }
            for g in goals
        ]
    
    def _deserialize_goals(self, data: list):
        return data
    
    async def get_user_goals(
        self,
        user_id: UUID,
        status: str = None,
        goal_type: str = None
    ) -> list[Goal]:
        """Get all goals for a user with optional filters."""
        query = select(Goal).where(Goal.user_id == user_id)
        
        if status:
            query = query.where(Goal.status == status)
        
        if goal_type:
            query = query.where(Goal.goal_type == goal_type)
        
        result = await self.db.execute(query.order_by(Goal.created_at.desc()))
        goals = result.scalars().all()
        return goals
    
    @transactional(rollback_on_error=True)
    @with_retry(max_attempts=3, backoff="exponential")
    async def update_goal(
        self,
        goal_id: UUID,
        user_id: UUID,
        goal_data: GoalUpdate
    ) -> Goal:
        """Update a goal."""
        goal = await self.get_goal(goal_id, user_id)
        
        update_data = goal_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(goal, key, value)
        
        goal.updated_at = datetime.now()
        self.db.add(goal)
        await self.db.commit()
        await self.db.refresh(goal)
        
        logger.info(f"Goal updated: {goal_id}")
        return goal
    
    @transactional(rollback_on_error=True)
    async def delete_goal(self, goal_id: UUID, user_id: UUID) -> bool:
        """Delete a goal."""
        goal = await self.get_goal(goal_id, user_id)
        
        await self.db.delete(goal)  # ✅ Add await
        await self.db.flush()       # ✅ Add flush to ensure deletion is flushed before commit
        await self.db.commit()
        
        logger.info(f"Goal deleted: {goal_id}")
        return True
    
    # ============== ANALYTICS OPERATIONS ==============
    
    async def update_goal_progress(
        self,
        goal_id: UUID,
        user_id: UUID,
        current_amount: Decimal
    ) -> Goal:
        """Update goal progress."""
        goal = await self.get_goal(goal_id, user_id)
        
        goal.current_amount = current_amount
        goal.updated_at = datetime.now()
        
        # Check if goal is achieved
        if goal.current_amount >= goal.target_amount:
            goal.status = "completed"
            logger.info(f"Goal completed: {goal.goal_name}")
        
        self.db.add(goal)
        await self.db.commit()
        await self.db.refresh(goal)
        
        return goal
    
    async def get_goal_progress(self, goal_id: UUID, user_id: UUID) -> dict:
        """Get detailed goal progress."""
        goal = await self.get_goal(goal_id, user_id)
        
        progress_percentage = (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0
        days_remaining = max(0, (goal.target_date - date.today()).days)
        amount_remaining = max(Decimal(0), goal.target_amount - goal.current_amount)
        
        # Calculate required monthly savings
        months_remaining = max(1, days_remaining // 30)
        required_monthly = float(amount_remaining / months_remaining) if months_remaining > 0 else 0
        
        return {
            "goal_id": goal.id,
            "goal_name": goal.goal_name,
            "progress_percentage": float(progress_percentage),
            "current_amount": float(goal.current_amount),
            "target_amount": float(goal.target_amount),
            "amount_remaining": float(amount_remaining),
            "days_remaining": days_remaining,
            "status": goal.status,
            "required_monthly_savings": required_monthly,
            "on_track": progress_percentage >= (days_remaining / ((goal.target_date - goal.created_at.date()).days) * 100) if (goal.target_date - goal.created_at.date()).days > 0 else False
        }
    
    async def get_goals_summary(self, user_id: UUID) -> dict:
        """Get summary of all goals for a user."""
        goals = await self.get_user_goals(user_id, status="active")
        
        total_target = sum(goal.target_amount for goal in goals)
        total_current = sum(goal.current_amount for goal in goals)
        
        goals_by_type = {}
        for goal in goals:
            if goal.goal_type not in goals_by_type:
                goals_by_type[goal.goal_type] = {
                    "count": 0,
                    "target": Decimal(0),
                    "current": Decimal(0)
                }
            goals_by_type[goal.goal_type]["count"] += 1
            goals_by_type[goal.goal_type]["target"] += goal.target_amount
            goals_by_type[goal.goal_type]["current"] += goal.current_amount
        
        return {
            "total_active_goals": len(goals),
            "total_target_amount": float(total_target),
            "total_current_amount": float(total_current),
            "overall_progress_percentage": float(total_current / total_target * 100) if total_target > 0 else 0,
            "goals_by_type": {
                k: {
                    "count": v["count"],
                    "target": float(v["target"]),
                    "current": float(v["current"]),
                    "progress": float(v["current"] / v["target"] * 100) if v["target"] > 0 else 0
                }
                for k, v in goals_by_type.items()
            }
        }
