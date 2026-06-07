"""Expense management endpoints."""
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select, func
from typing import Optional
from datetime import date, timedelta
import uuid

from app.db.session import get_data_db
from app.db.models.auth import User
from app.db.models.data import Expense

from app.dependencies import get_current_user
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    ExpenseListResponse,
    ExpenseSummary 
)
from app.services.expense_service import ExpenseService
from app.core.exceptions import ExpenseNotFoundError, DatabaseError
from app.core.logging import get_logger

logger = get_logger(__name__)


router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    expense_data: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """
    Create a new expense for the authenticated user.
    
    - **amount**: Expense amount (positive decimal)
    - **category**: Expense category (e.g., Food, Transport)
    - **date**: Date of expense
    - **description**: Optional description
    """
    service = ExpenseService(db)
    expense = await service.create_expense(current_user.id, expense_data)
    return expense


# ============= Analytics and Special Routes (BEFORE parameter routes) =============

@router.get("/summary", response_model=ExpenseSummary)
async def get_expense_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """Get summary of expenses for the authenticated user."""
    service = ExpenseService(db)
    summary = await service.get_expense_summary(
        current_user.id, start_date=start_date, end_date=end_date
    )
    return summary


@router.get("/categories", response_model=dict)
async def get_category_wise_expenses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """Get category-wise expense breakdown."""
    end_date = date.today()
    start_date = end_date - timedelta(days=180)
    
    try:
        result = await db.execute(
            select(
                Expense.category,
                func.sum(Expense.amount).label('total'),
                func.count(Expense.id).label('count')
            ).where(
                and_(
                    Expense.user_id == current_user.id,
                    Expense.date >= start_date,
                    Expense.date <= end_date
                )
            ).group_by(Expense.category)
        )
        
        categories = {}
        for row in result:
            categories[row[0]] = {
                "total": float(row[1]) if row[1] else 0,
                "count": row[2] or 0
            }
        
        return {"categories": categories, "period": {"start": str(start_date), "end": str(end_date)}}
    except Exception:
        return {"categories": {}, "period": {}}


@router.get("/analytics", response_model=dict)
async def get_expense_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """Get expense analytics for the current user."""
    from app.services.expense_analytics_service import ExpenseAnalyticsService
    from datetime import timedelta
    
    analytics_service = ExpenseAnalyticsService(db)
    end_date = date.today()
    start_date = end_date - timedelta(days=365)
    
    try:
        analytics = await analytics_service.calculate_expense_analytics(
            current_user.id, start_date=start_date, end_date=end_date
        )
        return analytics or {"total_amount": 0, "total_expenses": 0}
    except Exception:
        return {"total_amount": 0, "total_expenses": 0}


@router.get("/analytics/monthly", response_model=dict)
async def get_monthly_analytics(
    year: int = Query(..., description="Year (e.g., 2024)"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """Get monthly expense analytics."""
    from app.services.expense_analytics_service import ExpenseAnalyticsService
    
    try:
        analytics = ExpenseAnalyticsService(db)
        result = await analytics.get_monthly_analytics(current_user.id, year, month)
        return result
    except Exception as e:
        raise HTTPException(status_code=404, detail="Monthly analytics not found")


@router.get("/trends", response_model=dict)
async def get_expense_trends(
    months: int = Query(6, ge=1, le=24, description="Number of months to analyze"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """Get expense trends over time."""
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=months * 30)
        
        result = await db.execute(
            select(Expense).where(
                and_(
                    Expense.user_id == current_user.id,
                    Expense.date >= start_date,
                    Expense.date <= end_date
                )
            ).order_by(Expense.date)
        )
        
        expenses = result.scalars().all()
        return {"trends": [exp.dict() for exp in expenses]}
    except Exception:
        return {"trends": []}


# ============= CRUD Routes (AFTER special routes) =============

@router.get("", response_model=ExpenseListResponse)
async def list_expenses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    min_amount: Optional[float] = Query(None),
    max_amount: Optional[float] = Query(None),
    merchant: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """
    Get list of expenses for authenticated user with filters.
    
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **category**: Filter by category (optional)
    - **start_date**: Filter expenses from this date (optional)
    - **end_date**: Filter expenses until this date (optional)
    - **min_amount**: Filter expenses above this amount (optional)
    - **max_amount**: Filter expenses below this amount (optional)
    - **merchant**: Filter by merchant name (optional)
    - **payment_method**: Filter by payment method (optional)
    """
    from app.schemas.expense import ExpenseFilter
    
    filters = ExpenseFilter(
        category=category,
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount,
        max_amount=max_amount,
        merchant=merchant,
        payment_method=payment_method
    )
    
    service = ExpenseService(db)
    expenses, total = await service.get_user_expenses(
        current_user.id, skip, limit, filters
    )
    
    return ExpenseListResponse(total=total, expenses=expenses)


@router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """Get a specific expense by ID.
    
    **Path Parameters:**
    - **expense_id**: Expense UUID
    
    **Returns:** Expense details
    
    **Errors:**
    - **EXP_001**: Expense not found
    """
    logger.debug(
        "Get expense request",
        extra={"expense_id": str(expense_id), "user_id": str(current_user.id)}
    )
    service = ExpenseService(db)
    expense = await service.get_expense(expense_id, current_user.id)
    return expense


@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: uuid.UUID,
    expense_data: ExpenseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """Update an expense. Only provided fields will be updated.
    
    **Path Parameters:**
    - **expense_id**: Expense UUID
    
    **Request body:**
    - Any expense fields to update (amount, category, date, description, etc.)
    
    **Returns:** Updated expense
    
    **Errors:**
    - **EXP_001**: Expense not found
    """
    try:
        logger.info(
            "Update expense request",
            extra={"expense_id": str(expense_id), "user_id": str(current_user.id), "data": str(expense_data)}
        )
        service = ExpenseService(db)
        expense = await service.update_expense(
            expense_id, current_user.id, expense_data
        )
        return expense
    except Exception as e:
        logger.error(f"Update expense error: {str(e)}", extra={"expense_id": str(expense_id)})
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to update expense: {str(e)}"
        )


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """Delete an expense.
    
    **Path Parameters:**
    - **expense_id**: Expense UUID
    
    **Returns:** No content (204)
    
    **Errors:**
    - **EXP_001**: Expense not found
    """
    logger.info(
        "Delete expense request",
        extra={"expense_id": str(expense_id), "user_id": str(current_user.id)}
    )
    service = ExpenseService(db)
    success = await service.delete_expense(expense_id, current_user.id)
    return None

