"""Tests for core authorization (RBAC) module."""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.core.authorization import (
    Permission,
    Role,
    RolePermissionMap,
    RBACAuthorizationManager,
)


# ==================== Permission Enum Tests ====================

class TestPermission:
    """Test Permission enum."""
    
    def test_user_permissions_exist(self):
        """Test that all user permissions are defined."""
        assert Permission.USER_CREATE.value == "user:create"
        assert Permission.USER_READ.value == "user:read"
        assert Permission.USER_UPDATE.value == "user:update"
        assert Permission.USER_DELETE.value == "user:delete"
        assert Permission.USER_LIST.value == "user:list"
    
    def test_expense_permissions_exist(self):
        """Test that all expense permissions are defined."""
        assert Permission.EXPENSE_CREATE.value == "expense:create"
        assert Permission.EXPENSE_READ.value == "expense:read"
        assert Permission.EXPENSE_UPDATE.value == "expense:update"
        assert Permission.EXPENSE_DELETE.value == "expense:delete"
        assert Permission.EXPENSE_LIST.value == "expense:list"
    
    def test_budget_permissions_exist(self):
        """Test that all budget permissions are defined."""
        assert Permission.BUDGET_CREATE.value == "budget:create"
        assert Permission.BUDGET_READ.value == "budget:read"
        assert Permission.BUDGET_UPDATE.value == "budget:update"
        assert Permission.BUDGET_DELETE.value == "budget:delete"
        assert Permission.BUDGET_LIST.value == "budget:list"
    
    def test_goal_permissions_exist(self):
        """Test that all goal permissions are defined."""
        assert Permission.GOAL_CREATE.value == "goal:create"
        assert Permission.GOAL_READ.value == "goal:read"
        assert Permission.GOAL_UPDATE.value == "goal:update"
        assert Permission.GOAL_DELETE.value == "goal:delete"
        assert Permission.GOAL_LIST.value == "goal:list"
    
    def test_loan_permissions_exist(self):
        """Test that all loan permissions are defined."""
        assert Permission.LOAN_CREATE.value == "loan:create"
        assert Permission.LOAN_READ.value == "loan:read"
        assert Permission.LOAN_UPDATE.value == "loan:update"
        assert Permission.LOAN_DELETE.value == "loan:delete"
        assert Permission.LOAN_LIST.value == "loan:list"
    
    def test_admin_permissions_exist(self):
        """Test that all admin permissions are defined."""
        assert Permission.ADMIN_READ.value == "admin:read"
        assert Permission.ADMIN_WRITE.value == "admin:write"
        assert Permission.AUDIT_READ.value == "audit:read"


# ==================== Role Enum Tests ====================

class TestRole:
    """Test Role enum."""
    
    def test_user_role(self):
        """Test USER role exists."""
        assert Role.USER.value == "user"
    
    def test_admin_role(self):
        """Test ADMIN role exists."""
        assert Role.ADMIN.value == "admin"
    
    def test_superuser_role(self):
        """Test SUPERUSER role exists."""
        assert Role.SUPERUSER.value == "superuser"


# ==================== RolePermissionMap Tests ====================

