"""Goal management API endpoints."""
from fastapi import APIRouter, Depends, Query, status
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

logger = get_logger(__name__)

router = APIRouter(prefix="/goals", tags=["Goals"])


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    goal_data: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
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
    service = GoalService(db)
    goal = await service.create_goal(current_user.id, goal_data)
    
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """
    Get all goals for the authenticated user.
    
    **Query Parameters:**
    - **status**: Filter by status (active, completed, paused, abandoned)
    - **goal_type**: Filter by goal type (savings, debt_payoff, etc.)
    
    **Response:** List of goals with progress information
    """
    service = GoalService(db)
    goals = await service.get_user_goals(current_user.id, status=status_filter, goal_type=goal_type)
    
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
        for goal in goals
    ]
    
    return GoalListResponse(
        success=True,
        data=goal_responses
    )


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
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
    service = GoalService(db)
    goal = await service.get_goal(goal_id, current_user.id)
    
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


@router.put("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: UUID,
    goal_data: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """
    Update a goal.
    
    **Path Parameters:**
    - **goal_id**: UUID of the goal
    
    **Request Body:** Any fields to update (all optional)
    
    **Response:** Updated goal
    """
    service = GoalService(db)
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
async def delete_goal(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
):
    """
    Delete a goal.
    
    **Path Parameters:**
    - **goal_id**: UUID of the goal
    
    **Response:** 204 No Content on success
    """
    service = GoalService(db)
    await service.delete_goal(goal_id, current_user.id)
    return None


@router.put("/{goal_id}/progress")
async def update_goal_progress(
    goal_id: UUID,
    progress_data: GoalProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
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
    service = GoalService(db)
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
    db: AsyncSession = Depends(get_data_db)
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
    service = GoalService(db)
    progress = await service.get_goal_progress(goal_id, current_user.id)
    return progress


@router.get("/summary/all", response_model=dict)
async def get_goals_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_data_db)
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
    service = GoalService(db)
    summary = await service.get_goals_summary(current_user.id)
    return summary
