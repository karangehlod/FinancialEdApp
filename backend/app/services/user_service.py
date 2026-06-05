"""Improved user service with dependency injection and base service inheritance."""

from typing import Optional, List
from uuid import UUID
import logging

from app.repositories.interfaces import IUserProfileRepository
from app.schemas.user_profile import UserProfileCreate, UserProfileUpdate
from app.db.models.data import UserProfile
from app.core.exceptions import UserNotFoundError, DatabaseError
from app.services.base_service import CRUDService

logger = logging.getLogger(__name__)


class UserService(CRUDService[UserProfile]):
    """
    User service with full dependency injection.
    
    Responsibilities:
    - User profile CRUD operations
    - User profile validation
    - Delegation to repository layer
    
    Inherits from CRUDService for:
    - Standardized logging
    - Error handling
    - Common CRUD patterns
    """
    
    def __init__(self, user_profile_repository: IUserProfileRepository):
        """
        Initialize user service.
        
        Args:
            user_profile_repository: Repository for user profile data access
        """
        super().__init__()
        self.user_profile_repository = user_profile_repository
        self.log_operation("user_service_initialized")
    
    async def validate_dependencies(self) -> bool:
        """Validate that repository is available."""
        if not self.user_profile_repository:
            raise DatabaseError("User profile repository is not available")
        return True
    
    async def create(self, data: UserProfileCreate) -> UserProfile:
        """Create a new user profile."""
        operation = "create_user_profile"
        try:
            self.log_operation(
                operation,
                {"user_id": str(data.user_id) if hasattr(data, 'user_id') else 'unknown'}
            )
            profile = await self.user_profile_repository.create_profile(
                data.user_id if hasattr(data, 'user_id') else None,
                data
            )
            self.log_operation(f"{operation}_success", {"profile_id": str(profile.id)})
            return profile
        except Exception as e:
            self.handle_error(operation, e, {"input": str(data)})
    
    async def read(self, resource_id) -> Optional[UserProfile]:
        """Get a user profile by ID."""
        operation = "get_user_profile"
        try:
            self.log_operation(operation, {"user_id": str(resource_id)})
            profile = await self.user_profile_repository.get_profile_by_user_id(resource_id)
            return profile
        except Exception as e:
            self.handle_error(operation, e, {"user_id": str(resource_id)})
    
    async def update(self, resource_id, data: UserProfileUpdate) -> Optional[UserProfile]:
        """Update a user profile."""
        operation = "update_user_profile"
        try:
            self.log_operation(operation, {"user_id": str(resource_id)})
            profile = await self.user_profile_repository.update_profile(resource_id, data)
            if not profile:
                raise UserNotFoundError("User profile not found")
            self.log_operation(f"{operation}_success", {"user_id": str(resource_id)})
            return profile
        except UserNotFoundError:
            raise
        except Exception as e:
            self.handle_error(operation, e, {"user_id": str(resource_id)})
    
    async def delete(self, resource_id) -> bool:
        """Delete a user profile."""
        operation = "delete_user_profile"
        try:
            self.log_operation(operation, {"user_id": str(resource_id)})
            success = await self.user_profile_repository.delete_profile(resource_id)
            if success:
                self.log_operation(f"{operation}_success", {"user_id": str(resource_id)})
            return success
        except Exception as e:
            self.handle_error(operation, e, {"user_id": str(resource_id)})
    
    async def list(
        self,
        skip: int = 0,
        limit: int = 10,
        filters: Optional[dict] = None
    ) -> List[UserProfile]:
        """List user profiles with pagination."""
        operation = "list_user_profiles"
        try:
            self.log_operation(operation, {"skip": skip, "limit": limit})
            # This would require repository implementation
            # For now, return empty list
            return []
        except Exception as e:
            self.handle_error(operation, e, {"skip": skip, "limit": limit})