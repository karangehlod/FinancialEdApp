"""Base service class providing common functionality for all services."""

from typing import Optional, List, Any
from abc import ABC, abstractmethod
import logging
from datetime import datetime, timezone

from app.core.exceptions import AppException, DatabaseError

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """
    Abstract base service class providing:
    - Common logging functionality
    - Exception handling patterns
    - Audit trail support
    - Service initialization validation
    
    All domain services should inherit from this class to ensure
    consistency in error handling, logging, and cross-cutting concerns.
    """
    
    def __init__(self):
        """Initialize base service with logger."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self._service_name = self.__class__.__name__
        self.logger.debug(f"{self._service_name} initialized")
    
    def log_operation(
        self,
        operation: str,
        details: Optional[dict] = None,
        level: str = "info"
    ) -> None:
        """
        Log an operation with standardized format.
        
        Args:
            operation: Name of the operation (e.g., "create_user")
            details: Additional context details
            level: Logging level (debug, info, warning, error)
        """
        context = {
            "service": self._service_name,
            "operation": operation,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        if details:
            context.update(details)
        
        log_func = getattr(self.logger, level, self.logger.info)
        log_func(f"{operation}", extra=context)
    
    def log_error(
        self,
        operation: str,
        error: Exception,
        details: Optional[dict] = None
    ) -> None:
        """
        Log an error with full context.
        
        Args:
            operation: Name of the operation that failed
            error: The exception that occurred
            details: Additional context details
        """
        context = {
            "service": self._service_name,
            "operation": operation,
            "error": str(error),
            "error_type": type(error).__name__,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        if details:
            context.update(details)
        
        self.logger.error(f"{operation} failed", extra=context, exc_info=True)
    
    def handle_error(
        self,
        operation: str,
        error: Exception,
        details: Optional[dict] = None,
        reraise_as: Optional[type] = None
    ) -> None:
        """
        Handle errors with logging and optional re-raising as different exception.
        
        Args:
            operation: Name of the operation that failed
            error: The exception that occurred
            details: Additional context details
            reraise_as: Exception type to raise instead (defaults to DatabaseError)
        
        Raises:
            The specified exception type (defaults to DatabaseError)
        """
        self.log_error(operation, error, details)
        
        if reraise_as is None:
            reraise_as = DatabaseError
        
        if isinstance(error, AppException):
            raise error
        
        raise reraise_as(f"Operation '{operation}' failed: {str(error)}")
    
    async def validate_dependencies(self) -> bool:
        """
        Validate that all service dependencies are available.
        Subclasses may override to add dependency checks.
        Returns True if all dependencies are valid.
        """
        return True


class CRUDService(BaseService):
    """
    Base service for CRUD operations.
    
    Provides common patterns for Create, Read, Update, Delete operations
    with logging, error handling, and validation.
    """
    
    @abstractmethod
    async def create(self, data: Any) -> Any:
        """Create a new resource."""
        pass
    
    @abstractmethod
    async def read(self, resource_id: Any) -> Optional[Any]:
        """Read a resource by ID."""
        pass
    
    @abstractmethod
    async def update(self, resource_id: Any, data: Any) -> Optional[Any]:
        """Update a resource."""
        pass
    
    @abstractmethod
    async def delete(self, resource_id: Any) -> bool:
        """Delete a resource."""
        pass
    
    @abstractmethod
    async def list(
        self,
        skip: int = 0,
        limit: int = 10,
        filters: Optional[dict] = None
    ) -> List[Any]:
        """List resources with pagination and filtering."""
        pass


class ServiceFactory:
    """
    Factory for creating service instances with proper dependency injection.

    Uses a per-instance registry (not a class-level mutable dict) so that
    each factory scope is isolated and thread-safe by construction.
    """

    def __init__(self) -> None:
        self._services: dict[str, type] = {}

    def register_service(self, name: str, service_class: type) -> None:
        """Register a service class in the factory."""
        self._services[name] = service_class

    def get_service(self, name: str, *args, **kwargs) -> BaseService:
        """Get a service instance by name."""
        if name not in self._services:
            raise ValueError(f"Service '{name}' not registered")
        return self._services[name](*args, **kwargs)

    def create_service_instance(self, service_class: type, **kwargs) -> BaseService:
        """Create a service instance with automatic dependency resolution."""
        return service_class(**kwargs)