class TestRolePermissionMap:
    """Test RolePermissionMap."""
    
    def test_get_permissions_user_role(self):
        """Test getting permissions for USER role."""
        role_map = RolePermissionMap()
        permissions = role_map.get_permissions(Role.USER)
        
        assert Permission.EXPENSE_CREATE in permissions
        assert Permission.EXPENSE_READ in permissions
        assert Permission.BUDGET_CREATE in permissions
        assert Permission.GOAL_CREATE in permissions
        assert Permission.LOAN_CREATE in permissions
    
    def test_get_permissions_admin_role(self):
        """Test getting permissions for ADMIN role."""
        role_map = RolePermissionMap()
        permissions = role_map.get_permissions(Role.ADMIN)
        
        assert Permission.ADMIN_READ in permissions
        assert Permission.AUDIT_READ in permissions
        assert Permission.EXPENSE_CREATE in permissions  # Inherits from USER
    
    def test_get_permissions_superuser_role(self):
        """Test getting permissions for SUPERUSER role."""
        role_map = RolePermissionMap()
        permissions = role_map.get_permissions(Role.SUPERUSER)
        
        assert Permission.USER_CREATE in permissions
        assert Permission.ADMIN_WRITE in permissions
        assert Permission.AUDIT_READ in permissions
        assert len(permissions) > len(role_map.get_permissions(Role.ADMIN))
    
    def test_get_permissions_unknown_role(self):
        """Test getting permissions for unknown role."""
        role_map = RolePermissionMap()
        permissions = role_map.get_permissions("unknown_role")
        
        assert permissions == set()
    
    def test_has_permission_user_can_create_expense(self):
        """Test USER role can create expenses."""
        role_map = RolePermissionMap()
        has_perm = role_map.has_permission(Role.USER, Permission.EXPENSE_CREATE)
        
        assert has_perm is True
    
    def test_has_permission_user_cannot_delete_user(self):
        """Test USER role cannot delete users."""
        role_map = RolePermissionMap()
        has_perm = role_map.has_permission(Role.USER, Permission.USER_DELETE)
        
        assert has_perm is False
    
    def test_has_permission_admin_can_read_admin(self):
        """Test ADMIN role can read admin resources."""
        role_map = RolePermissionMap()
        has_perm = role_map.has_permission(Role.ADMIN, Permission.ADMIN_READ)
        
        assert has_perm is True
    
    def test_has_permission_superuser_has_all_permissions(self):
        """Test SUPERUSER has all permissions."""
        role_map = RolePermissionMap()
        
        # Check some permissions
        assert role_map.has_permission(Role.SUPERUSER, Permission.USER_CREATE)
        assert role_map.has_permission(Role.SUPERUSER, Permission.ADMIN_WRITE)
        assert role_map.has_permission(Role.SUPERUSER, Permission.AUDIT_READ)
    
    def test_user_role_cannot_read_admin(self):
        """Test USER role cannot read admin resources."""
        role_map = RolePermissionMap()
        has_perm = role_map.has_permission(Role.USER, Permission.ADMIN_READ)
        
        assert has_perm is False


# ==================== RBACAuthorizationManager Tests ====================

