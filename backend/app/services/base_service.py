"""Base service class providing common functionality for all services."""

from typing import Generic, TypeVar, Optional, List, Any
from abc import ABC, abstractmethod
import logging
from datetime import datetime, timezone

from app.core.exceptions import AppException, DatabaseError

# T is kept for CRUDService[T] — a typed CRUD base. BaseService itself
# is a plain behaviour mixin and does not use T directly.
T = TypeVar('T')
logger = logging.getLogger(__name__)


class BaseService(ABC):
    """
    Abstract base service (behaviour mixin) providing:
    - Structured logging via log_operation / log_error
    - Standardised exception handling via handle_error
    - Audit trail support
    - Service initialisation validation

    All domain services should inherit from this class to ensure
    consistency in error handling, logging, and cross-cutting concerns.

    Note: Generic[T] was intentionally removed — BaseService is a behaviour
    mixin, not a generic container. Use CRUDService[T] when a typed primary
    model type is needed.
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
    
    @abstractmethod
    async def validate_dependencies(self) -> bool:
        """
        Validate that all service dependencies are available.
        
        Raises:
            AppException: If any dependency is unavailable
        
        Returns:
            True if all dependencies are valid
        """
        pass


class CRUDService(BaseService, Generic[T]):
    """
    Typed base service for CRUD operations.

    Provides common patterns for Create, Read, Update, Delete operations
    with logging, error handling, and validation. Specify T as the primary
    SQLAlchemy model type (e.g. ``CRUDService[Expense]``).
    """
    
    @abstractmethod
    async def create(self, data: Any) -> T:
        """Create a new resource."""
        pass
    
    @abstractmethod
    async def read(self, resource_id: Any) -> Optional[T]:
        """Read a resource by ID."""
        pass
    
    @abstractmethod
    async def update(self, resource_id: Any, data: Any) -> Optional[T]:
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
    ) -> List[T]:
        """List resources with pagination and filtering."""
        pass


class ServiceFactory:
    """
    Factory for creating service instances with proper dependency injection.
    
    Ensures all services are initialized with their required dependencies
    and provides a consistent way to instantiate services throughout the application.
    """
    
    _services: dict = {}
    
    @classmethod
    def register_service(cls, name: str, service_class: type) -> None:
        """Register a service class in the factory."""
        cls._services[name] = service_class
    
    @classmethod
    def get_service(cls, name: str, *args, **kwargs) -> BaseService:
        """Get a service instance by name."""
        if name not in cls._services:
            raise ValueError(f"Service '{name}' not registered")
        
        service_class = cls._services[name]
        return service_class(*args, **kwargs)
    
    @classmethod
    def create_service_instance(cls, service_class: type, **kwargs) -> BaseService:
        """Create a service instance with automatic dependency resolution."""
        instance = service_class(**kwargs)
        return instance
