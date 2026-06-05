"""API endpoints for notification management."""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import logging

from app.dependencies import get_current_user
from app.db.session import get_data_db
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    NotificationSummary,
)
from app.services.notification_service import NotificationService
from app.core.logging import get_logger
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_data_db
from fastapi import Request

logger = get_logger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_notification_service(
    session: AsyncSession = Depends(get_data_db),
) -> NotificationService:
    """Dependency factory — builds a NotificationService per request."""
    return NotificationService(session)


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List notifications",
    description="Get paginated list of notifications for current user",
)
async def list_notifications(
    notification_type: Optional[str] = Query(
        None, description="Filter by notification type"
    ),
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
    current_user=Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Get paginated list of notifications for the current user.

    **Query Parameters:**
    - `notification_type`: Optional - Filter by notification type (budget_alert, loan_reminder, goal_milestone, etc.)
    - `is_read`: Optional - Filter by read status (true/false)
    - `skip`: Number of items to skip (default: 0)
    - `limit`: Number of items to return (default: 20, max: 100)

    **Response:**
    - List of notifications with pagination info

    **Example:**
    ```
    GET /api/v1/notifications?notification_type=budget_alert&is_read=false&skip=0&limit=20
    ```

    **Success Response (200):**
    ```json
    {
        "notifications": [
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "550e8400-e29b-41d4-a716-446655440001",
                "notification_type": "budget_alert",
                "title": "Budget Alert: Food",
                "message": "Your Food budget has reached 85% of the allocated amount.",
                "related_resource_id": "550e8400-e29b-41d4-a716-446655440002",
                "related_resource_type": "budget",
                "is_read": false,
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-15T10:30:00"
            }
        ],
        "total": 45,
        "skip": 0,
        "limit": 20
    }
    ```

    **Error Response (401):**
    ```json
    {
        "error_code": "AUTH_001",
        "message": "Invalid or missing authentication token"
    }
    ```
    """

    notifications, total = await notification_service.get_notifications(
        user_id=str(current_user.id),
        notification_type=notification_type,
        is_read=is_read,
        skip=skip,
        limit=limit,
    )

    return NotificationListResponse(
        notifications=[
            NotificationResponse.model_validate(n) for n in notifications
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="Get notification",
    description="Get a specific notification by ID",
)
async def get_notification(
    notification_id: str,
    current_user=Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Get a specific notification by ID.

    **Path Parameters:**
    - `notification_id`: Notification UUID

    **Response:**
    - Notification details

    **Example:**
    ```
    GET /api/v1/notifications/550e8400-e29b-41d4-a716-446655440000
    ```

    **Success Response (200):**
    ```json
    {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "user_id": "550e8400-e29b-41d4-a716-446655440001",
        "notification_type": "budget_alert",
        "title": "Budget Alert: Food",
        "message": "Your Food budget has reached 85% of the allocated amount.",
        "related_resource_id": "550e8400-e29b-41d4-a716-446655440002",
        "related_resource_type": "budget",
        "is_read": false,
        "created_at": "2024-01-15T10:30:00",
        "updated_at": "2024-01-15T10:30:00"
    }
    ```

    **Error Response (404):**
    ```json
    {
        "error_code": "SRV_001",
        "message": "Notification not found"
    }
    ```
    """

    try:
        notification = await notification_service.get_notification(
            notification_id=notification_id,
            user_id=str(current_user.id),
        )
        return NotificationResponse.model_validate(notification)
    except Exception as e:
        logger.error(f"Error fetching notification: {str(e)}")
        raise HTTPException(status_code=404, detail="Notification not found")


@router.put(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark notification as read",
    description="Mark a specific notification as read",
)
async def mark_as_read(
    notification_id: str,
    current_user=Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Mark a notification as read.

    **Path Parameters:**
    - `notification_id`: Notification UUID

    **Response:**
    - Updated notification

    **Example:**
    ```
    PUT /api/v1/notifications/550e8400-e29b-41d4-a716-446655440000/read
    ```

    **Success Response (200):**
    ```json
    {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "user_id": "550e8400-e29b-41d4-a716-446655440001",
        "notification_type": "budget_alert",
        "title": "Budget Alert: Food",
        "message": "Your Food budget has reached 85% of the allocated amount.",
        "related_resource_id": "550e8400-e29b-41d4-a716-446655440002",
        "related_resource_type": "budget",
        "is_read": true,
        "created_at": "2024-01-15T10:30:00",
        "updated_at": "2024-01-15T10:35:00"
    }
    ```

    **Error Response (404):**
    ```json
    {
        "error_code": "SRV_001",
        "message": "Notification not found"
    }
    ```
    """

    try:
        notification = await notification_service.mark_as_read(
            notification_id=notification_id,
            user_id=str(current_user.id),
        )
        return NotificationResponse.model_validate(notification)
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        raise HTTPException(status_code=404, detail="Notification not found")


@router.put(
    "/mark-all/read",
    summary="Mark all notifications as read",
    description="Mark all unread notifications as read",
)
async def mark_all_as_read(
    current_user=Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Mark all unread notifications as read.

    **Response:**
    - Number of notifications updated

    **Example:**
    ```
    PUT /api/v1/notifications/mark-all/read
    ```

    **Success Response (200):**
    ```json
    {
        "message": "All notifications marked as read",
        "count": 15
    }
    ```
    """

    count = await notification_service.mark_all_as_read(user_id=str(current_user.id))

    return {"message": "All notifications marked as read", "count": count}


@router.delete(
    "/{notification_id}",
    summary="Delete notification",
    description="Delete a specific notification",
)
async def delete_notification(
    notification_id: str,
    current_user=Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Delete a notification.

    **Path Parameters:**
    - `notification_id`: Notification UUID

    **Response:**
    - Deletion confirmation

    **Example:**
    ```
    DELETE /api/v1/notifications/550e8400-e29b-41d4-a716-446655440000
    ```

    **Success Response (200):**
    ```json
    {
        "message": "Notification deleted successfully"
    }
    ```

    **Error Response (404):**
    ```json
    {
        "error_code": "SRV_001",
        "message": "Notification not found"
    }
    ```
    """

    try:
        await notification_service.delete_notification(
            notification_id=notification_id,
            user_id=str(current_user.id),
        )
        return {"message": "Notification deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting notification: {str(e)}")
        raise HTTPException(status_code=404, detail="Notification not found")


@router.get(
    "/summary/overview",
    response_model=NotificationSummary,
    summary="Get notification summary",
    description="Get summary of notifications (total, unread, by type)",
)
async def get_notification_summary(
    current_user=Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Get summary of notifications for the current user.

    **Response:**
    - Notification summary (total, unread, by type)

    **Example:**
    ```
    GET /api/v1/notifications/summary/overview
    ```

    **Success Response (200):**
    ```json
    {
        "total": 45,
        "unread": 12,
        "by_type": {
            "budget_alert": 20,
            "loan_reminder": 10,
            "goal_milestone": 15
        }
    }
    ```
    """

    summary = await notification_service.get_notification_summary(
        user_id=str(current_user.id)
    )

    return NotificationSummary(**summary)


@router.get(
    "/unread/count",
    summary="Get unread notification count",
    description="Get count of unread notifications",
)
async def get_unread_count(
    current_user=Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Get count of unread notifications.

    **Response:**
    - Number of unread notifications

    **Example:**
    ```
    GET /api/v1/notifications/unread/count
    ```

    **Success Response (200):**
    ```json
    {
        "unread_count": 12
    }
    ```
    """

    count = await notification_service.get_unread_count(user_id=str(current_user.id))

    return {"unread_count": count}
