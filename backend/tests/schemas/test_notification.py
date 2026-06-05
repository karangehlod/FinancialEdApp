"""Tests for notification schema validation."""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from pydantic import ValidationError
from app.schemas.notification import (
    NotificationCreate,
    NotificationUpdate,
    NotificationResponse,
    NotificationListResponse,
    NotificationSummary,
    NotificationPreferences,
)


class TestNotificationCreate:
    """Test NotificationCreate schema validation."""
    
    def test_valid_notification_creation(self):
        """Test creating a notification with required fields only."""
        data = {
            "notification_type": "budget_alert",
            "title": "Budget exceeded",
            "message": "You have exceeded your monthly budget",
        }
        notification = NotificationCreate(**data)
        assert notification.notification_type == "budget_alert"
        assert notification.title == "Budget exceeded"
        assert notification.related_resource_id is None
    
    def test_notification_with_related_resource(self):
        """Test creating a notification with related resource info."""
        resource_id = uuid4()
        data = {
            "notification_type": "expense_created",
            "title": "Expense recorded",
            "message": "Your expense has been recorded",
            "related_resource_id": resource_id,
            "related_resource_type": "expense",
        }
        notification = NotificationCreate(**data)
        assert notification.related_resource_id == resource_id
        assert notification.related_resource_type == "expense"
    
    def test_notification_title_too_long(self):
        """Test that notification title exceeding 255 chars is rejected."""
        data = {
            "notification_type": "alert",
            "title": "a" * 256,
            "message": "Test message",
        }
        with pytest.raises(ValidationError):
            NotificationCreate(**data)
    
    def test_notification_title_at_limit(self):
        """Test notification title at exactly 255 chars."""
        data = {
            "notification_type": "alert",
            "title": "a" * 255,
            "message": "Test message",
        }
        notification = NotificationCreate(**data)
        assert len(notification.title) == 255
    
    def test_notification_empty_title(self):
        """Test that empty title may be allowed (no min_length specified)."""
        data = {
            "notification_type": "alert",
            "title": "",
            "message": "Test message",
        }
        notification = NotificationCreate(**data)
        assert notification.title == ""
    
    def test_notification_missing_required_fields(self):
        """Test that missing required fields raises error."""
        data = {
            "notification_type": "alert",
            # Missing title and message
        }
        with pytest.raises(ValidationError):
            NotificationCreate(**data)
    
    def test_various_notification_types(self):
        """Test various notification types."""
        types = [
            "budget_alert",
            "loan_reminder",
            "goal_milestone",
            "expense_alert",
            "system_notification",
        ]
        for notif_type in types:
            data = {
                "notification_type": notif_type,
                "title": f"{notif_type} title",
                "message": "Test message",
            }
            notification = NotificationCreate(**data)
            assert notification.notification_type == notif_type
    
    def test_long_message(self):
        """Test notification with very long message."""
        data = {
            "notification_type": "alert",
            "title": "Long message",
            "message": "a" * 5000,
        }
        notification = NotificationCreate(**data)
        assert len(notification.message) == 5000
    
    def test_special_characters_in_fields(self):
        """Test notification with special characters."""
        data = {
            "notification_type": "alert",
            "title": "Special: @#$% & <html>",
            "message": "Message with 'quotes' and \"double quotes\"",
        }
        notification = NotificationCreate(**data)
        assert "@#$%" in notification.title
        assert "quotes" in notification.message
    
    def test_related_resource_type_at_limit(self):
        """Test related_resource_type at 50 character limit."""
        data = {
            "notification_type": "alert",
            "title": "Test",
            "message": "Test",
            "related_resource_type": "a" * 50,
        }
        notification = NotificationCreate(**data)
        assert len(notification.related_resource_type) == 50
    
    def test_related_resource_type_too_long(self):
        """Test that related_resource_type exceeding 50 chars is rejected."""
        data = {
            "notification_type": "alert",
            "title": "Test",
            "message": "Test",
            "related_resource_type": "a" * 51,
        }
        with pytest.raises(ValidationError):
            NotificationCreate(**data)


class TestNotificationUpdate:
    """Test NotificationUpdate schema validation."""
    
    def test_mark_as_read(self):
        """Test marking notification as read."""
        data = {"is_read": True}
        update = NotificationUpdate(**data)
        assert update.is_read is True
    
    def test_mark_as_unread(self):
        """Test marking notification as unread."""
        data = {"is_read": False}
        update = NotificationUpdate(**data)
        assert update.is_read is False
    
    def test_is_read_required(self):
        """Test that is_read is required."""
        with pytest.raises(ValidationError):
            NotificationUpdate()


