"""Unit tests for app.services.base_service module."""

import pytest
from datetime import datetime
from typing import Optional
from unittest.mock import MagicMock, patch
from app.services.base_service import (
    BaseService,
    CRUDService,
    ServiceFactory,
)
from app.core.exceptions import AppException, DatabaseError


class ConcreteBaseService(BaseService):
    """Concrete implementation for testing."""
    
    async def validate_dependencies(self) -> bool:
        return True


class ConcreteCRUDService(CRUDService):
    """Concrete CRUD service for testing."""
    
    async def create(self, data):
        return data
    
    async def read(self, resource_id):
        return {"id": resource_id}
    
    async def update(self, resource_id, data):
        return {"id": resource_id, **data}
    
    async def delete(self, resource_id):
        return True
    
    async def list(self, skip=0, limit=10, filters=None):
        return []
    
    async def validate_dependencies(self) -> bool:
        return True


class TestBaseServiceInitialization:
    """Test BaseService initialization."""
    
    def test_base_service_init(self):
        service = ConcreteBaseService()
        assert service is not None
        assert service._service_name == "ConcreteBaseService"
        assert service.logger is not None

    def test_base_service_logger_name(self):
        service = ConcreteBaseService()
        assert service.logger.name == "ConcreteBaseService"


class TestBaseServiceLogging:
    """Test BaseService logging functionality."""
    
    def test_log_operation_info_level(self):
        service = ConcreteBaseService()
        with patch.object(service.logger, "info") as mock_log:
            service.log_operation("test_operation", level="info")
            mock_log.assert_called_once()

    def test_log_operation_debug_level(self):
        service = ConcreteBaseService()
        with patch.object(service.logger, "debug") as mock_log:
            service.log_operation("debug_operation", level="debug")
            mock_log.assert_called_once()

    def test_log_operation_warning_level(self):
        service = ConcreteBaseService()
        with patch.object(service.logger, "warning") as mock_log:
            service.log_operation("warning_operation", level="warning")
            mock_log.assert_called_once()

    def test_log_operation_error_level(self):
        service = ConcreteBaseService()
        with patch.object(service.logger, "error") as mock_log:
            service.log_operation("error_operation", level="error")
            mock_log.assert_called_once()

    def test_log_operation_with_details(self):
        service = ConcreteBaseService()
        details = {"user_id": "123", "action": "create"}
        with patch.object(service.logger, "info") as mock_log:
            service.log_operation("operation", details=details, level="info")
            assert mock_log.called

    def test_log_operation_without_details(self):
        service = ConcreteBaseService()
        with patch.object(service.logger, "info") as mock_log:
            service.log_operation("operation", level="info")
            assert mock_log.called

    def test_log_operation_uses_correct_operation_name(self):
        service = ConcreteBaseService()
        with patch.object(service.logger, "info") as mock_log:
            service.log_operation("my_operation", level="info")
            # Verify operation name is in the call
            call_args = mock_log.call_args
            assert "my_operation" in call_args[0][0]

    def test_log_error_logs_exception_info(self):
        service = ConcreteBaseService()
        error = ValueError("Test error")
        with patch.object(service.logger, "error") as mock_log:
            service.log_error("failed_operation", error)
            assert mock_log.called

    def test_log_error_with_details(self):
        service = ConcreteBaseService()
        error = Exception("Test error")
        details = {"resource_id": "456"}
        with patch.object(service.logger, "error") as mock_log:
            service.log_error("operation", error, details)
            assert mock_log.called

    def test_log_error_without_details(self):
        service = ConcreteBaseService()
        error = Exception("Error message")
        with patch.object(service.logger, "error") as mock_log:
            service.log_error("operation", error)
            assert mock_log.called


