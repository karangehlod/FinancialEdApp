"""Pydantic schemas for notifications."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


class NotificationBase(BaseModel):
    """Base notification schema."""

    notification_type: str = Field(..., description="Type of notification")
    title: str = Field(..., max_length=255, description="Notification title")
    message: str = Field(..., description="Notification message")
    related_resource_id: Optional[UUID] = Field(None, description="Related resource ID")
    related_resource_type: Optional[str] = Field(
        None, max_length=50, description="Type of related resource"
    )


class NotificationCreate(NotificationBase):
    """Schema for creating a notification."""

    pass


class NotificationUpdate(BaseModel):
    """Schema for updating a notification."""

    is_read: bool = Field(..., description="Read status")


class NotificationResponse(NotificationBase):
    """Schema for notification response."""

    id: UUID = Field(..., description="Notification ID")
    user_id: UUID = Field(..., description="User ID")
    is_read: bool = Field(..., description="Read status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Schema for notification list response."""

    notifications: list[NotificationResponse] = Field(
        ..., description="List of notifications"
    )
    total: int = Field(..., description="Total number of notifications")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Number of items returned")


class NotificationSummary(BaseModel):
    """Schema for notification summary."""

    total: int = Field(..., description="Total notifications")
    unread: int = Field(..., description="Unread notifications")
    by_type: dict = Field(..., description="Notifications count by type")


class NotificationPreferences(BaseModel):
    """Schema for notification preferences."""

    budget_alerts_enabled: bool = Field(
        True, description="Enable budget alert notifications"
    )
    loan_reminders_enabled: bool = Field(
        True, description="Enable loan payment reminder notifications"
    )
    goal_notifications_enabled: bool = Field(
        True, description="Enable goal milestone notifications"
    )
    expense_alerts_enabled: bool = Field(
        True, description="Enable expense alert notifications"
    )
    email_notifications_enabled: bool = Field(
        True, description="Enable email notifications"
    )
    in_app_notifications_enabled: bool = Field(
        True, description="Enable in-app notifications"
    )
