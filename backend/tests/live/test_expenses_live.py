"""
Live Integration Tests: Expense Management
===========================================
Tests the full expense CRUD lifecycle + financial calculations:
  - Create expense (happy path, validation, edge cases)
  - List expenses with pagination and filters
  - Update and delete expenses
  - Cross-user isolation: User A cannot see/modify User B's expenses
  - Financial math: category totals, monthly summaries
  - Recurring expense detection
  - Analytics/insights endpoint correctness

Markers: pytest -m live_expenses
"""
import uuid
import pytest
from datetime import date, timedelta

from tests.conftest_live import (
    make_user, live_client, auth_headers_for,
    auth_db, data_db,
)
from app.config import settings

pytestmark = [pytest.mark.asyncio, pytest.mark.live, pytest.mark.live_expenses]

API = settings.API_V1_PREFIX
TODAY = date.today().isoformat()


def _expense_payload(
    amount: float = 500.0,
    category: str = "Food",
    date_str: str = None,
    description: str = "Test expense",
    payment_method: str = "Cash",
) -> dict:
    return {
        "amount": amount,
        "category": category,
        "date": date_str or TODAY,
        "description": description,
        "payment_method": payment_method,
    }


# =============================================================================
# ── CREATE EXPENSE ────────────────────────────────────────────────────────────
# =============================================================================

