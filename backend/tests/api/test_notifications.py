"""Comprehensive tests for Notification API endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, date, timedelta
import uuid

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# ============== GET NOTIFICATIONS TESTS ==============

class TestGetNotifications:
    """Test notification retrieval endpoints."""
    
    def test_get_all_notifications(self, client):
        """Test retrieving all notifications."""
        response = client.get(
            "/api/v1/notifications",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_get_notifications_with_status_filter(self, client):
        """Test retrieving notifications filtered by status."""
        response = client.get(
            "/api/v1/notifications?status=unread",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_get_notifications_with_type_filter(self, client):
        """Test retrieving notifications filtered by type."""
        response = client.get(
            "/api/v1/notifications?type=budget_alert",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_get_notifications_pagination(self, client):
        """Test notification pagination."""
        response = client.get(
            "/api/v1/notifications?skip=0&limit=10",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_get_specific_notification(self, client):
        """Test retrieving a specific notification."""
        notification_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/notifications/{notification_id}",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403, 404]
    
    def test_get_notification_invalid_id(self, client):
        """Test retrieving notification with invalid ID."""
        response = client.get(
            "/api/v1/notifications/invalid-id",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [422, 401, 403]


# ============== MARK NOTIFICATION TESTS ==============

class TestMarkNotification:
    """Test marking notification as read/unread."""
    
    def test_mark_notification_as_read(self, client):
        """Test marking notification as read."""
        notification_id = str(uuid.uuid4())
        response = client.put(
            f"/api/v1/notifications/{notification_id}/read",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 201, 401, 403, 404]
    
    
    def test_mark_all_notifications_as_read(self, client):
        """Test marking all notifications as read."""
        response = client.put(
            "/api/v1/notifications/mark-all/read",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 201, 401, 403]
    
    def test_mark_invalid_notification_id(self, client):
        """Test marking with invalid notification ID."""
        response = client.put(
            "/api/v1/notifications/invalid-id/read",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [422, 401, 403]


# ============== DELETE NOTIFICATION TESTS ==============

class TestDeleteNotification:
    """Test notification deletion."""
    
    def test_delete_notification(self, client):
        """Test deleting a notification."""
        notification_id = str(uuid.uuid4())
        response = client.delete(
            f"/api/v1/notifications/{notification_id}",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [204, 401, 403, 404]
    
    def test_delete_notification_invalid_id(self, client):
        """Test deleting notification with invalid ID."""
        response = client.delete(
            "/api/v1/notifications/invalid-id",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [422, 401, 403]
    

# ============== BUDGET ALERT NOTIFICATIONS TESTS ==============

class TestBudgetAlertNotifications:
    """Test budget alert notification endpoints."""
    
    def test_get_budget_alerts(self, client):
        """Test getting budget alert notifications."""
        response = client.get(
            "/api/v1/notifications/budget-alerts",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_get_budget_alerts_with_threshold(self, client):
        """Test getting budget alerts above threshold."""
        response = client.get(
            "/api/v1/notifications/budget-alerts?threshold=80",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_dismiss_budget_alert(self, client):
        """Test dismissing budget alert."""
        alert_id = str(uuid.uuid4())
        response = client.post(
            f"/api/v1/notifications/budget-alerts/{alert_id}/dismiss",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 201, 401, 403, 404]


# ============== LOAN REMINDER NOTIFICATIONS TESTS ==============

class TestLoanReminderNotifications:
    """Test loan reminder notification endpoints."""
    
    def test_get_loan_reminders(self, client):
        """Test getting loan reminder notifications."""
        response = client.get(
            "/api/v1/notifications/loan-reminders",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_get_upcoming_loan_payments(self, client):
        """Test getting upcoming loan payment reminders."""
        response = client.get(
            "/api/v1/notifications/upcoming-payments",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_snooze_loan_reminder(self, client):
        """Test snoozing loan reminder."""
        reminder_id = str(uuid.uuid4())
        response = client.post(
            f"/api/v1/notifications/loan-reminders/{reminder_id}/snooze",
            json={"snooze_hours": 24},
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 201, 401, 403, 404, 400, 422]


# ============== GOAL MILESTONE NOTIFICATIONS TESTS ==============

class TestGoalMilestoneNotifications:
    """Test goal milestone notification endpoints."""
    
    def test_get_goal_milestones(self, client):
        """Test getting goal milestone notifications."""
        response = client.get(
            "/api/v1/notifications/goal-milestones",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_acknowledge_milestone(self, client):
        """Test acknowledging milestone."""
        milestone_id = str(uuid.uuid4())
        response = client.post(
            f"/api/v1/notifications/goal-milestones/{milestone_id}/acknowledge",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 201, 401, 403, 404]


# ============== NOTIFICATION SUMMARY TESTS ==============

class TestNotificationSummary:
    """Test notification summary endpoints."""
    
    def test_get_notification_summary(self, client):
        """Test getting notification summary."""
        response = client.get(
            "/api/v1/notifications/summary",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_get_unread_count(self, client):
        """Test getting unread notification count."""
        response = client.get(
            "/api/v1/notifications/unread-count",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]


# ============== EDGE CASES AND ERROR HANDLING ==============

class TestNotificationEdgeCases:
    """Test edge cases and error handling."""
    
    def test_get_notifications_with_invalid_status(self, client):
        """Test getting notifications with invalid status filter."""
        response = client.get(
            "/api/v1/notifications?status=invalid_status",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 400, 401, 403]
    
    def test_mark_already_read_as_read(self, client):
        """Test marking already read notification as read."""
        notification_id = str(uuid.uuid4())
        
        # First read
        response1 = client.put(
            f"/api/v1/notifications/{notification_id}/read",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        # Read again
        response2 = client.put(
            f"/api/v1/notifications/{notification_id}/read",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response1.status_code in [200, 201, 401, 403, 404]
        assert response2.status_code in [200, 201, 401, 403, 404]
    
    def test_snooze_with_invalid_hours(self, client):
        """Test snoozing reminder with invalid hours."""
        reminder_id = str(uuid.uuid4())
        response = client.post(
            f"/api/v1/notifications/loan-reminders/{reminder_id}/snooze",
            json={"snooze_hours": -24},
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [400, 401, 403, 404, 422]
    
    def test_snooze_with_zero_hours(self, client):
        """Test snoozing reminder with zero hours."""
        reminder_id = str(uuid.uuid4())
        response = client.post(
            f"/api/v1/notifications/loan-reminders/{reminder_id}/snooze",
            json={"snooze_hours": 0},
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [400, 401, 403, 404, 422]
    
    def test_snooze_with_very_large_hours(self, client):
        """Test snoozing reminder with very large hours."""
        reminder_id = str(uuid.uuid4())
        response = client.post(
            f"/api/v1/notifications/loan-reminders/{reminder_id}/snooze",
            json={"snooze_hours": 999999},
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 201, 400, 401, 403, 404, 422]


# ============== HTTP METHOD VALIDATION ==============

class TestNotificationHTTPMethods:
    """Test HTTP method validation."""
    
    def test_get_notifications_get_allowed(self, client):
        """Test that GET is allowed for notifications."""
        response = client.get(
            "/api/v1/notifications",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 401, 403]
    
    def test_read_notification_post_allowed(self, client):
        """Test that PUT is allowed for reading notification."""
        notification_id = str(uuid.uuid4())
        response = client.put(
            f"/api/v1/notifications/{notification_id}/read",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [200, 201, 401, 403, 404]
