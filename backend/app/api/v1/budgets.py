"""Budget management endpoints."""
from fastapi import APIRouter, Depends, Query, status, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List
from datetime import date, datetime, timezone
import uuid

from app.db.session import get_data_db
from app.db.models.auth import User
from app.db.models.data import Budget, BudgetAlert
from app.dependencies import get_current_user
from app.core.logging import get_logger
from app.core.cache import compute_etag, set_metadata, bump_version
from app.core.validation_decorators import validate_budget_input, sanitize_request_fields
from app.core.error_handling_decorators import (
    log_operation,
    audit_log,
    handle_db_errors,
    handle_not_found_errors,
)
from app.core.rate_limiting_decorators import rate_limit, apply_preset_limit
from app.config import settings

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


def get_budget_service(
    request: Request,
    db: AsyncSession = Depends(get_data_db),
) -> BudgetService:
    """Dependency factory — builds a BudgetService per request."""
    cache_service = getattr(request.app.state, "cache_service", None) if request else None
    return BudgetService(db, cache_service=cache_service)


# ============= Summary and Analytics (STATIC ROUTES BEFORE PARAMETRIC) =============

@router.get("/summary", response_model=dict)
async def get_budget_summary(
    current_user: User = Depends(get_current_user),
    service: BudgetService = Depends(get_budget_service),
):
    """Get summary of all budgets for the current user."""
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
    service: BudgetService = Depends(get_budget_service),
):
    """Get budget alerts for the current user."""
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
    service: BudgetService = Depends(get_budget_service),
):
    """Get comprehensive budget analytics for a period."""
    analytics = await service.get_budget_analytics(
        current_user.id, start_date, end_date
    )
    return analytics


@router.put("/alerts/{alert_id}/read")
async def mark_alert_as_read(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: BudgetService = Depends(get_budget_service),
):
    """Mark a budget alert as read."""
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
@apply_preset_limit("create")
@validate_budget_input
@log_operation("create_budget", include_args=False, include_result=False)
@audit_log(action="create", resource_type="budget")
@handle_db_errors(rollback_on_error=True)
async def create_budget(
    budget_data: BudgetCreate,
    current_user: User = Depends(get_current_user),
    request: Request = None,
    response: Response = None,
    service: BudgetService = Depends(get_budget_service),
):
    """
    Create a new monthly budget for a specific category.
    """
    logger.info(
        "Budget creation request",
        user_id=str(current_user.id),
        category=budget_data.category,
        month=str(budget_data.month),
        amount=str(budget_data.allocated_amount),
    )
    
    try:
        budget = await service.create_budget(current_user.id, budget_data)
        logger.info(
            "Budget created successfully",
            user_id=str(current_user.id),
            budget_id=str(budget.id),
            category=budget.category,
        )

        # Bump namespace version so lists and related metadata become stale
        try:
            redis_client = getattr(request.app.state, "redis_client", None) if request else None
            if redis_client:
                logical_key = f"/api/v1/budgets?user_id={current_user.id}"
                await bump_version(redis_client, "budgets", logical_key)
        except Exception:
            pass

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
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return (hard cap: 500)"),
    current_user: User = Depends(get_current_user),
    request: Request = None,
    response: Response = None,
    service: BudgetService = Depends(get_budget_service),
):
    """Get list of all budgets for the authenticated user."""
    logger.debug(
        "List budgets request",
        user_id=str(current_user.id),
        active_only=active_only,
    )
    
    all_budgets = await service.get_user_budgets(
        current_user.id, start_date, end_date
    )

    # Apply pagination at the list level
    paginated_budgets = all_budgets[skip : skip + limit]

    # Convert to response schema with calculated fields
    from decimal import Decimal
    budget_responses = []
    for budget in paginated_budgets:
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
        budget_count=len(paginated_budgets),
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
    db: AsyncSession = Depends(get_data_db),
    request: Request = None,
    response: Response = None,
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
    
    # Attach ETag/Last-Modified metadata
    try:
        redis_client = getattr(request.app.state, "redis_client", None) if request else None
        payload = {
            "id": str(budget.id),
            "user_id": str(budget.user_id),
            "category": budget.category,
            "allocated_amount": float(budget.allocated_amount),
            "spent_amount": float(budget.spent_amount),
            "month": budget.month.isoformat() if hasattr(budget.month, 'isoformat') else str(budget.month),
        }
        etag = compute_etag(payload)
        last_modified = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        logical_key = request.url.path if request else f"/api/v1/budgets/{budget_id}"
        if redis_client:
            await set_metadata(redis_client, "budgets", logical_key, etag, last_modified, ttl=settings.CACHE_TTL_BUDGETS)
        if response is not None:
            response.headers["ETag"] = etag
            response.headers["Last-Modified"] = last_modified
            response.headers["X-Cache"] = "MISS"
    except Exception:
        pass

    return budget


@router.put(
    "/{budget_id}",
    response_model=BudgetResponse,
    responses={
        200: {"description": "Budget updated"},
        404: {"description": "Budget not found"},
    },
)
@apply_preset_limit("update")
@validate_budget_input
@log_operation("update_budget", include_args=False, include_result=False)
@audit_log(action="update", resource_type="budget")
@handle_db_errors(rollback_on_error=True)
async def update_budget(
    budget_id: uuid.UUID,
    budget_data: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    request: Request = None,
    response: Response = None,
    service: BudgetService = Depends(get_budget_service),
):
    """Update an existing budget."""
    logger.info(
        "Budget update request",
        user_id=str(current_user.id),
        budget_id=str(budget_id),
    )
    
    try:
        updated = await service.update_budget(budget_id, current_user.id, budget_data)

        # Bump version to invalidate metadata
        try:
            redis_client = getattr(request.app.state, "redis_client", None) if request else None
            logical_key = request.url.path if request else f"/api/v1/budgets/{budget_id}"
            if redis_client:
                await bump_version(redis_client, "budgets", logical_key)
        except Exception:
            pass

        return updated
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
@apply_preset_limit("delete")
@log_operation("delete_budget")
@audit_log(action="delete", resource_type="budget")
@handle_db_errors(rollback_on_error=True)
async def delete_budget(
    budget_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    request: Request = None,
    service: BudgetService = Depends(get_budget_service),
):
    """Delete (deactivate) a budget."""
    logger.info(
        "Budget deletion request",
        user_id=str(current_user.id),
        budget_id=str(budget_id),
    )
    
    result = await service.delete_budget(budget_id, current_user.id)

    # Bump version / invalidate metadata for this resource
    try:
        redis_client = getattr(request.app.state, "redis_client", None) if request else None
        logical_key = request.url.path if request else f"/api/v1/budgets/{budget_id}"
        if redis_client:
            await bump_version(redis_client, "budgets", logical_key)
    except Exception:
        pass

    return result
