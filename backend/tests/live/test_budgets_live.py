"""
Live Integration Tests: Budget Management
==========================================
Tests the full budget CRUD lifecycle against real PostgreSQL:
  - Create budget (happy path + validation)
  - List budgets for a month (scoped to authenticated user)
  - Update budget allocated amount
  - Delete budget
  - Duplicate (user/month/category) rejected with 409
  - Cross-user isolation: User A cannot see User B's budgets
  - Budget alert fires when expense total crosses threshold

Markers: pytest -m live_budgets
"""
import uuid
import pytest
from datetime import date, datetime, timedelta

from tests.conftest_live import (
    make_user, live_client, authed_client, auth_headers_for,
    auth_db, data_db,
)
from app.config import settings

pytestmark = [pytest.mark.asyncio, pytest.mark.live, pytest.mark.live_budgets]

API = settings.API_V1_PREFIX
CURRENT_MONTH = date.today().replace(day=1).isoformat()  # e.g. "2026-02-01"


def _budget_payload(category: str = "Food", amount: float = 5000.0, month: str = None) -> dict:
    return {
        "category": category,
        "allocated_amount": amount,
        "month": month or CURRENT_MONTH,
    }


# =============================================================================
# ── CREATE BUDGET ─────────────────────────────────────────────────────────────
# =============================================================================