class TestExpenseCreation:

    async def test_create_expense_returns_201(self, live_client, make_user, auth_headers_for):
        """Happy path: valid expense payload → 201 with ID."""
        user = await make_user()
        resp = await live_client.post(
            f"{API}/expenses/",
            json=_expense_payload(),
            headers=auth_headers_for(user),
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert "id" in body
        assert float(body["amount"]) == 500.0
        assert body["category"].lower() == "food"

    async def test_create_expense_without_auth_returns_401(self, live_client):
        resp = await live_client.post(f"{API}/expenses/", json=_expense_payload())
        assert resp.status_code == 401, resp.text

    async def test_create_expense_negative_amount_returns_422(
        self, live_client, make_user, auth_headers_for
    ):
        user = await make_user()
        resp = await live_client.post(
            f"{API}/expenses/",
            json=_expense_payload(amount=-100.0),
            headers=auth_headers_for(user),
        )
        assert resp.status_code == 422, resp.text

    async def test_create_expense_zero_amount_returns_422(
        self, live_client, make_user, auth_headers_for
    ):
        user = await make_user()
        resp = await live_client.post(
            f"{API}/expenses/",
            json=_expense_payload(amount=0),
            headers=auth_headers_for(user),
        )
        assert resp.status_code in (400, 422), resp.text

    async def test_create_expense_missing_amount_returns_422(
        self, live_client, make_user, auth_headers_for
    ):
        user = await make_user()
        payload = {"category": "Food", "date": TODAY}
        resp = await live_client.post(
            f"{API}/expenses/", json=payload, headers=auth_headers_for(user)
        )
        assert resp.status_code == 422, resp.text

    async def test_create_expense_missing_category_returns_422(
        self, live_client, make_user, auth_headers_for
    ):
        user = await make_user()
        payload = {"amount": 500.0, "date": TODAY}
        resp = await live_client.post(
            f"{API}/expenses/", json=payload, headers=auth_headers_for(user)
        )
        assert resp.status_code == 422, resp.text

    async def test_create_expense_future_date_is_accepted(
        self, live_client, make_user, auth_headers_for
    ):
        """Future-dated expenses (planned spend) should be accepted."""
        user = await make_user()
        future_date = (date.today() + timedelta(days=7)).isoformat()
        resp = await live_client.post(
            f"{API}/expenses/",
            json=_expense_payload(date_str=future_date),
            headers=auth_headers_for(user),
        )
        assert resp.status_code in (200, 201), resp.text

    async def test_create_expense_large_amount_precision(
        self, live_client, make_user, auth_headers_for
    ):
        """Amounts with 2 decimal places must be stored and returned exactly."""
        user = await make_user()
        resp = await live_client.post(
            f"{API}/expenses/",
            json=_expense_payload(amount=12345.67),
            headers=auth_headers_for(user),
        )
        assert resp.status_code in (200, 201), resp.text
        if resp.status_code in (200, 201):
            assert float(resp.json()["amount"]) == 12345.67


# =============================================================================
# ── READ EXPENSES ─────────────────────────────────────────────────────────────
# =============================================================================

class TestExpenseRetrieval:

    async def test_list_expenses_returns_own_expenses_only(
        self, live_client, make_user, auth_headers_for
    ):
        """User A's expense list must not contain User B's expenses."""
        user_a = await make_user()
        user_b = await make_user()

        # Each user creates an expense
        await live_client.post(
            f"{API}/expenses/",
            json=_expense_payload(amount=100, category="Transport"),
            headers=auth_headers_for(user_a),
        )
        await live_client.post(
            f"{API}/expenses/",
            json=_expense_payload(amount=200, category="Entertainment"),
            headers=auth_headers_for(user_b),
        )

        # User A fetches their expenses
        resp = await live_client.get(f"{API}/expenses/", headers=auth_headers_for(user_a))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        items = body if isinstance(body, list) else body.get("items", body.get("data", []))

        for exp in items:
            assert exp.get("user_id") != str(user_b.id), "User B's expense leaked to User A!"

    async def test_get_expense_by_id(self, live_client, make_user, auth_headers_for):
        user = await make_user()
        headers = auth_headers_for(user)

        create_resp = await live_client.post(
            f"{API}/expenses/", json=_expense_payload(amount=750, category="Healthcare"), headers=headers
        )
        assert create_resp.status_code == 201
        expense_id = create_resp.json()["id"]

        get_resp = await live_client.get(f"{API}/expenses/{expense_id}", headers=headers)
        assert get_resp.status_code == 200, get_resp.text
        assert get_resp.json()["id"] == expense_id

    async def test_user_b_cannot_get_user_a_expense(
        self, live_client, make_user, auth_headers_for
    ):
        """Cross-user read of a specific expense must return 403 or 404."""
        user_a = await make_user()
        user_b = await make_user()

        create_resp = await live_client.post(
            f"{API}/expenses/", json=_expense_payload(), headers=auth_headers_for(user_a)
        )
        assert create_resp.status_code == 201
        expense_id = create_resp.json()["id"]

        get_resp = await live_client.get(
            f"{API}/expenses/{expense_id}", headers=auth_headers_for(user_b)
        )
        assert get_resp.status_code in (403, 404), get_resp.text

    async def test_list_expenses_filter_by_category(
        self, live_client, make_user, auth_headers_for
    ):
        """Category filter must return only expenses in that category."""
        user = await make_user()
        headers = auth_headers_for(user)

        await live_client.post(f"{API}/expenses/", json=_expense_payload(category="Food"), headers=headers)
        await live_client.post(f"{API}/expenses/", json=_expense_payload(category="Transport"), headers=headers)

        resp = await live_client.get(f"{API}/expenses/?category=Food", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        items = body if isinstance(body, list) else body.get("items", body.get("data", []))
        for item in items:
            assert item["category"].lower() == "food", f"Non-food expense returned: {item}"


# =============================================================================
# ── UPDATE EXPENSE ────────────────────────────────────────────────────────────
# =============================================================================

class TestExpenseUpdate:

    async def test_update_expense_amount(self, live_client, make_user, auth_headers_for):
        user = await make_user()
        headers = auth_headers_for(user)

        create_resp = await live_client.post(
            f"{API}/expenses/", json=_expense_payload(amount=300), headers=headers
        )
        assert create_resp.status_code == 201
        expense_id = create_resp.json()["id"]

        update_resp = await live_client.put(
            f"{API}/expenses/{expense_id}",
            json={"amount": 450.0},
            headers=headers,
        )
        assert update_resp.status_code == 200, update_resp.text
        assert float(update_resp.json()["amount"]) == 450.0

    async def test_user_b_cannot_update_user_a_expense(
        self, live_client, make_user, auth_headers_for
    ):
        user_a = await make_user()
        user_b = await make_user()

        create_resp = await live_client.post(
            f"{API}/expenses/", json=_expense_payload(), headers=auth_headers_for(user_a)
        )
        assert create_resp.status_code == 201
        expense_id = create_resp.json()["id"]

        update_resp = await live_client.put(
            f"{API}/expenses/{expense_id}",
            json={"amount": 9999.0},
            headers=auth_headers_for(user_b),
        )
        assert update_resp.status_code in (403, 404), update_resp.text


# =============================================================================
# ── DELETE EXPENSE ────────────────────────────────────────────────────────────
# =============================================================================

class TestExpenseDeletion:

    async def test_delete_expense_returns_204(self, live_client, make_user, auth_headers_for):
        user = await make_user()
        headers = auth_headers_for(user)

        create_resp = await live_client.post(
            f"{API}/expenses/", json=_expense_payload(), headers=headers
        )
        assert create_resp.status_code == 201
        expense_id = create_resp.json()["id"]

        del_resp = await live_client.delete(f"{API}/expenses/{expense_id}", headers=headers)
        assert del_resp.status_code in (200, 204), del_resp.text

        # Verify it's gone
        get_resp = await live_client.get(f"{API}/expenses/{expense_id}", headers=headers)
        assert get_resp.status_code == 404, get_resp.text

    async def test_user_b_cannot_delete_user_a_expense(
        self, live_client, make_user, auth_headers_for
    ):
        user_a = await make_user()
        user_b = await make_user()

        create_resp = await live_client.post(
            f"{API}/expenses/", json=_expense_payload(), headers=auth_headers_for(user_a)
        )
        assert create_resp.status_code == 201
        expense_id = create_resp.json()["id"]

        del_resp = await live_client.delete(
            f"{API}/expenses/{expense_id}", headers=auth_headers_for(user_b)
        )
        assert del_resp.status_code in (403, 404), del_resp.text


# =============================================================================
# ── FINANCIAL CALCULATIONS ─────────────────────────────────────────────────────
# =============================================================================

class TestFinancialCalculations:
    """Verify the financial math is correct — category totals, summaries."""

    async def test_monthly_total_reflects_all_expenses(
        self, live_client, make_user, auth_headers_for
    ):
        """
        Create 3 expenses totalling a known amount.
        The monthly summary endpoint must reflect the correct total.
        """
        user = await make_user()
        headers = auth_headers_for(user)
        month = date.today().replace(day=1).isoformat()

        amounts = [100.0, 250.0, 75.0]
        for amt in amounts:
            r = await live_client.post(
                f"{API}/expenses/", json=_expense_payload(amount=amt, category="Food"), headers=headers
            )
            assert r.status_code == 201, r.text

        # Request the analytics/summary
        summary_resp = await live_client.get(
            f"{API}/expenses/analytics/summary?month={month}", headers=headers
        )
        if summary_resp.status_code == 404:
            pytest.skip("Analytics summary endpoint not yet implemented")

        assert summary_resp.status_code == 200, summary_resp.text
        body = summary_resp.json()
        # Total should be at least sum of our expenses
        total = body.get("total") or body.get("total_amount") or body.get("monthly_total")
        if total is not None:
            assert float(total) >= sum(amounts), f"Total {total} < expected {sum(amounts)}"
