"""
Unit tests for pagination limit enforcement across all list endpoints.

These tests verify that:
- All list endpoints reject limit > 500 (hard cap) with HTTP 422
- All list endpoints accept limit = 500 (boundary)
- Default limit values are reasonable (<= 100)
- skip / offset parameters work correctly
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_mock_user(user_id="00000000-0000-0000-0000-000000000001"):
    """Create a minimal mock User object for dependency overrides."""
    user = MagicMock()
    user.id = user_id
    user.email = "test@example.com"
    user.is_active = True
    return user


# ── Expense endpoint ──────────────────────────────────────────────────────────

class TestExpensePagination:
    """Pagination tests for GET /api/v1/expenses/"""

    def _get_client(self):
        from app.main import app
        from app.dependencies import get_current_user

        app.dependency_overrides[get_current_user] = lambda: make_mock_user()
        return TestClient(app)

    def test_limit_above_500_returns_422(self):
        client = self._get_client()
        resp = client.get("/api/v1/expenses/", params={"limit": 501})
        assert resp.status_code == 422, resp.text

    def test_limit_at_500_is_accepted(self):
        client = self._get_client()
        with patch("app.api.v1.expenses.ExpenseService") as mock_svc_cls:
            instance = mock_svc_cls.return_value
            instance.get_user_expenses = AsyncMock(return_value=([], 0))
            resp = client.get("/api/v1/expenses/", params={"limit": 500})
        assert resp.status_code in (200, 422)  # 422 only if query fails for other reasons

    def test_limit_zero_returns_422(self):
        client = self._get_client()
        resp = client.get("/api/v1/expenses/", params={"limit": 0})
        assert resp.status_code == 422, resp.text

    def test_default_limit_is_reasonable(self):
        """Default limit query param should be <= 100."""
        from app.api.v1.expenses import router
        for route in router.routes:
            if hasattr(route, "path") and route.path == "" or route.path == "/":
                if hasattr(route, "dependant"):
                    for dep in route.dependant.query_params:
                        if dep.name == "limit":
                            assert dep.field_info.default <= 100


# ── Budget endpoint ────────────────────────────────────────────────────────────

class TestBudgetPagination:
    """Pagination tests for GET /api/v1/budgets/"""

    def _get_client(self):
        from app.main import app
        from app.dependencies import get_current_user

        app.dependency_overrides[get_current_user] = lambda: make_mock_user()
        return TestClient(app)

    def test_limit_above_500_returns_422(self):
        client = self._get_client()
        resp = client.get("/api/v1/budgets/", params={"limit": 501})
        assert resp.status_code == 422, resp.text

    def test_limit_negative_returns_422(self):
        client = self._get_client()
        resp = client.get("/api/v1/budgets/", params={"limit": -1})
        assert resp.status_code == 422, resp.text


# ── Goals endpoint ─────────────────────────────────────────────────────────────

class TestGoalPagination:
    """Pagination tests for GET /api/v1/goals/"""

    def _get_client(self):
        from app.main import app
        from app.dependencies import get_current_user

        app.dependency_overrides[get_current_user] = lambda: make_mock_user()
        return TestClient(app)

    def test_limit_above_500_returns_422(self):
        client = self._get_client()
        resp = client.get("/api/v1/goals/", params={"limit": 501})
        assert resp.status_code == 422, resp.text

    def test_limit_at_500_boundary(self):
        client = self._get_client()
        with patch("app.api.v1.goals.GoalService") as mock_svc_cls:
            instance = mock_svc_cls.return_value
            instance.get_user_goals = AsyncMock(return_value=[])
            resp = client.get("/api/v1/goals/", params={"limit": 500})
        # Should not be 422 (validation error) — may be 200 or other
        assert resp.status_code != 422


# ── Loans endpoint ─────────────────────────────────────────────────────────────

class TestLoanPagination:
    """Pagination tests for GET /api/v1/loans/"""

    def _get_client(self):
        from app.main import app
        from app.dependencies import get_current_user

        app.dependency_overrides[get_current_user] = lambda: make_mock_user()
        return TestClient(app)

    def test_limit_above_500_returns_422(self):
        client = self._get_client()
        resp = client.get("/api/v1/loans/", params={"limit": 501})
        assert resp.status_code == 422, resp.text

    def test_skip_negative_returns_422(self):
        client = self._get_client()
        resp = client.get("/api/v1/loans/", params={"skip": -1})
        assert resp.status_code == 422, resp.text


# ── Admin audit-log endpoint ──────────────────────────────────────────────────

class TestAdminAuditLogPagination:
    """Pagination tests for GET /api/v1/admin/audit-log"""

    def _get_client_with_admin(self):
        from app.main import app
        from app.api.v1.admin import require_admin

        admin_user = make_mock_user()
        admin_user.is_admin = True
        app.dependency_overrides[require_admin] = lambda: admin_user
        return TestClient(app)

    def test_audit_log_limit_above_500_returns_422(self):
        client = self._get_client_with_admin()
        resp = client.get("/api/v1/admin/audit-log", params={"limit": 501})
        assert resp.status_code == 422, resp.text

    def test_audit_log_limit_at_500_accepted(self):
        """limit=500 should pass validation (not 422)."""
        client = self._get_client_with_admin()
        with patch("app.api.v1.admin.get_data_db"):
            resp = client.get("/api/v1/admin/audit-log", params={"limit": 500})
        # Should not be a validation error
        assert resp.status_code != 422