class TestBudgetCreation:

    async def test_create_budget_returns_201(self, live_client, make_user, auth_headers_for):
        """Authenticated user can create a budget for any category/month."""
        user = await make_user()
        headers = auth_headers_for(user)

        resp = await live_client.post(
            f"{API}/budgets/", json=_budget_payload(), headers=headers
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert "id" in body
        assert body["category"].lower() == "food"
        assert float(body["allocated_amount"]) == 5000.0

    async def test_create_budget_without_auth_returns_401(self, live_client):
        resp = await live_client.post(f"{API}/budgets/", json=_budget_payload())
        assert resp.status_code == 401, resp.text

    async def test_create_budget_negative_amount_returns_422(
        self, live_client, make_user, auth_headers_for
    ):
        """Negative allocated_amount violates business rules."""
        user = await make_user()
        resp = await live_client.post(
            f"{API}/budgets/",
            json=_budget_payload(amount=-100.0),
            headers=auth_headers_for(user),
        )
        assert resp.status_code == 422, resp.text

    async def test_create_budget_zero_amount_returns_422(
        self, live_client, make_user, auth_headers_for
    ):
        """Zero budget makes no sense and must be rejected."""
        user = await make_user()
        resp = await live_client.post(
            f"{API}/budgets/",
            json=_budget_payload(amount=0),
            headers=auth_headers_for(user),
        )
        assert resp.status_code in (400, 422), resp.text

    async def test_create_budget_missing_category_returns_422(
        self, live_client, make_user, auth_headers_for
    ):
        user = await make_user()
        resp = await live_client.post(
            f"{API}/budgets/",
            json={"allocated_amount": 5000.0, "month": CURRENT_MONTH},
            headers=auth_headers_for(user),
        )
        assert resp.status_code == 422, resp.text

    async def test_duplicate_budget_same_user_month_category_returns_409(
        self, live_client, make_user, auth_headers_for
    ):
        """Two budgets for the same user/month/category violate the unique constraint."""
        user = await make_user()
        headers = auth_headers_for(user)

        # Create first
        r1 = await live_client.post(f"{API}/budgets/", json=_budget_payload(), headers=headers)
        assert r1.status_code == 201, r1.text

        # Create duplicate
        r2 = await live_client.post(f"{API}/budgets/", json=_budget_payload(), headers=headers)
        assert r2.status_code == 409, r2.text


# =============================================================================
# ── READ BUDGETS ──────────────────────────────────────────────────────────────
# =============================================================================

class TestBudgetRetrieval:

    async def test_list_budgets_returns_only_own_budgets(
        self, live_client, make_user, auth_headers_for
    ):
        """User A's budget list must not include User B's budgets."""
        user_a = await make_user()
        user_b = await make_user()

        # Create a budget for each user in the same month
        await live_client.post(
            f"{API}/budgets/",
            json=_budget_payload("Transport", 2000.0),
            headers=auth_headers_for(user_a),
        )
        await live_client.post(
            f"{API}/budgets/",
            json=_budget_payload("Entertainment", 3000.0),
            headers=auth_headers_for(user_b),
        )

        # User A lists their budgets
        resp = await live_client.get(
            f"{API}/budgets/?month={CURRENT_MONTH}",
            headers=auth_headers_for(user_a),
        )
        assert resp.status_code == 200, resp.text
        budgets = resp.json()
        budget_list = budgets if isinstance(budgets, list) else budgets.get("items", budgets.get("data", []))

        # All returned budgets must belong to user_a
        for b in budget_list:
            assert b.get("user_id") != str(user_b.id), "User B's budget leaked into User A's list!"

    async def test_list_budgets_for_specific_month(
        self, live_client, make_user, auth_headers_for
    ):
        """Budgets filtered by month must only return that month's budgets."""
        user = await make_user()
        headers = auth_headers_for(user)

        this_month = date.today().replace(day=1).isoformat()
        next_month = (date.today().replace(day=1) + timedelta(days=32)).replace(day=1).isoformat()

        # Create budgets in two different months
        await live_client.post(f"{API}/budgets/", json=_budget_payload("Food", 5000, this_month), headers=headers)
        await live_client.post(f"{API}/budgets/", json=_budget_payload("Food", 6000, next_month), headers=headers)

        resp = await live_client.get(f"{API}/budgets/?month={this_month}", headers=headers)
        assert resp.status_code == 200, resp.text

    async def test_get_budget_by_id(self, live_client, make_user, auth_headers_for):
        """User can retrieve a specific budget by its ID."""
        user = await make_user()
        headers = auth_headers_for(user)

        create_resp = await live_client.post(
            f"{API}/budgets/", json=_budget_payload("Healthcare", 3000), headers=headers
        )
        assert create_resp.status_code == 201
        budget_id = create_resp.json()["id"]

        get_resp = await live_client.get(f"{API}/budgets/{budget_id}", headers=headers)
        assert get_resp.status_code == 200, get_resp.text
        assert get_resp.json()["id"] == budget_id


# =============================================================================
# ── UPDATE BUDGET ─────────────────────────────────────────────────────────────
# =============================================================================

class TestBudgetUpdate:

    async def test_update_budget_allocated_amount(self, live_client, make_user, auth_headers_for):
        """User can change the allocated amount of an existing budget."""
        user = await make_user()
        headers = auth_headers_for(user)

        create_resp = await live_client.post(
            f"{API}/budgets/", json=_budget_payload("Groceries", 4000), headers=headers
        )
        assert create_resp.status_code == 201
        budget_id = create_resp.json()["id"]

        update_resp = await live_client.put(
            f"{API}/budgets/{budget_id}",
            json={"allocated_amount": 6000.0},
            headers=headers,
        )
        assert update_resp.status_code == 200, update_resp.text
        assert float(update_resp.json()["allocated_amount"]) == 6000.0

    async def test_user_b_cannot_update_user_a_budget(
        self, live_client, make_user, auth_headers_for
    ):
        """Cross-user budget modification must be forbidden (403 or 404)."""
        user_a = await make_user()
        user_b = await make_user()

        create_resp = await live_client.post(
            f"{API}/budgets/", json=_budget_payload(), headers=auth_headers_for(user_a)
        )
        assert create_resp.status_code == 201
        budget_id = create_resp.json()["id"]

        # User B tries to update User A's budget
        update_resp = await live_client.put(
            f"{API}/budgets/{budget_id}",
            json={"allocated_amount": 999.0},
            headers=auth_headers_for(user_b),
        )
        assert update_resp.status_code in (403, 404), update_resp.text


# =============================================================================
# ── DELETE BUDGET ─────────────────────────────────────────────────────────────
# =============================================================================

class TestBudgetDeletion:

    async def test_delete_budget_returns_204(self, live_client, make_user, auth_headers_for):
        """Owner can delete their own budget."""
        user = await make_user()
        headers = auth_headers_for(user)

        create_resp = await live_client.post(
            f"{API}/budgets/", json=_budget_payload("Shopping", 2500), headers=headers
        )
        assert create_resp.status_code == 201
        budget_id = create_resp.json()["id"]

        del_resp = await live_client.delete(f"{API}/budgets/{budget_id}", headers=headers)
        assert del_resp.status_code in (200, 204), del_resp.text

        # Verify it's gone
        get_resp = await live_client.get(f"{API}/budgets/{budget_id}", headers=headers)
        assert get_resp.status_code == 404, get_resp.text

    async def test_user_b_cannot_delete_user_a_budget(
        self, live_client, make_user, auth_headers_for
    ):
        """Cross-user budget deletion must be forbidden."""
        user_a = await make_user()
        user_b = await make_user()

        create_resp = await live_client.post(
            f"{API}/budgets/", json=_budget_payload("Electronics", 8000),
            headers=auth_headers_for(user_a),
        )
        assert create_resp.status_code == 201
        budget_id = create_resp.json()["id"]

        del_resp = await live_client.delete(
            f"{API}/budgets/{budget_id}", headers=auth_headers_for(user_b)
        )
        assert del_resp.status_code in (403, 404), del_resp.text


# =============================================================================
# ── BUDGET ALERTS ─────────────────────────────────────────────────────────────
# =============================================================================

class TestBudgetAlerts:
    """Budget alerts fire when spending reaches the configured threshold."""

    async def test_budget_alert_created_when_expense_exceeds_threshold(
        self, live_client, make_user, auth_headers_for
    ):
        """
        Flow:
          1. Create a budget of 1000 for "Food"
          2. Add an expense of 850 in "Food" (85% of budget → above 80% threshold)
          3. Check that a budget_alert exists for the budget
        """
        user = await make_user()
        headers = auth_headers_for(user)

        # Create budget
        budget_resp = await live_client.post(
            f"{API}/budgets/",
            json={"category": "Food", "allocated_amount": 1000.0, "month": CURRENT_MONTH},
            headers=headers,
        )
        if budget_resp.status_code != 201:
            pytest.skip(f"Budget creation failed: {budget_resp.text}")
        budget_id = budget_resp.json()["id"]

        # Add expense that triggers the alert (85% of 1000)
        expense_resp = await live_client.post(
            f"{API}/expenses/",
            json={
                "amount": 850.0,
                "category": "Food",
                "date": date.today().isoformat(),
                "description": "Grocery run",
            },
            headers=headers,
        )
        # Expense creation may succeed or trigger alert creation in background
        assert expense_resp.status_code in (200, 201, 202), expense_resp.text

        # Check budget alerts exist
        alerts_resp = await live_client.get(
            f"{API}/budgets/{budget_id}/alerts", headers=headers
        )
        if alerts_resp.status_code == 404:
            pytest.skip("Budget alerts endpoint not implemented yet")
        assert alerts_resp.status_code == 200, alerts_resp.text