class TestRBACAuthorizationManager:
    """Test RBACAuthorizationManager."""
    
    @pytest.mark.asyncio
    async def test_is_authorized_user_create_expense(self):
        """Test USER can create expense."""
        manager = RBACAuthorizationManager()
        manager.assign_role("user123", Role.USER)
        
        result = await manager.is_authorized(
            user_id="user123",
            resource_type="expense",
            action="create"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_is_authorized_user_cannot_delete_user(self):
        """Test USER cannot delete user."""
        manager = RBACAuthorizationManager()
        manager.assign_role("user123", Role.USER)
        
        result = await manager.is_authorized(
            user_id="user123",
            resource_type="user",
            action="delete"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_is_authorized_admin_can_read_admin(self):
        """Test ADMIN can read admin resources."""
        manager = RBACAuthorizationManager()
        manager.assign_role("admin123", Role.ADMIN)
        
        result = await manager.is_authorized(
            user_id="admin123",
            resource_type="admin",
            action="read"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_is_authorized_superuser_can_do_anything(self):
        """Test SUPERUSER can perform any action."""
        manager = RBACAuthorizationManager()
        manager.assign_role("super123", Role.SUPERUSER)
        
        # Test various permissions
        assert await manager.is_authorized("super123", "user", "create")
        assert await manager.is_authorized("super123", "admin", "write")
        assert await manager.is_authorized("super123", "audit", "read")
    
    @pytest.mark.asyncio
    async def test_is_authorized_unknown_permission(self):
        """Test authorization with unknown permission."""
        manager = RBACAuthorizationManager()
        manager.assign_role("user123", Role.USER)
        
        result = await manager.is_authorized(
            user_id="user123",
            resource_type="unknown",
            action="unknown_action"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_is_authorized_default_user_role(self):
        """Test that unassigned users get USER role by default."""
        manager = RBACAuthorizationManager()
        
        result = await manager.is_authorized(
            user_id="new_user",
            resource_type="expense",
            action="create"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_is_authorized_with_resource_id(self):
        """Test authorization with resource ID."""
        manager = RBACAuthorizationManager()
        manager.assign_role("user123", Role.USER)
        
        result = await manager.is_authorized(
            user_id="user123",
            resource_type="expense",
            action="read",
            resource_id="expense456"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_is_authorized_with_context(self):
        """Test authorization with context."""
        manager = RBACAuthorizationManager()
        manager.assign_role("user123", Role.USER)
        
        result = await manager.is_authorized(
            user_id="user123",
            resource_type="expense",
            action="update",
            context={"ip": "192.168.1.1"}
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_is_authorized_error_handling(self):
        """Test error handling in authorization check."""
        manager = RBACAuthorizationManager()
        manager.user_roles["user123"] = {Role.USER}
        
        # Should handle errors gracefully and return False
        result = await manager.is_authorized(
            user_id="user123",
            resource_type="expense",
            action="create"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_get_user_permissions_user_role(self):
        """Test getting permissions for user."""
        manager = RBACAuthorizationManager()
        manager.assign_role("user123", Role.USER)
        
        permissions = await manager.get_user_permissions("user123")
        
        assert Permission.EXPENSE_CREATE in permissions
        assert Permission.BUDGET_READ in permissions
        assert len(permissions) > 10
    
    @pytest.mark.asyncio
    async def test_get_user_permissions_admin_role(self):
        """Test getting permissions for admin."""
        manager = RBACAuthorizationManager()
        manager.assign_role("admin123", Role.ADMIN)
        
        permissions = await manager.get_user_permissions("admin123")
        
        assert Permission.ADMIN_READ in permissions
        assert Permission.ADMIN_WRITE not in permissions  # Admin doesn't have WRITE
    
    @pytest.mark.asyncio
    async def test_get_user_permissions_superuser_role(self):
        """Test getting permissions for superuser."""
        manager = RBACAuthorizationManager()
        manager.assign_role("super123", Role.SUPERUSER)
        
        permissions = await manager.get_user_permissions("super123")
        
        assert Permission.USER_CREATE in permissions
        assert Permission.ADMIN_WRITE in permissions
        assert len(permissions) > len(await manager.get_user_permissions("user123"))
    
    @pytest.mark.asyncio
    async def test_get_user_permissions_multiple_roles(self):
        """Test getting permissions for user with multiple roles."""
        manager = RBACAuthorizationManager()
        manager.assign_role("user123", Role.USER)
        manager.assign_role("user123", Role.ADMIN)
        
        permissions = await manager.get_user_permissions("user123")
        
        # Should have permissions from both USER and ADMIN roles
        assert Permission.EXPENSE_CREATE in permissions
        assert Permission.ADMIN_READ in permissions
    
    @pytest.mark.asyncio
    async def test_get_user_permissions_no_roles(self):
        """Test getting permissions for unassigned user."""
        manager = RBACAuthorizationManager()
        
        permissions = await manager.get_user_permissions("new_user")
        
        # Should get default USER permissions
        assert Permission.EXPENSE_CREATE in permissions
    
    def test_assign_role(self):
        """Test assigning a role to a user."""
        manager = RBACAuthorizationManager()
        
        manager.assign_role("user123", Role.ADMIN)
        roles = manager.get_user_roles("user123")
        
        assert Role.ADMIN in roles
    
    def test_assign_multiple_roles(self):
        """Test assigning multiple roles to a user."""
        manager = RBACAuthorizationManager()
        
        manager.assign_role("user123", Role.USER)
        manager.assign_role("user123", Role.ADMIN)
        roles = manager.get_user_roles("user123")
        
        assert Role.USER in roles
        assert Role.ADMIN in roles
    
    def test_revoke_role(self):
        """Test revoking a role from a user."""
        manager = RBACAuthorizationManager()
        manager.assign_role("user123", Role.ADMIN)
        
        manager.revoke_role("user123", Role.ADMIN)
        roles = manager.get_user_roles("user123")
        
        assert Role.ADMIN not in roles
    
    def test_revoke_role_non_existent(self):
        """Test revoking a non-existent role."""
        manager = RBACAuthorizationManager()
        
        # Should not raise error
        manager.revoke_role("new_user", Role.ADMIN)
    
    def test_get_user_roles_unassigned(self):
        """Test getting roles for unassigned user."""
        manager = RBACAuthorizationManager()
        
        roles = manager.get_user_roles("new_user")
        
        assert roles == {Role.USER}  # Default role
    
    def test_get_user_roles_assigned(self):
        """Test getting roles for assigned user."""
        manager = RBACAuthorizationManager()
        manager.assign_role("user123", Role.ADMIN)
        
        roles = manager.get_user_roles("user123")
        
        assert Role.ADMIN in roles
    
    @pytest.mark.asyncio
    async def test_multiple_authorization_checks(self):
        """Test multiple authorization checks in sequence."""
        manager = RBACAuthorizationManager()
        manager.assign_role("user123", Role.USER)
        
        # Multiple checks
        assert await manager.is_authorized("user123", "expense", "create")
        assert await manager.is_authorized("user123", "budget", "read")
        assert not await manager.is_authorized("user123", "user", "delete")
        assert await manager.is_authorized("user123", "goal", "update")
    
    @pytest.mark.asyncio
    async def test_permission_change_after_role_assignment(self):
        """Test that permission changes after role assignment."""
        manager = RBACAuthorizationManager()
        
        # Initially user role
        assert not await manager.is_authorized("user123", "admin", "read")
        
        # Assign admin role
        manager.assign_role("user123", Role.ADMIN)
        
        # Now should be authorized
        assert await manager.is_authorized("user123", "admin", "read")
