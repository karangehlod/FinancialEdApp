"""Repository for expense data access - handles all database operations."""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.db.models.data import Expense
from app.schemas.expense import ExpenseCreate, ExpenseUpdate, ExpenseFilter
from app.core.exceptions import (
    ExpenseNotFoundError,
    DatabaseError
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class ExpenseRepository:
    """
    Repository for expense data access.
    
    Handles all database operations for expenses including CRUD,
    filtering, querying, and aggregations. Follows the Repository Pattern
    for data access abstraction and enables easy testing through mocking.
    
    Responsibilities:
    - Create, read, update, delete operations
    - Filtering and pagination
    - Aggregation queries (summary, totals by category, etc.)
    - Database transaction management
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            db: AsyncSession for database operations
        """
        self.db = db
    
    async def create(self, user_id: UUID, expense_data: ExpenseCreate) -> Expense:
        """
        Create a new expense.
        
        Args:
            user_id: UUID of the user creating the expense
            expense_data: ExpenseCreate schema with expense details
        
        Returns:
            The created Expense object
        
        Raises:
            DatabaseError: If creation fails
        """
        try:
            new_expense = Expense(
                user_id=user_id,
                amount=expense_data.amount,
                category=expense_data.category,
                subcategory=expense_data.subcategory,
                description=expense_data.description,
                date=expense_data.date,
                merchant=expense_data.merchant,
                payment_method=expense_data.payment_method,
                is_recurring=expense_data.is_recurring or False
            )
            
            self.db.add(new_expense)
            await self.db.commit()
            await self.db.refresh(new_expense)
            
            logger.info(f"Expense created: {new_expense.id}")
            return new_expense
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating expense: {str(e)}")
            raise DatabaseError(f"Failed to create expense: {str(e)}")
    
    async def get_by_id(self, expense_id: UUID, user_id: UUID) -> Optional[Expense]:
        """
        Get a specific expense by ID with user ownership validation.
        
        Args:
            expense_id: UUID of the expense
            user_id: UUID of the user (for access control)
        
        Returns:
            Expense object if found, None otherwise
        
        Raises:
            ExpenseNotFoundError: If expense not found or user doesn't own it
        """
        try:
            result = await self.db.execute(
                select(Expense).where(
                    and_(
                        Expense.id == expense_id,
                        Expense.user_id == user_id,
                        Expense.is_deleted == False  # P1-7: Filter out soft-deleted
                    )
                )
            )
            expense = result.scalar_one_or_none()
            
            if not expense:
                logger.warning(
                    "Expense not found",
                    extra={"expense_id": str(expense_id), "user_id": str(user_id)}
                )
                raise ExpenseNotFoundError(str(expense_id))
            
            return expense
        except ExpenseNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error fetching expense: {str(e)}")
            raise DatabaseError(f"Failed to retrieve expense: {str(e)}")
    
    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
        filters: Optional[ExpenseFilter] = None
    ) -> tuple[List[Expense], int]:
        """
        Get all expenses for a user with optional filtering and pagination.
        
        Args:
            user_id: UUID of the user
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            filters: Optional ExpenseFilter with category, date range, amount range, etc.
        
        Returns:
            Tuple of (list of Expense objects, total count)
        """
        try:
            query = select(Expense).where(
                and_(
                    Expense.user_id == user_id,
                    Expense.is_deleted == False  # P1-7: Filter out soft-deleted
                )
            )
            
            # Apply filters
            if filters:
                if filters.category:
                    query = query.where(Expense.category == filters.category)
                if filters.start_date:
                    query = query.where(Expense.date >= filters.start_date)
                if filters.end_date:
                    query = query.where(Expense.date <= filters.end_date)
                if filters.min_amount:
                    query = query.where(Expense.amount >= filters.min_amount)
                if filters.max_amount:
                    query = query.where(Expense.amount <= filters.max_amount)
                if filters.merchant:
                    query = query.where(Expense.merchant.ilike(f"%{filters.merchant}%"))
                if filters.payment_method:
                    query = query.where(Expense.payment_method == filters.payment_method)
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total = await self.db.scalar(count_query)
            
            # Get paginated results
            query = query.order_by(Expense.date.desc()).offset(skip).limit(limit)
            result = await self.db.execute(query)
            expenses = result.scalars().all()
            
            return expenses, total or 0
        except Exception as e:
            logger.error(f"Error fetching user expenses: {str(e)}")
            raise DatabaseError(f"Failed to retrieve expenses: {str(e)}")
    
    async def update(
        self,
        expense_id: UUID,
        user_id: UUID,
        expense_data: ExpenseUpdate
    ) -> Expense:
        """
        Update an expense.
        
        Args:
            expense_id: UUID of the expense
            user_id: UUID of the user (for access control)
            expense_data: ExpenseUpdate schema with fields to update
        
        Returns:
            Updated Expense object
        
        Raises:
            ExpenseNotFoundError: If expense not found or user doesn't own it
            DatabaseError: If update fails
        """
        try:
            result = await self.db.execute(
                select(Expense).where(
                    and_(
                        Expense.id == expense_id,
                        Expense.user_id == user_id,
                        Expense.is_deleted == False  # P1-7: Filter out soft-deleted
                    )
                )
            )
            expense = result.scalar_one_or_none()
            
            if not expense:
                logger.warning("Expense not found for update")
                raise ExpenseNotFoundError(str(expense_id))
            
            # Update fields
            update_data = expense_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(expense, field, value)
            
            await self.db.commit()
            await self.db.refresh(expense)
            
            logger.info(f"Expense updated: {expense_id}")
            return expense
        except ExpenseNotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating expense: {str(e)}")
            raise DatabaseError(f"Failed to update expense: {str(e)}")
    
    async def delete(self, expense_id: UUID, user_id: UUID) -> bool:
        """
        Soft delete an expense.
        
        Args:
            expense_id: UUID of the expense
            user_id: UUID of the user (for access control)
        
        Returns:
            True if deleted successfully
        
        Raises:
            ExpenseNotFoundError: If expense not found or user doesn't own it
            DatabaseError: If delete fails
        """
        try:
            result = await self.db.execute(
                select(Expense).where(
                    and_(
                        Expense.id == expense_id,
                        Expense.user_id == user_id,
                        Expense.is_deleted == False  # P1-7: Can only delete active expenses
                    )
                )
            )
            expense = result.scalar_one_or_none()
            
            if not expense:
                logger.warning("Expense not found for deletion")
                raise ExpenseNotFoundError(str(expense_id))
            
            # P1-7: Soft delete - mark as deleted without removing from DB
            expense.soft_delete()
            await self.db.commit()
            
            logger.info(f"Expense soft-deleted: {expense_id}")
            return True
        except ExpenseNotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting expense: {str(e)}")
            raise DatabaseError(f"Failed to delete expense: {str(e)}")
    
    async def get_summary(
        self,
        user_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get expense summary for a period.
        
        Aggregates total spending and count of expenses for the given
        user and optional filters.
        
        Args:
            user_id: UUID of the user
            start_date: Start date for summary (inclusive)
            end_date: End date for summary (inclusive)
            category: Optional category to filter
        
        Returns:
            Dict with:
                - total_amount: Sum of all expenses
                - count: Number of expenses
                - start_date: Summary start date
                - end_date: Summary end date
        """
        # Set default dates if not provided
        if start_date is None:
            start_date = date.today().replace(day=1)
        if end_date is None:
            end_date = date.today()
        
        try:
            query = select(
                func.sum(Expense.amount).label('total'),
                func.count(Expense.id).label('count')
            ).where(
                and_(
                    Expense.user_id == user_id,
                    Expense.date >= start_date,
                    Expense.date <= end_date,
                    Expense.is_deleted == False  # P1-7: Filter out soft-deleted
                )
            )
            
            if category:
                query = query.where(Expense.category == category)
            
            result = await self.db.execute(query)
            summary = result.one()
            
            return {
                "total_amount": summary.total or Decimal(0),
                "count": summary.count or 0,
                "start_date": start_date,
                "end_date": end_date
            }
        except Exception as e:
            logger.error(f"Error getting expense summary: {str(e)}")
            raise DatabaseError(f"Failed to get summary: {str(e)}")
    
    async def get_by_date_range(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date
    ) -> List[Expense]:
        """
        Get all expenses for a user within a date range.
        
        Args:
            user_id: UUID of the user
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
        
        Returns:
            List of Expense objects ordered by date
        """
        try:
            result = await self.db.execute(
                select(Expense).where(
                    and_(
                        Expense.user_id == user_id,
                        Expense.date >= start_date,
                        Expense.date <= end_date,
                        Expense.is_deleted == False  # P1-7: Filter out soft-deleted
                    )
                ).order_by(Expense.date)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting expenses by date range: {str(e)}")
            raise DatabaseError(f"Failed to retrieve expenses: {str(e)}")
    
    async def get_by_category(
        self,
        user_id: UUID,
        category: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Expense]:
        """
        Get all expenses for a user in a specific category.
        
        Args:
            user_id: UUID of the user
            category: Category name
            start_date: Optional start date (inclusive)
            end_date: Optional end date (inclusive)
        
        Returns:
            List of Expense objects ordered by date
        """
        try:
            query = select(Expense).where(
                and_(
                    Expense.user_id == user_id,
                    Expense.category == category,
                    Expense.is_deleted == False  # P1-7: Filter out soft-deleted
                )
            )
            
            if start_date:
                query = query.where(Expense.date >= start_date)
            if end_date:
                query = query.where(Expense.date <= end_date)
            
            result = await self.db.execute(query.order_by(Expense.date))
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting category expenses: {str(e)}")
            raise DatabaseError(f"Failed to retrieve category expenses: {str(e)}")
