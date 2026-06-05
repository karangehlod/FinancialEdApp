"""Repository for budget data access operations."""

from typing import Optional, List
from uuid import UUID
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.models.data import Budget
from app.schemas.budget import BudgetCreate, BudgetUpdate
from app.core.exceptions import ResourceNotFoundError


class BudgetRepository:
    """
    Repository for budget data access operations.
    
    Responsibilities:
    - CRUD operations for budgets
    - Query building and data retrieval
    - Database-level budget lookups
    
    Uses the Repository Pattern to separate data access from business logic.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize BudgetRepository with database session.
        
        Args:
            db: AsyncSession for database operations
        """
        self.db = db
    
    # ============== CREATE ==============
    
    async def create(self, user_id: UUID, budget_data: BudgetCreate) -> Budget:
        """
        Create a new budget or update if already exists for month/category.
        
        Args:
            user_id: UUID of the user
            budget_data: Budget creation data
        
        Returns:
            Created or updated Budget object
        """
        # Check if exists first
        existing = await self.get_by_user_month_category(
            user_id,
            budget_data.month,
            budget_data.category
        )
        
        if existing:
            # Update instead of creating duplicate
            existing.allocated_amount = budget_data.allocated_amount
            existing.recommended_amount = getattr(budget_data, 'recommended_amount', None)
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        
        # Create new budget
        budget = Budget(
            user_id=user_id,
            month=budget_data.month,
            category=budget_data.category,
            allocated_amount=budget_data.allocated_amount,
            spent_amount=Decimal(0),
            recommended_amount=getattr(budget_data, 'recommended_amount', None)
        )
        
        self.db.add(budget)
        await self.db.commit()
        await self.db.refresh(budget)
        return budget
    
    # ============== READ ==============
    
    async def get_by_id(self, budget_id: UUID, user_id: UUID) -> Optional[Budget]:
        """
        Get budget by ID.
        
        Args:
            budget_id: UUID of the budget
            user_id: UUID of the user (for permission check)
        
        Returns:
            Budget object or None if not found
        """
        result = await self.db.execute(
            select(Budget).where(
                and_(
                    Budget.id == budget_id,
                    Budget.user_id == user_id,
                    Budget.is_deleted == False  # P1-7: Filter out soft-deleted
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_user_month_category(
        self,
        user_id: UUID,
        month: date,
        category: str
    ) -> Optional[Budget]:
        """
        Get budget by user, month, and category.
        
        Args:
            user_id: UUID of the user
            month: Month for the budget
            category: Budget category
        
        Returns:
            Budget object or None if not found
        """
        result = await self.db.execute(
            select(Budget).where(
                and_(
                    Budget.user_id == user_id,
                    Budget.month == month,
                    Budget.category == category,
                    Budget.is_deleted == False  # P1-7: Filter out soft-deleted
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_user(
        self,
        user_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Budget]:
        """
        Get all budgets for a user with optional date filtering.
        
        Args:
            user_id: UUID of the user
            start_date: Start date for filtering (optional)
            end_date: End date for filtering (optional)
        
        Returns:
            List of Budget objects
        """
        query = select(Budget).where(
            and_(
                Budget.user_id == user_id,
                Budget.is_deleted == False  # P1-7: Filter out soft-deleted
            )
        )
        
        if start_date and end_date:
            query = query.where(
                and_(
                    Budget.month >= start_date,
                    Budget.month <= end_date
                )
            )
        
        query = query.order_by(Budget.category)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    # ============== UPDATE ==============
    
    async def update(
        self,
        budget_id: UUID,
        user_id: UUID,
        budget_data: BudgetUpdate
    ) -> Budget:
        """
        Update a budget.
        
        Args:
            budget_id: UUID of the budget to update
            user_id: UUID of the user (for permission check)
            budget_data: Budget update data
        
        Returns:
            Updated Budget object
        
        Raises:
            ResourceNotFoundError: If budget not found
        """
        budget = await self.get_by_id(budget_id, user_id)
        if not budget:
            raise ResourceNotFoundError("Budget", str(budget_id))
        
        # Update only provided fields
        for key, value in budget_data.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(budget, key, value)
        
        self.db.add(budget)
        await self.db.commit()
        await self.db.refresh(budget)
        return budget
    
    # ============== DELETE ==============
    
    async def delete(self, budget_id: UUID, user_id: UUID) -> bool:
        """
        Soft delete a budget.
        
        Args:
            budget_id: UUID of the budget to delete
            user_id: UUID of the user (for permission check)
        
        Returns:
            True if deleted, False if not found
        
        Raises:
            ResourceNotFoundError: If budget not found
        """
        budget = await self.get_by_id(budget_id, user_id)
        if not budget:
            raise ResourceNotFoundError("Budget", str(budget_id))
        
        # P1-7: Soft delete - mark as deleted without removing from DB
        budget.soft_delete()
        self.db.add(budget)
        await self.db.flush()  # ✅ Ensure soft delete is flushed before commit
        await self.db.commit()
        return True