class TestBaseServiceErrorHandling:
    """Test BaseService error handling."""
    
    def test_handle_error_with_app_exception_reraises(self):
        service = ConcreteBaseService()
        error = AppException("App error", status_code=400)
        
        with pytest.raises(AppException):
            service.handle_error("operation", error)

    def test_handle_error_with_generic_exception_raises_database_error(self):
        service = ConcreteBaseService()
        error = ValueError("Generic error")
        
        with pytest.raises(DatabaseError):
            service.handle_error("operation", error)

    def test_handle_error_with_custom_reraise_exception(self):
        service = ConcreteBaseService()
        error = ValueError("Generic error")
        
        with pytest.raises(AppException):
            service.handle_error(
                "operation",
                error,
                reraise_as=AppException
            )

    def test_handle_error_preserves_operation_name(self):
        service = ConcreteBaseService()
        error = RuntimeError("Runtime error")
        
        with pytest.raises(DatabaseError) as exc_info:
            service.handle_error("my_operation", error)
        
        assert "my_operation" in str(exc_info.value)

    def test_handle_error_with_details(self):
        service = ConcreteBaseService()
        error = Exception("Error")
        details = {"key": "value"}
        
        with patch.object(service, "log_error") as mock_log:
            try:
                service.handle_error("operation", error, details)
            except DatabaseError:
                pass
            
            mock_log.assert_called_once_with("operation", error, details)

    def test_handle_error_without_details(self):
        service = ConcreteBaseService()
        error = Exception("Error")
        
        with patch.object(service, "log_error") as mock_log:
            try:
                service.handle_error("operation", error)
            except DatabaseError:
                pass
            
            mock_log.assert_called_once_with("operation", error, None)


class TestBaseServiceAbstractMethods:
    """Test BaseService abstract methods."""
    
    @pytest.mark.asyncio
    async def test_validate_dependencies_must_be_implemented(self):
        # BaseService is abstract and can't be instantiated directly
        # ConcreteBaseService implements it
        service = ConcreteBaseService()
        result = await service.validate_dependencies()
        assert result is True


class TestCRUDService:
    """Test CRUDService functionality."""
    
    def test_crud_service_inherits_from_base_service(self):
        service = ConcreteCRUDService()
        assert isinstance(service, BaseService)

    @pytest.mark.asyncio
    async def test_crud_create(self):
        service = ConcreteCRUDService()
        data = {"name": "test"}
        result = await service.create(data)
        assert result == data

    @pytest.mark.asyncio
    async def test_crud_read(self):
        service = ConcreteCRUDService()
        resource_id = "123"
        result = await service.read(resource_id)
        assert result["id"] == resource_id

    @pytest.mark.asyncio
    async def test_crud_update(self):
        service = ConcreteCRUDService()
        resource_id = "123"
        data = {"name": "updated"}
        result = await service.update(resource_id, data)
        assert result["id"] == resource_id
        assert result["name"] == "updated"

    @pytest.mark.asyncio
    async def test_crud_delete(self):
        service = ConcreteCRUDService()
        result = await service.delete("123")
        assert result is True

    @pytest.mark.asyncio
    async def test_crud_list(self):
        service = ConcreteCRUDService()
        result = await service.list(skip=0, limit=10)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_crud_list_with_filters(self):
        service = ConcreteCRUDService()
        filters = {"status": "active"}
        result = await service.list(filters=filters)
        assert isinstance(result, list)


class TestServiceFactory:
    """Test ServiceFactory."""
    
    def test_factory_register_service(self):
        # Clear previous registrations
        ServiceFactory._services = {}
        
        ServiceFactory.register_service("test_service", ConcreteCRUDService)
        assert "test_service" in ServiceFactory._services

    def test_factory_get_service(self):
        ServiceFactory._services = {}
        ServiceFactory.register_service("test_service", ConcreteCRUDService)
        
        service = ServiceFactory.get_service("test_service")
        assert isinstance(service, ConcreteCRUDService)

    def test_factory_get_unregistered_service_raises_error(self):
        ServiceFactory._services = {}
        
        with pytest.raises(ValueError, match="not registered"):
            ServiceFactory.get_service("non_existent_service")

    def test_factory_create_service_instance(self):
        service = ServiceFactory.create_service_instance(ConcreteCRUDService)
        assert isinstance(service, ConcreteCRUDService)

    def test_factory_multiple_registrations(self):
        ServiceFactory._services = {}
        
        ServiceFactory.register_service("service1", ConcreteBaseService)
        ServiceFactory.register_service("service2", ConcreteCRUDService)
        
        service1 = ServiceFactory.get_service("service1")
        service2 = ServiceFactory.get_service("service2")
        
        assert isinstance(service1, ConcreteBaseService)
        assert isinstance(service2, ConcreteCRUDService)

    def test_factory_overwrite_existing_registration(self):
        ServiceFactory._services = {}
        
        ServiceFactory.register_service("service", ConcreteBaseService)
        assert ServiceFactory.get_service("service").__class__.__name__ == "ConcreteBaseService"
        
        ServiceFactory.register_service("service", ConcreteCRUDService)
        assert ServiceFactory.get_service("service").__class__.__name__ == "ConcreteCRUDService"
