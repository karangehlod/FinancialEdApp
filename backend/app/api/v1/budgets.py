"""Budget management endpoints."""
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List
from datetime import date
import uuid

from app.db.session import get_data_db
from app.db.models.auth import User
from app.db.models.data import Budget, BudgetAlert
from app.dependencies import get_current_user
from app.core.logging import get_logger

logger = get_logger(__name__)
from app.schemas.budget import (
    BudgetCreate,
    BudgetUpdate,
    BudgetResponse,
    BudgetAnalytics,
    BudgetWithAlert,
    MonthlyBudgetSummary,
    BudgetAlertResponse
)
from app.schemas.loan import BudgetLoanIntegration
from app.services.budget_service import BudgetService


router = APIRouter(prefix="/budgets", tags=["Budget Management"])


# ============= Summary and Analytics (STATIC ROUTES BEFORE PARAMETRIC) =============

@router.get("/summary", response_model=dict)
async def get_budget_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """Get summary of all budgets for the current user."""
    service = BudgetService(db)
    budgets = await service.get_user_budgets(current_user.id)
    
    total_allocated = sum(float(b.allocated_amount) for b in budgets)
    total_spent = sum(float(b.spent_amount) for b in budgets)
    utilization = (total_spent / total_allocated * 100) if total_allocated > 0 else 0
    
    return {
        "total_allocated": total_allocated,
        "total_spent": total_spent,
        "remaining": total_allocated - total_spent,
        "utilization_percentage": utilization,
        "budget_count": len(budgets)
    }


