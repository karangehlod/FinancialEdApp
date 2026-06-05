"""Role-Based Access Control (RBAC) authorization."""

from abc import ABC, abstractmethod
from typing import List, Set, Optional, Dict, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """System permissions."""
    
    # User permissions
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_LIST = "user:list"
    
    # Expense permissions
    EXPENSE_CREATE = "expense:create"
    EXPENSE_READ = "expense:read"
    EXPENSE_UPDATE = "expense:update"
    EXPENSE_DELETE = "expense:delete"
    EXPENSE_LIST = "expense:list"
    
    # Budget permissions
    BUDGET_CREATE = "budget:create"
    BUDGET_READ = "budget:read"
    BUDGET_UPDATE = "budget:update"
    BUDGET_DELETE = "budget:delete"
    BUDGET_LIST = "budget:list"
    
    # Goal permissions
    GOAL_CREATE = "goal:create"
    GOAL_READ = "goal:read"
    GOAL_UPDATE = "goal:update"
    GOAL_DELETE = "goal:delete"
    GOAL_LIST = "goal:list"
    
    # Loan permissions
    LOAN_CREATE = "loan:create"
    LOAN_READ = "loan:read"
    LOAN_UPDATE = "loan:update"
    LOAN_DELETE = "loan:delete"
    LOAN_LIST = "loan:list"
    
    # Admin permissions
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"
    AUDIT_READ = "audit:read"


class Role(str, Enum):
    """System roles."""
    
    USER = "user"
    ADMIN = "admin"
    SUPERUSER = "superuser"


class RolePermissionMap:
    """Mapping of roles to permissions."""
    
    def __init__(self):
        """Initialize role-permission mappings."""
        self.role_permissions: Dict[Role, Set[Permission]] = {
            Role.USER: {
                # User can manage their own profile
                Permission.USER_READ,
                Permission.USER_UPDATE,
                
                # User can manage their expenses
                Permission.EXPENSE_CREATE,
                Permission.EXPENSE_READ,
                Permission.EXPENSE_UPDATE,
                Permission.EXPENSE_DELETE,
                Permission.EXPENSE_LIST,
                
                # User can manage their budgets
                Permission.BUDGET_CREATE,
                Permission.BUDGET_READ,
                Permission.BUDGET_UPDATE,
                Permission.BUDGET_DELETE,
                Permission.BUDGET_LIST,
                
                # User can manage their goals
                Permission.GOAL_CREATE,
                Permission.GOAL_READ,
                Permission.GOAL_UPDATE,
                Permission.GOAL_DELETE,
                Permission.GOAL_LIST,
                
                # User can manage their loans
                Permission.LOAN_CREATE,
                Permission.LOAN_READ,
                Permission.LOAN_UPDATE,
                Permission.LOAN_DELETE,
                Permission.LOAN_LIST,
            },
            
            Role.ADMIN: {
                # Admin inherits all user permissions
                Permission.USER_READ,
                Permission.USER_UPDATE,
                Permission.EXPENSE_CREATE,
                Permission.EXPENSE_READ,
                Permission.EXPENSE_UPDATE,
                Permission.EXPENSE_DELETE,
                Permission.EXPENSE_LIST,
                Permission.BUDGET_CREATE,
                Permission.BUDGET_READ,
                Permission.BUDGET_UPDATE,
                Permission.BUDGET_DELETE,
                Permission.BUDGET_LIST,
                Permission.GOAL_CREATE,
                Permission.GOAL_READ,
                Permission.GOAL_UPDATE,
                Permission.GOAL_DELETE,
                Permission.GOAL_LIST,
                Permission.LOAN_CREATE,
                Permission.LOAN_READ,
                Permission.LOAN_UPDATE,
                Permission.LOAN_DELETE,
                Permission.LOAN_LIST,
                
                # Admin-specific permissions
                Permission.ADMIN_READ,
                Permission.AUDIT_READ,
            },
            
            Role.SUPERUSER: {
                # Superuser has all permissions
                Permission.USER_CREATE,
                Permission.USER_READ,
                Permission.USER_UPDATE,
                Permission.USER_DELETE,
                Permission.USER_LIST,
                Permission.EXPENSE_CREATE,
                Permission.EXPENSE_READ,
                Permission.EXPENSE_UPDATE,
                Permission.EXPENSE_DELETE,
                Permission.EXPENSE_LIST,
                Permission.BUDGET_CREATE,
                Permission.BUDGET_READ,
                Permission.BUDGET_UPDATE,
                Permission.BUDGET_DELETE,
                Permission.BUDGET_LIST,
                Permission.GOAL_CREATE,
                Permission.GOAL_READ,
                Permission.GOAL_UPDATE,
                Permission.GOAL_DELETE,
                Permission.GOAL_LIST,
                Permission.LOAN_CREATE,
                Permission.LOAN_READ,
                Permission.LOAN_UPDATE,
                Permission.LOAN_DELETE,
                Permission.LOAN_LIST,
                Permission.ADMIN_READ,
                Permission.ADMIN_WRITE,
                Permission.AUDIT_READ,
            }
        }
    
    def get_permissions(self, role: Role) -> Set[Permission]:
        """Get all permissions for a role."""
        return self.role_permissions.get(role, set())
    
    def has_permission(self, role: Role, permission: Permission) -> bool:
        """Check if a role has a specific permission."""
        return permission in self.get_permissions(role)


