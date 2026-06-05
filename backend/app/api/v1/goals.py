"""Goal management API endpoints."""
from fastapi import APIRouter, Depends, Query, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.db.session import get_data_db
from app.db.models.auth import User
from app.dependencies import get_current_user
from app.schemas.goal import (
    GoalCreate,
    GoalUpdate,
    GoalResponse,
    GoalListResponse,
    GoalProgressUpdate,
    GoalMilestoneResponse
)
from app.services.goal_service import GoalService
from app.core.logging import get_logger
from app.core.cache import compute_etag, set_metadata, bump_version
from app.core.validation_decorators import validate_goal_input
from app.core.error_handling_decorators import (
    log_operation,
    audit_log,
    handle_db_errors,
)
from app.core.rate_limiting_decorators import rate_limit, apply_preset_limit
from app.config import settings
from datetime import datetime, timezone

logger = get_logger(__name__)

router = APIRouter(prefix="/goals", tags=["Goals"])


def get_goal_service(
    request: Request,
    db: AsyncSession = Depends(get_data_db),
) -> GoalService:
    """Dependency factory — builds a GoalService per request."""
    cache_service = getattr(request.app.state, "cache_service", None) if request else None
    return GoalService(db, cache_service=cache_service)


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
@apply_preset_limit("create")
@validate_goal_input
@log_operation("create_goal", include_args=False, include_result=False)
@audit_log(action="create", resource_type="goal")
@handle_db_errors(rollback_on_error=True)
async def create_goal(
    goal_data: GoalCreate,
    current_user: User = Depends(get_current_user),
    request: Request = None,
    response: Response = None,
    service: GoalService = Depends(get_goal_service),
):
    """
    Create a new financial goal.
    
    **Request Body:**
    - **goal_name**: Name of the goal
    - **goal_type**: Type of goal (savings, debt_payoff, investment, emergency_fund, other)
    - **target_amount**: Target amount to achieve (positive decimal)
    - **target_date**: Target date (YYYY-MM-DD format, must be in future)
    - **description**: Optional description
    - **priority**: Priority level (high, medium, low)
    
    **Response:** Returns the created goal with calculated progress
    
    **Errors:**
    - 400: Invalid goal data
    - 401: Unauthorized
    - 500: Server error
    """
    # injected via Depends(get_goal_service)
    goal = await service.create_goal(current_user.id, goal_data)

    # Bump metadata version so lists and related metadata become stale
    try:
        redis_client = getattr(request.app.state, "redis_client", None) if request else None
        if redis_client:
            logical_key = f"/api/v1/goals?user_id={current_user.id}"
            await bump_version(redis_client, "goals", logical_key)
    except Exception:
        pass

    return GoalResponse(
        id=goal.id,
        user_id=goal.user_id,
        goal_name=goal.goal_name,
        goal_type=goal.goal_type,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        target_date=goal.target_date,
        description=goal.description,
        priority=goal.priority,
        status=goal.status,
        progress_percentage=(goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0,
        days_remaining=(goal.target_date - goal.created_at.date()).days,
        created_at=goal.created_at.isoformat() if goal.created_at else "",
        updated_at=goal.updated_at.isoformat() if goal.updated_at else ""
    )


@router.get("", response_model=GoalListResponse)
async def get_goals(
    status_filter: Optional[str] = Query(None, alias="status"),
    goal_type: Optional[str] = None,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return (hard cap: 500)"),
    current_user: User = Depends(get_current_user),
    request: Request = None,
    response: Response = None,
    service: GoalService = Depends(get_goal_service),
):
    """
    Get all goals for the authenticated user.
    
    **Query Parameters:**
    - **status**: Filter by status (active, completed, paused, abandoned)
    - **goal_type**: Filter by goal type (savings, debt_payoff, etc.)
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Max records to return (default: 50, hard cap: 500)
    
    **Response:** List of goals with progress information
    """
    # injected via Depends(get_goal_service)
    all_goals = await service.get_user_goals(current_user.id, status=status_filter, goal_type=goal_type)

    # Apply pagination at the list level (service doesn't yet support offset/limit natively)
    paginated_goals = all_goals[skip : skip + limit]

    from datetime import date
    goal_responses = [
        GoalResponse(
            id=goal.id,
            user_id=goal.user_id,
            goal_name=goal.goal_name,
            goal_type=goal.goal_type,
            target_amount=goal.target_amount,
            current_amount=goal.current_amount,
            target_date=goal.target_date,
            description=goal.description,
            priority=goal.priority,
            status=goal.status,
            progress_percentage=(goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0,
            days_remaining=(goal.target_date - date.today()).days,
            created_at=goal.created_at.isoformat() if goal.created_at else "",
            updated_at=goal.updated_at.isoformat() if goal.updated_at else ""
        )
        for goal in paginated_goals
    ]

    return GoalListResponse(
        success=True,
        data=goal_responses,
        pagination={"skip": skip, "limit": limit, "total": len(all_goals)},
    )


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    request: Request = None,
    response: Response = None,
    service: GoalService = Depends(get_goal_service),
):
    """
    Get a specific goal by ID.
    
    **Path Parameters:**
    - **goal_id**: UUID of the goal
    
    **Response:** Goal details with progress information
    
    **Errors:**
    - 404: Goal not found
    - 401: Unauthorized
    """
    # injected via Depends(get_goal_service)
    goal = await service.get_goal(goal_id, current_user.id)

    # Attach metadata
    try:
        redis_client = getattr(request.app.state, "redis_client", None) if request else None
        payload = {
            "id": str(goal.id),
            "user_id": str(goal.user_id),
            "goal_name": goal.goal_name,
            "goal_type": goal.goal_type,
            "target_amount": float(goal.target_amount),
            "current_amount": float(goal.current_amount),
        }
        etag = compute_etag(payload)
        last_modified = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        logical_key = request.url.path if request else f"/api/v1/goals/{goal_id}"
        if redis_client:
            await set_metadata(redis_client, "goals", logical_key, etag, last_modified, ttl=settings.CACHE_TTL_GOALS)
        if response is not None:
            response.headers["ETag"] = etag
            response.headers["Last-Modified"] = last_modified
            response.headers["X-Cache"] = "MISS"
    except Exception:
        pass

    return GoalResponse(
        id=goal.id,
        user_id=goal.user_id,
        goal_name=goal.goal_name,
        goal_type=goal.goal_type,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        target_date=goal.target_date,
        description=goal.description,
        priority=goal.priority,
        status=goal.status,
        progress_percentage=(goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0,
        days_remaining=(goal.target_date - date.today()).days,
        created_at=goal.created_at.isoformat() if goal.created_at else "",
        updated_at=goal.updated_at.isoformat() if goal.updated_at else ""
    )


@router.put("/{goal_id}", response_model=GoalResponse)
@apply_preset_limit("update")
@validate_goal_input
@log_operation("update_goal", include_args=False, include_result=False)
@audit_log(action="update", resource_type="goal")
@handle_db_errors(rollback_on_error=True)
async def update_goal(
    goal_id: UUID,
    goal_data: GoalUpdate,
    current_user: User = Depends(get_current_user),
    request: Request = None,
    response: Response = None,
    service: GoalService = Depends(get_goal_service),
):
    """
    Update a goal.
    
    **Path Parameters:**
    - **goal_id**: UUID of the goal
    
    **Request Body:** Any fields to update (all optional)
    
    **Response:** Updated goal
    """
    # injected via Depends(get_goal_service)
    goal = await service.update_goal(goal_id, current_user.id, goal_data)
    
    from datetime import date
    return GoalResponse(
        id=goal.id,
        user_id=goal.user_id,
        goal_name=goal.goal_name,
        goal_type=goal.goal_type,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        target_date=goal.target_date,
        description=goal.description,
        priority=goal.priority,
        status=goal.status,
        progress_percentage=(goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0,
        days_remaining=(goal.target_date - date.today()).days,
        created_at=goal.created_at.isoformat() if goal.created_at else "",
        updated_at=goal.updated_at.isoformat() if goal.updated_at else ""
    )


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
@apply_preset_limit("delete")
@log_operation("delete_goal")
@audit_log(action="delete", resource_type="goal")
@handle_db_errors(rollback_on_error=True)
async def delete_goal(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    request: Request = None,
    response: Response = None,
    service: GoalService = Depends(get_goal_service),
):
    """
    Delete a goal.
    
    **Path Parameters:**
    - **goal_id**: UUID of the goal
    
    **Response:** 204 No Content on success
    """
    # injected via Depends(get_goal_service)
    await service.delete_goal(goal_id, current_user.id)
    return None


@router.put("/{goal_id}/progress")
async def update_goal_progress(
    goal_id: UUID,
    progress_data: GoalProgressUpdate,
    current_user: User = Depends(get_current_user),
    service: GoalService = Depends(get_goal_service),
):
    """
    Update goal progress by setting current amount.
    
    **Path Parameters:**
    - **goal_id**: UUID of the goal
    
    **Request Body:**
    - **current_amount**: Current amount accumulated (must be >= 0)
    
    **Response:** Updated goal with progress
    
    **Example Request:**
    ```json
    {
        "current_amount": 5000.50
    }
    ```
    """
    # injected via Depends(get_goal_service)
    goal = await service.update_goal_progress(
        goal_id, current_user.id, progress_data.current_amount
    )
    
    from datetime import date
    return GoalResponse(
        id=goal.id,
        user_id=goal.user_id,
        goal_name=goal.goal_name,
        goal_type=goal.goal_type,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        target_date=goal.target_date,
        description=goal.description,
        priority=goal.priority,
        status=goal.status,
        progress_percentage=(goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0,
        days_remaining=(goal.target_date - date.today()).days,
        created_at=goal.created_at.isoformat() if goal.created_at else "",
        updated_at=goal.updated_at.isoformat() if goal.updated_at else ""
    )


@router.get("/{goal_id}/progress", response_model=dict)
async def get_goal_progress(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    service: GoalService = Depends(get_goal_service),
):
    """
    Get detailed goal progress information.
    
    **Path Parameters:**
    - **goal_id**: UUID of the goal
    
    **Response:**
    - **progress_percentage**: Percentage towards goal (0-100)
    - **current_amount**: Amount saved so far
    - **target_amount**: Total target amount
    - **amount_remaining**: Amount still needed
    - **days_remaining**: Days until target date
    - **required_monthly_savings**: Monthly savings needed to meet goal
    - **on_track**: Whether goal is on track
    """
    # injected via Depends(get_goal_service)
    progress = await service.get_goal_progress(goal_id, current_user.id)
    return progress


@router.get("/summary/all", response_model=dict)
async def get_goals_summary(
    current_user: User = Depends(get_current_user),
    service: GoalService = Depends(get_goal_service),
):
    """
    Get summary of all active goals for the user.
    
    **Response:**
    - **total_active_goals**: Number of active goals
    - **total_target_amount**: Total target across all goals
    - **total_current_amount**: Total amount saved across all goals
    - **overall_progress_percentage**: Overall progress (0-100)
    - **goals_by_type**: Breakdown by goal type
    """
    # injected via Depends(get_goal_service)
    summary = await service.get_goals_summary(current_user.id)
    return summary