@router.get("/alerts", response_model=dict)
async def get_budget_alerts(
    unread_only: bool = Query(False, description="Return only unread alerts"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """Get budget alerts for the current user."""
    service = BudgetService(db)
    alerts = await service.get_user_alerts(current_user.id, unread_only)
    # Convert ORM objects to dicts
    alerts_data = [
        {
            "id": str(alert.id),
            "budget_id": str(alert.budget_id),
            "alert_level": alert.alert_level,
            "message": alert.message,
            "is_read": alert.is_read
        }
        for alert in alerts
    ]
    return {"alerts": alerts_data}


@router.get("/recommendations", response_model=dict)
async def get_budget_recommendations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """Get personalized budget recommendations based on spending patterns."""
    # Return empty recommendations for now
    return {"recommendations": []}


@router.get("/insights/yearly", response_model=dict)
async def get_yearly_spending_insights(
    year: int = Query(..., description="Year for analysis"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """Get yearly spending insights and patterns."""
    # Return empty insights for now
    return {"insights": []}


@router.get("/analytics/summary", response_model=BudgetAnalytics)
async def get_budget_analytics(
    start_date: date = Query(..., description="Analysis start date"),
    end_date: date = Query(..., description="Analysis end date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """Get comprehensive budget analytics for a period."""
    service = BudgetService(db)
    analytics = await service.get_budget_analytics(
        current_user.id, start_date, end_date
    )
    return analytics


@router.put("/alerts/{alert_id}/read")
async def mark_alert_as_read(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """Mark a budget alert as read."""
    service = BudgetService(db)
    success = await service.mark_alert_as_read(alert_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    return {"message": "Alert marked as read"}


# ============= Budget CRUD Endpoints =============

@router.post(
    "",
    response_model=BudgetResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Budget created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "user_id": "550e8400-e29b-41d4-a716-446655440001",
                        "month": "2026-01-01",
                        "category": "FOOD",
                        "allocated_amount": "5000.00",
                        "spent_amount": "1250.50",
                        "created_at": "2026-01-14T10:00:00",
                    }
                }
            },
        },
        400: {
            "description": "Invalid budget data or duplicate category",
        },
        422: {
            "description": "Validation error",
        },
    },
)
async def create_budget(
    budget_data: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """
    Create a new monthly budget for a specific category.

    **Request body:**
    - **month**: Budget month (YYYY-MM-01 format)
    - **category**: Expense category (FOOD, TRANSPORT, ENTERTAINMENT, etc.)
    - **allocated_amount**: Monthly budget limit (must be positive)
    - **recommended_amount**: Optional recommended budget

    **Returns:** Created budget with spending summary

    **Errors:**
    - **BDG_002**: Duplicate category for the month
    - **VAL_001**: Invalid budget amount
    - **BDG_003**: Negative or zero amount

    **Example:**
    ```json
    {
        "month": "2026-01-01",
        "category": "FOOD",
        "allocated_amount": 5000
    }
    ```

    **Notes:**
    - Each category can only have one budget per month
    - Budget alerts are automatically generated at 90% and 100% utilization
    - Spending is tracked automatically as expenses are created
    """
    logger.info(
        "Budget creation request",
        user_id=str(current_user.id),
        category=budget_data.category,
        month=str(budget_data.month),
        amount=str(budget_data.allocated_amount),
    )
    
    try:
        service = BudgetService(db)
        budget = await service.create_budget(current_user.id, budget_data)
        logger.info(
            "Budget created successfully",
            user_id=str(current_user.id),
            budget_id=str(budget.id),
            category=budget.category,
        )
        return budget
    except Exception as e:
        logger.error(
            "Budget creation failed",
            user_id=str(current_user.id),
            category=budget_data.category,
            exc_info=True,
        )
        raise


@router.get(
    "",
    response_model=List[BudgetWithAlert],
    responses={
        200: {
            "description": "List of user budgets",
        },
    },
)
async def list_budgets(
    active_only: bool = Query(True, description="Show only active budgets"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """
    Get list of all budgets for the authenticated user.

    **Query Parameters:**
    - **active_only**: Show only active budgets (default: true)
    - **start_date**: Filter budgets from this month
    - **end_date**: Filter budgets until this month

    **Returns:** List of budgets with current spending and alert status

    **Example:**
    ```bash
    GET /budgets/?active_only=true&start_date=2026-01-01&end_date=2026-01-31
    ```

    **Notes:**
    - Returns budgets with calculated spending and utilization percentage
    - Includes any active budget alerts
    - Supports filtering by date range
    """
    logger.debug(
        "List budgets request",
        user_id=str(current_user.id),
        active_only=active_only,
    )
    
    service = BudgetService(db)
    budgets = await service.get_user_budgets(
        current_user.id, start_date, end_date
    )
    
    # Convert to response schema with calculated fields
    from decimal import Decimal
    budget_responses = []
    for budget in budgets:
        remaining = budget.allocated_amount - budget.spent_amount
        utilization = float((budget.spent_amount / budget.allocated_amount * 100)) if budget.allocated_amount > 0 else 0.0
        alert_status = "critical" if utilization >= 100 else "warning" if utilization >= 90 else "ok"
        
        budget_responses.append(BudgetWithAlert(
            id=budget.id,
            user_id=budget.user_id,
            category=budget.category,
            allocated_amount=budget.allocated_amount,
            spent_amount=budget.spent_amount,
            month=budget.month,
            recommended_amount=budget.recommended_amount,
            remaining_amount=remaining,
            utilization_percentage=utilization,
            alert_status=alert_status,
            created_at=budget.created_at
        ))
    
    logger.debug(
        "Budgets retrieved",
        user_id=str(current_user.id),
        budget_count=len(budgets),
    )
    return budget_responses


@router.get(
    "/{budget_id}",
    response_model=BudgetResponse,
    responses={
        200: {"description": "Budget details"},
        404: {"description": "Budget not found"},
    },
)
async def get_budget(
    budget_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """
    Get details of a specific budget.

    **Path Parameters:**
    - **budget_id**: Budget UUID

    **Returns:** Budget with spending summary and utilization

    **Errors:**
    - **BDG_001**: Budget not found

    **Example:**
    ```bash
    GET /budgets/550e8400-e29b-41d4-a716-446655440000
    ```
    """
    logger.debug(
        "Get budget request",
        user_id=str(current_user.id),
        budget_id=str(budget_id),
    )
    
    result = await db.execute(
        select(Budget).where(
            and_(
                Budget.id == budget_id,
                Budget.user_id == current_user.id
            )
        )
    )
    budget = result.scalar_one_or_none()
    
    if not budget:
        logger.warning(
            "Budget not found",
            user_id=str(current_user.id),
            budget_id=str(budget_id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )
    
    return budget


@router.put(
    "/{budget_id}",
    response_model=BudgetResponse,
    responses={
        200: {"description": "Budget updated"},
        404: {"description": "Budget not found"},
    },
)
async def update_budget(
    budget_id: uuid.UUID,
    budget_data: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """
    Update an existing budget.

    **Path Parameters:**
    - **budget_id**: Budget UUID

    **Request body:**
    - **allocated_amount**: New monthly budget limit (optional)
    - **recommended_amount**: New recommended budget (optional)

    **Returns:** Updated budget

    **Errors:**
    - **BDG_001**: Budget not found
    - **VAL_001**: Invalid budget amount

    **Example:**
    ```json
    {
        "allocated_amount": 6000
    }
    ```
    """
    logger.info(
        "Budget update request",
        user_id=str(current_user.id),
        budget_id=str(budget_id),
    )
    
    try:
        service = BudgetService(db)
        budget = await service.update_budget(
            budget_id, current_user.id, budget_data
        )
        logger.info(
            "Budget updated successfully",
            user_id=str(current_user.id),
            budget_id=str(budget_id),
        )
        return budget
    except Exception as e:
        logger.error(
            "Budget update failed",
            user_id=str(current_user.id),
            budget_id=str(budget_id),
            exc_info=True,
        )
        raise


@router.delete(
    "/{budget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Budget deleted"},
        404: {"description": "Budget not found"},
    },
)
async def delete_budget(
    budget_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """
    Delete (deactivate) a budget.

    **Path Parameters:**
    - **budget_id**: Budget UUID

    **Returns:** No content (204)

    **Errors:**
    - **BDG_001**: Budget not found

    **Example:**
    ```bash
    DELETE /budgets/550e8400-e29b-41d4-a716-446655440000
    ```
    **Notes:**
    - Deleting a budget deactivates it but keeps the historical data
    - Expenses already recorded against the budget are not deleted
    """
    logger.info(
        "Budget deletion request",
        user_id=str(current_user.id),
        budget_id=str(budget_id),
    )
    
    service = BudgetService(db)
    success = await service.delete_budget(budget_id, current_user.id)
    if not success:
        logger.warning(
            "Budget not found for deletion",
            user_id=str(current_user.id),
            budget_id=str(budget_id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )
    
    logger.info(
        "Budget deleted successfully",
        user_id=str(current_user.id),
        budget_id=str(budget_id),
    )
