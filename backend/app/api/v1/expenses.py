"""Expense management endpoints."""
from fastapi import APIRouter, Depends, Query, status, HTTPException, Request, Response
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
from app.core.cache import compute_etag, set_metadata, bump_version
from app.core.validation_decorators import validate_expense_input, sanitize_request_fields
from app.core.error_handling_decorators import (
    log_operation,
    audit_log,
    handle_db_errors,
    handle_not_found_errors,
)
from app.core.rate_limiting_decorators import rate_limit, apply_preset_limit
from app.config import settings

logger = get_logger(__name__)


router = APIRouter(prefix="/expenses", tags=["Expenses"])


def get_expense_service(
    request: Request,
    db: AsyncSession = Depends(get_data_db),
) -> ExpenseService:
    """Dependency factory — builds an ExpenseService per request."""
    cache_service = getattr(request.app.state, "cache_service", None) if request else None
    return ExpenseService(db, cache_service=cache_service)


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
@apply_preset_limit("create")
@validate_expense_input
@sanitize_request_fields(['description'], sanitizer_type='text')
@log_operation("create_expense", include_args=False, include_result=False)
@audit_log(action="create", resource_type="expense")
@handle_db_errors(rollback_on_error=True)
async def create_expense(
    expense_data: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    request: Request = None,
    response: Response = None,
    service: ExpenseService = Depends(get_expense_service),
):
    """
    Create a new expense for the authenticated user.
    
    - **amount**: Expense amount (positive decimal)
    - **category**: Expense category (e.g., Food, Transport)
    - **date**: Date of expense
    - **description**: Optional description
    """
    expense = await service.create_expense(current_user.id, expense_data)

    try:
        redis_client = getattr(request.app.state, "redis_client", None) if request else None
        if redis_client:
            logical_key = f"{request.url.path}/{expense.id}" if request else f"/api/v1/expenses/{expense.id}"
            await bump_version(redis_client, "expenses", logical_key)
    except Exception:
        pass

    return expense


# ============= Analytics and Special Routes (BEFORE parameter routes) =============

@router.get("/summary", response_model=ExpenseSummary)
async def get_expense_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    service: ExpenseService = Depends(get_expense_service),
):
    """Get summary of expenses for the authenticated user."""
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
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return (hard cap: 500)"),
    category: Optional[str] = Query(None, max_length=50),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    min_amount: Optional[float] = Query(None, ge=0),
    max_amount: Optional[float] = Query(None, ge=0),
    merchant: Optional[str] = Query(None, max_length=200),
    payment_method: Optional[str] = Query(None, max_length=50),
    current_user: User = Depends(get_current_user),
    request: Request = None,
    response: Response = None,
    service: ExpenseService = Depends(get_expense_service),
):
    """
    Get list of expenses for authenticated user with filters.
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
    
    expenses, total = await service.get_user_expenses(
        current_user.id, skip, limit, filters
    )
    
    return ExpenseListResponse(total=total, expenses=expenses)


@router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ExpenseService = Depends(get_expense_service),
):
    """Get a specific expense by ID."""
    logger.debug(
        "Get expense request",
        extra={"expense_id": str(expense_id), "user_id": str(current_user.id)}
    )
    expense = await service.get_expense(expense_id, current_user.id)
    return expense


@router.put("/{expense_id}", response_model=ExpenseResponse)
@apply_preset_limit("update")
@validate_expense_input
@sanitize_request_fields(['description'], sanitizer_type='text')
@log_operation("update_expense", include_args=False, include_result=False)
@audit_log(action="update", resource_type="expense")
@handle_db_errors(rollback_on_error=True)
async def update_expense(
    expense_id: uuid.UUID,
    expense_data: ExpenseUpdate,
    current_user: User = Depends(get_current_user),
    request: Request = None,
    response: Response = None,
    service: ExpenseService = Depends(get_expense_service),
):
    """Update an expense. Only provided fields will be updated."""
    try:
        logger.info(
            "Update expense request",
            extra={"expense_id": str(expense_id), "user_id": str(current_user.id), "data": str(expense_data)}
        )
        expense = await service.update_expense(
            expense_id, current_user.id, expense_data
        )

        try:
            redis_client = getattr(request.app.state, "redis_client", None) if request else None
            logical_key = request.url.path if request else f"/api/v1/expenses/{expense_id}"
            if redis_client:
                await bump_version(redis_client, "expenses", logical_key)
        except Exception:
            pass

        return expense
    except ExpenseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense {expense_id} not found"
        )
    except Exception as e:
        logger.error(f"Update expense error: {str(e)}", extra={"expense_id": str(expense_id)})
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to update expense: {str(e)}"
        )


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
@apply_preset_limit("delete")
@log_operation("delete_expense")
@audit_log(action="delete", resource_type="expense")
@handle_db_errors(rollback_on_error=True)
async def delete_expense(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    request: Request = None,
    service: ExpenseService = Depends(get_expense_service),
):
    """Delete an expense."""
    logger.info(
        "Delete expense request",
        extra={"expense_id": str(expense_id), "user_id": str(current_user.id)}
    )
    success = await service.delete_expense(expense_id, current_user.id)

    try:
        redis_client = getattr(request.app.state, "redis_client", None) if request else None
        logical_key = request.url.path if request else f"/api/v1/expenses/{expense_id}"
        if redis_client:
            await bump_version(redis_client, "expenses", logical_key)
    except Exception:
        pass

    return None