class TestNotificationResponse:
    """Test NotificationResponse schema."""
    
    def test_valid_response(self):
        """Test complete notification response."""
        now = datetime.utcnow()
        notification_id = uuid4()
        user_id = uuid4()
        
        data = {
            "notification_type": "budget_alert",
            "title": "Budget exceeded",
            "message": "You exceeded budget",
            "id": notification_id,
            "user_id": user_id,
            "is_read": False,
            "created_at": now,
            "updated_at": now,
        }
        response = NotificationResponse(**data)
        assert response.id == notification_id
        assert response.user_id == user_id
        assert response.is_read is False
    
    def test_response_with_related_resource(self):
        """Test notification response with related resource."""
        now = datetime.utcnow()
        resource_id = uuid4()
        
        data = {
            "notification_type": "expense_created",
            "title": "Expense created",
            "message": "New expense recorded",
            "related_resource_id": resource_id,
            "related_resource_type": "expense",
            "id": uuid4(),
            "user_id": uuid4(),
            "is_read": True,
            "created_at": now,
            "updated_at": now,
        }
        response = NotificationResponse(**data)
        assert response.related_resource_id == resource_id


class TestNotificationListResponse:
    """Test NotificationListResponse schema."""
    
    def test_empty_list(self):
        """Test notification list response with empty list."""
        data = {
            "notifications": [],
            "total": 0,
            "skip": 0,
            "limit": 10,
        }
        response = NotificationListResponse(**data)
        assert len(response.notifications) == 0
        assert response.total == 0
    
    def test_populated_list(self):
        """Test notification list with multiple items."""
        now = datetime.utcnow()
        notifications_data = [
            {
                "notification_type": "alert",
                "title": f"Alert {i}",
                "message": f"Message {i}",
                "id": uuid4(),
                "user_id": uuid4(),
                "is_read": i % 2 == 0,
                "created_at": now,
                "updated_at": now,
            }
            for i in range(5)
        ]
        
        data = {
            "notifications": notifications_data,
            "total": 5,
            "skip": 0,
            "limit": 10,
        }
        response = NotificationListResponse(**data)
        assert len(response.notifications) == 5
        assert response.total == 5
    
    def test_pagination_info(self):
        """Test pagination information."""
        data = {
            "notifications": [],
            "total": 100,
            "skip": 20,
            "limit": 10,
        }
        response = NotificationListResponse(**data)
        assert response.skip == 20
        assert response.limit == 10
        assert response.total == 100


class TestNotificationSummary:
    """Test NotificationSummary schema."""
    
    def test_summary_with_no_notifications(self):
        """Test summary with no notifications."""
        data = {
            "total": 0,
            "unread": 0,
            "by_type": {},
        }
        summary = NotificationSummary(**data)
        assert summary.total == 0
        assert summary.unread == 0
        assert len(summary.by_type) == 0
    
    def test_summary_with_notifications(self):
        """Test summary with multiple notifications."""
        data = {
            "total": 15,
            "unread": 5,
            "by_type": {
                "budget_alert": 7,
                "loan_reminder": 5,
                "goal_milestone": 3,
            },
        }
        summary = NotificationSummary(**data)
        assert summary.total == 15
        assert summary.unread == 5
        assert summary.by_type["budget_alert"] == 7
        assert summary.by_type["loan_reminder"] == 5
    
    def test_summary_all_read(self):
        """Test summary with all notifications read."""
        data = {
            "total": 10,
            "unread": 0,
            "by_type": {"budget_alert": 10},
        }
        summary = NotificationSummary(**data)
        assert summary.unread == 0
        assert summary.total == 10


class TestNotificationPreferences:
    """Test NotificationPreferences schema."""
    
    def test_default_preferences(self):
        """Test notification preferences with defaults."""
        prefs = NotificationPreferences()
        assert prefs.budget_alerts_enabled is True
        assert prefs.loan_reminders_enabled is True
        assert prefs.goal_notifications_enabled is True
        assert prefs.expense_alerts_enabled is True
        assert prefs.email_notifications_enabled is True
        assert prefs.in_app_notifications_enabled is True
    
    def test_all_disabled(self):
        """Test notification preferences all disabled."""
        data = {
            "budget_alerts_enabled": False,
            "loan_reminders_enabled": False,
            "goal_notifications_enabled": False,
            "expense_alerts_enabled": False,
            "email_notifications_enabled": False,
            "in_app_notifications_enabled": False,
        }
        prefs = NotificationPreferences(**data)
        assert all([
            prefs.budget_alerts_enabled is False,
            prefs.loan_reminders_enabled is False,
            prefs.goal_notifications_enabled is False,
            prefs.expense_alerts_enabled is False,
            prefs.email_notifications_enabled is False,
            prefs.in_app_notifications_enabled is False,
        ])
    
    def test_mixed_preferences(self):
        """Test notification preferences with mixed values."""
        data = {
            "budget_alerts_enabled": True,
            "loan_reminders_enabled": False,
            "goal_notifications_enabled": True,
            "expense_alerts_enabled": False,
            "email_notifications_enabled": True,
            "in_app_notifications_enabled": False,
        }
        prefs = NotificationPreferences(**data)
        assert prefs.budget_alerts_enabled is True
        assert prefs.loan_reminders_enabled is False
        assert prefs.goal_notifications_enabled is True
        assert prefs.expense_alerts_enabled is False