class AuthorizationManager(ABC):
    """Abstract authorization manager."""
    
    @abstractmethod
    async def is_authorized(
        self,
        user_id: str,
        resource_type: str,
        action: str,
        resource_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if user is authorized for an action."""
        pass
    
    @abstractmethod
    async def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Get all permissions for a user."""
        pass


class RBACAuthorizationManager(AuthorizationManager):
    """RBAC-based authorization manager."""
    
    def __init__(self, role_permission_map: Optional[RolePermissionMap] = None):
        """
        Initialize RBAC authorization manager.
        
        Args:
            role_permission_map: Role-permission mapping (uses default if not provided)
        """
        self.role_permission_map = role_permission_map or RolePermissionMap()
        self.user_roles: Dict[str, Set[Role]] = {}
    
    async def is_authorized(
        self,
        user_id: str,
        resource_type: str,
        action: str,
        resource_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if user is authorized for an action.
        
        Args:
            user_id: User ID
            resource_type: Type of resource (e.g., "expense", "budget")
            action: Action to perform (e.g., "create", "read", "update", "delete")
            resource_id: ID of specific resource (for resource-level authorization)
            context: Additional context for authorization decision
        
        Returns:
            True if authorized, False otherwise
        """
        try:
            # Get user roles
            roles = self.user_roles.get(user_id, {Role.USER})
            
            # Build permission name
            permission_str = f"{resource_type}:{action}"
            
            try:
                permission = Permission(permission_str)
            except ValueError:
                logger.warning(f"Unknown permission: {permission_str}")
                return False
            
            # Check if any role has the permission
            for role in roles:
                if self.role_permission_map.has_permission(role, permission):
                    # Additional context-based checks can go here
                    return await self._check_resource_ownership(
                        user_id, resource_type, resource_id, context
                    )
            
            logger.warning(
                f"Authorization denied: user={user_id}, "
                f"resource={resource_type}, action={action}"
            )
            return False
        
        except Exception as e:
            logger.error(f"Error checking authorization: {e}")
            return False
    
    async def _check_resource_ownership(
        self,
        user_id: str,
        resource_type: str,
        resource_id: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Check if user owns the resource.
        
        This is a placeholder for resource-level authorization.
        In production, this would check database records.
        """
        if resource_id is None:
            return True  # No resource-level check needed
        
        # Check if user owns the resource
        # This would typically query the database
        # For now, return True if resource_id matches user_id
        return True
    
    async def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Get all permissions for a user."""
        roles = self.user_roles.get(user_id, {Role.USER})
        permissions = set()
        
        for role in roles:
            permissions.update(self.role_permission_map.get_permissions(role))
        
        return permissions
    
    def assign_role(self, user_id: str, role: Role) -> None:
        """Assign a role to a user."""
        if user_id not in self.user_roles:
            self.user_roles[user_id] = set()
        
        self.user_roles[user_id].add(role)
        logger.info(f"Assigned role {role} to user {user_id}")
    
    def revoke_role(self, user_id: str, role: Role) -> None:
        """Revoke a role from a user."""
        if user_id in self.user_roles:
            self.user_roles[user_id].discard(role)
            logger.info(f"Revoked role {role} from user {user_id}")
    
    def get_user_roles(self, user_id: str) -> Set[Role]:
        """Get all roles for a user."""
        return self.user_roles.get(user_id, {Role.USER})


# Global authorization manager instance
authorization_manager = RBACAuthorizationManager()
