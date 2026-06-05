"""Tests for notification_service.py - 100% branch coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID
from datetime import datetime, timedelta

from app.services.notification_service import NotificationService
from app.db.models.data import Notification
from app.core.exceptions import ResourceNotFoundError


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock(return_value=None)
    db.refresh = AsyncMock(return_value=None)
    db.execute = AsyncMock()
    db.delete = AsyncMock(return_value=None)  # Changed: delete is async
    db.add_all = MagicMock()
    return db


@pytest.fixture
def service(mock_db):
    return NotificationService(mock_db)


@pytest.fixture
def sample_notification():
    return Notification(
        id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        user_id=UUID("550e8400-e29b-41d4-a716-446655440001"),
        notification_type="budget_alert",
        title="Budget Alert",
        message="You've exceeded your budget",
        related_resource_id=None,
        related_resource_type=None,
        is_read=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


class TestInitialization:
    def test_init_stores_db(self, mock_db):
        service = NotificationService(mock_db)
        assert service.db_session is mock_db


class TestCreateNotification:
    @pytest.mark.asyncio
    async def test_create_notification_success(self, service, mock_db):
        with patch('app.services.notification_service.uuid.uuid4', return_value=UUID("550e8400-e29b-41d4-a716-446655440000")):
            with patch('app.services.notification_service.datetime') as mock_dt:
                mock_dt.utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0)
                
                result = await service.create_notification(
                    user_id="550e8400-e29b-41d4-a716-446655440001",
                    notification_type="budget_alert",
                    title="Title",
                    message="Message"
                )
                
                mock_db.add.assert_called_once()
                mock_db.commit.assert_called_once()
                mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_notification_with_related_resource(self, service, mock_db):
        with patch('app.services.notification_service.uuid.uuid4', return_value=UUID("550e8400-e29b-41d4-a716-446655440000")):
            with patch('app.services.notification_service.datetime') as mock_dt:
                mock_dt.utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0)
                
                result = await service.create_notification(
                    user_id="550e8400-e29b-41d4-a716-446655440001",
                    notification_type="budget_alert",
                    title="Title",
                    message="Message",
                    related_resource_id="550e8400-e29b-41d4-a716-446655440002",
                    related_resource_type="budget"
                )
                
                notif = mock_db.add.call_args[0][0]
                assert notif.related_resource_id == UUID("550e8400-e29b-41d4-a716-446655440002")
                assert notif.related_resource_type == "budget"

    @pytest.mark.asyncio
    async def test_create_notification_without_related_resource(self, service, mock_db):
        with patch('app.services.notification_service.uuid.uuid4', return_value=UUID("550e8400-e29b-41d4-a716-446655440000")):
            with patch('app.services.notification_service.datetime') as mock_dt:
                mock_dt.utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0)
                
                result = await service.create_notification(
                    user_id="550e8400-e29b-41d4-a716-446655440001",
                    notification_type="budget_alert",
                    title="Title",
                    message="Message"
                )
                
                notif = mock_db.add.call_args[0][0]
                assert notif.related_resource_id is None


class TestGetNotification:
    @pytest.mark.asyncio
    async def test_get_notification_found(self, service, mock_db, sample_notification):
        # Create proper mock chain
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.first.return_value = sample_notification
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_result.scalar.return_value = 1  # Fix: return actual count
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await service.get_notification(
            "550e8400-e29b-41d4-a716-446655440000",
            "550e8400-e29b-41d4-a716-446655440001"
        )
        
        assert result == sample_notification

    @pytest.mark.asyncio
    async def test_get_notification_not_found_raises_error(self, service, mock_db):
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.first.return_value = None
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_result.scalar.return_value = 1  # Fix: return actual count
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        with pytest.raises(ResourceNotFoundError):
            await service.get_notification(
                "550e8400-e29b-41d4-a716-446655440000",
                "550e8400-e29b-41d4-a716-446655440001"
            )


class TestGetNotifications:
    @pytest.mark.asyncio
    async def test_get_notifications_no_filters(self, service, mock_db, sample_notification):
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.all.return_value = [sample_notification]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_result.scalar.return_value = 1  # Fix: return actual count
        mock_result.scalar.return_value = 1  # Fix: return actual count
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        notifs, total = await service.get_notifications(
            user_id="550e8400-e29b-41d4-a716-446655440001"
        )
        
        assert total == 1
        mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_get_notifications_with_type_filter(self, service, mock_db, sample_notification):
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.all.return_value = [sample_notification]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_result.scalar.return_value = 1  # Fix: return actual count
        mock_result.scalar.return_value = 1  # Fix: return actual count
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        notifs, total = await service.get_notifications(
            user_id="550e8400-e29b-41d4-a716-446655440001",
            notification_type="budget_alert"
        )
        
        assert total == 1

    @pytest.mark.asyncio
    async def test_get_notifications_with_is_read_filter_true(self, service, mock_db, sample_notification):
        sample_notification.is_read = True
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.all.return_value = [sample_notification]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_result.scalar.return_value = 1  # Fix: return actual count
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        notifs, total = await service.get_notifications(
            user_id="550e8400-e29b-41d4-a716-446655440001",
            is_read=True
        )
        
        assert total == 1

    @pytest.mark.asyncio
    async def test_get_notifications_with_is_read_filter_false(self, service, mock_db, sample_notification):
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.all.return_value = [sample_notification]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_result.scalar.return_value = 1  # Fix: return actual count
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        notifs, total = await service.get_notifications(
            user_id="550e8400-e29b-41d4-a716-446655440001",
            is_read=False
        )
        
        assert total == 1

    @pytest.mark.asyncio
    async def test_get_notifications_with_pagination(self, service, mock_db, sample_notification):
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.all.return_value = [sample_notification]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_result.scalar.return_value = 1  # Fix: return actual count
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        notifs, total = await service.get_notifications(
            user_id="550e8400-e29b-41d4-a716-446655440001",
            skip=10,
            limit=5
        )
        
        assert total == 1


class TestMarkAsRead:
    @pytest.mark.asyncio
    async def test_mark_as_read(self, service, mock_db, sample_notification):
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.first.return_value = sample_notification
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_result.scalar.return_value = 1  # Fix: return actual count
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        with patch('app.services.notification_service.datetime') as mock_dt:
            mock_dt.utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0)
            
            result = await service.mark_as_read(
                "550e8400-e29b-41d4-a716-446655440000",
                "550e8400-e29b-41d4-a716-446655440001"
            )
            
            assert sample_notification.is_read is True
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()


class TestMarkAllAsRead:
    @pytest.mark.asyncio
    async def test_mark_all_as_read(self, service, mock_db, sample_notification):
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.all.return_value = [sample_notification]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_result.scalar.return_value = 1  # Fix: return actual count
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        with patch('app.services.notification_service.datetime') as mock_dt:
            mock_dt.utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0)
            
            count = await service.mark_all_as_read(
                user_id="550e8400-e29b-41d4-a716-446655440001"
            )
            
            assert count == 1
            assert sample_notification.is_read is True
            mock_db.add_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_all_as_read_none(self, service, mock_db):
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.all.return_value = []
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_result.scalar.return_value = 1  # Fix: return actual count
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        count = await service.mark_all_as_read(
            user_id="550e8400-e29b-41d4-a716-446655440001"
        )
        
        assert count == 0


class TestDeleteNotification:
    @pytest.mark.asyncio
    async def test_delete_notification(self, service, mock_db, sample_notification):
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.first.return_value = sample_notification
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_result.scalar.return_value = 1  # Fix: return actual count
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await service.delete_notification(
            "550e8400-e29b-41d4-a716-446655440000",
            "550e8400-e29b-41d4-a716-446655440001"
        )
        
        assert result is True
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()


class TestDeleteOldNotifications:
    @pytest.mark.asyncio
    async def test_delete_old_notifications(self, service, mock_db, sample_notification):
        sample_notification.created_at = datetime.utcnow() - timedelta(days=40)
        
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.all.return_value = [sample_notification]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_result.scalar.return_value = 1  # Fix: return actual count
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        count = await service.delete_old_notifications(
            user_id="550e8400-e29b-41d4-a716-446655440001",
            days=30
        )
        
        assert count == 1
        mock_db.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_old_notifications_default_days(self, service, mock_db, sample_notification):
        sample_notification.created_at = datetime.utcnow() - timedelta(days=40)
        
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.all.return_value = [sample_notification]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_result.scalar.return_value = 1  # Fix: return actual count
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        count = await service.delete_old_notifications(
            user_id="550e8400-e29b-41d4-a716-446655440001"
        )
        
        assert count == 1


class TestGetUnreadCount:
    @pytest.mark.asyncio
    async def test_get_unread_count(self, service, mock_db, sample_notification):
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.all.return_value = [sample_notification]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_result.scalar.return_value = 1  # Fix: return actual count
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        count = await service.get_unread_count(
            user_id="550e8400-e29b-41d4-a716-446655440001"
        )
        
        assert count == 1

    @pytest.mark.asyncio
    async def test_get_unread_count_zero(self, service, mock_db):
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.all.return_value = []
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_result.scalar.return_value = 1  # Fix: return actual count
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        count = await service.get_unread_count(
            user_id="550e8400-e29b-41d4-a716-446655440001"
        )
        
        assert count == 0


class TestGetNotificationSummary:
    @pytest.mark.asyncio
    async def test_get_notification_summary(self, service, mock_db, sample_notification):
        notif2 = Notification(
            id=UUID("550e8400-e29b-41d4-a716-446655440002"),
            user_id=UUID("550e8400-e29b-41d4-a716-446655440001"),
            notification_type="loan_reminder",
            title="Loan Reminder",
            message="Your loan is due",
            related_resource_id=None,
            related_resource_type=None,
            is_read=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.all.return_value = [sample_notification, notif2]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_result.scalar.return_value = 1  # Fix: return actual count
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        summary = await service.get_notification_summary(
            user_id="550e8400-e29b-41d4-a716-446655440001"
        )
        
        assert summary["total"] == 2
        assert summary["unread"] == 1
        assert "budget_alert" in summary["by_type"]
        assert "loan_reminder" in summary["by_type"]

    @pytest.mark.asyncio
    async def test_get_notification_summary_empty(self, service, mock_db):
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.all.return_value = []
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_result.scalar.return_value = 1  # Fix: return actual count
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        summary = await service.get_notification_summary(
            user_id="550e8400-e29b-41d4-a716-446655440001"
        )
        
        assert summary["total"] == 0
        assert summary["unread"] == 0
        assert summary["by_type"] == {}

    @pytest.mark.asyncio
    async def test_get_notification_summary_aggregation(self, service, mock_db):
        notif1 = Notification(
            id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            user_id=UUID("550e8400-e29b-41d4-a716-446655440001"),
            notification_type="budget_alert",
            title="Budget Alert 1",
            message="Message 1",
            related_resource_id=None,
            related_resource_type=None,
            is_read=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        notif2 = Notification(
            id=UUID("550e8400-e29b-41d4-a716-446655440001"),
            user_id=UUID("550e8400-e29b-41d4-a716-446655440001"),
            notification_type="budget_alert",
            title="Budget Alert 2",
            message="Message 2",
            related_resource_id=None,
            related_resource_type=None,
            is_read=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        mock_scalar_obj = MagicMock()
        mock_scalar_obj.all.return_value = [notif1, notif2]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar_obj
        mock_result.scalar.return_value = 1  # Fix: return actual count
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        summary = await service.get_notification_summary(
            user_id="550e8400-e29b-41d4-a716-446655440001"
        )
        
        assert summary["total"] == 2
        assert summary["unread"] == 1
        assert summary["by_type"]["budget_alert"] == 2
