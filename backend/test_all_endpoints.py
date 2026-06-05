#!/usr/bin/env python3
"""
Quick endpoint tester — verifies all major API endpoints.
Run: python3 test_all_endpoints.py
"""
import httpx
import json
import sys

BASE = "http://localhost:8000"
API = f"{BASE}/api/v1"

def pp(label, resp):
    status = resp.status_code
    try:
        body = resp.json()
    except Exception:
        body = resp.text[:200]
    icon = "✅" if status < 400 else "❌"
    print(f"{icon} {label}: HTTP {status}")
    if status >= 400:
        print(f"   Body: {json.dumps(body, indent=2)[:300]}")
    return status

with httpx.Client(timeout=15) as c:
    # === Public ===
    print("\n===== PUBLIC ENDPOINTS =====")
    pp("Root", c.get(f"{BASE}/"))
    pp("Health", c.get(f"{BASE}/health"))
    pp("Health/live", c.get(f"{BASE}/health/live"))
    pp("Health/ready", c.get(f"{BASE}/health/ready"))
    pp("Docs (Swagger)", c.get(f"{BASE}/docs"))
    pp("OpenAPI JSON", c.get(f"{BASE}/openapi.json"))

    # === Auth: Register ===
    print("\n===== AUTH: REGISTER =====")
    import random
    email = f"endpointtest_{random.randint(10000,99999)}@example.com"
    r = c.post(f"{API}/auth/register", json={"email": email, "password": "TestPass123!", "name": "Tester"})
    pp(f"Register ({email})", r)

    # === Auth: Login ===
    print("\n===== AUTH: LOGIN =====")
    r = c.post(f"{API}/auth/login", json={"email": email, "password": "TestPass123!"})
    pp("Login (correct)", r)
    tokens = r.json()
    access = tokens.get("access_token", "")
    refresh = tokens.get("refresh_token", "")
    headers = {"Authorization": f"Bearer {access}"}

    r = c.post(f"{API}/auth/login", json={"email": email, "password": "WrongPass!"})
    pp("Login (wrong pass → 401)", r)

    r = c.post(f"{API}/auth/login", json={"email": "nobody@x.com", "password": "any"})
    pp("Login (nonexistent → 401)", r)

    # === Auth: /me ===
    print("\n===== AUTH: /ME =====")
    pp("/me (authed)", c.get(f"{API}/auth/me", headers=headers))
    pp("/me (no token → 401)", c.get(f"{API}/auth/me"))
    pp("/me (bad token → 401)", c.get(f"{API}/auth/me", headers={"Authorization": "Bearer bad.token.here"}))

    # === Token Refresh ===
    print("\n===== TOKEN REFRESH =====")
    r = c.post(f"{API}/auth/refresh", json={"refresh_token": refresh})
    pp("Refresh (valid)", r)
    if r.status_code == 200:
        access = r.json().get("access_token", access)
        headers = {"Authorization": f"Bearer {access}"}
    pp("Refresh (invalid → 401)", c.post(f"{API}/auth/refresh", json={"refresh_token": "bad"}))

    # === 2FA ===
    print("\n===== 2FA =====")
    pp("2FA setup", c.post(f"{API}/auth/2fa/setup", headers=headers))
    pp("2FA setup (no auth → 401)", c.post(f"{API}/auth/2fa/setup"))

    # === Expenses ===
    print("\n===== EXPENSES =====")
    r = c.post(f"{API}/expenses/", headers=headers, json={
        "amount": 500, "category": "Food", "date": "2026-02-28",
        "description": "Lunch", "payment_method": "Cash"
    })
    pp("Create expense", r)
    expense_id = None
    if r.status_code in (200, 201):
        expense_id = r.json().get("id")

    pp("List expenses", c.get(f"{API}/expenses/", headers=headers))
    pp("Expense summary", c.get(f"{API}/expenses/summary", headers=headers))
    pp("Create expense (no auth → 401)", c.post(f"{API}/expenses/", json={"amount":1,"category":"Food","date":"2026-02-28"}))
    pp("Create expense (neg amt → 422)", c.post(f"{API}/expenses/", headers=headers, json={"amount":-1,"category":"Food","date":"2026-02-28"}))

    if expense_id:
        pp(f"Get expense {expense_id[:8]}...", c.get(f"{API}/expenses/{expense_id}", headers=headers))
        pp("Update expense", c.put(f"{API}/expenses/{expense_id}", headers=headers, json={"amount":600}))
        pp("Delete expense", c.delete(f"{API}/expenses/{expense_id}", headers=headers))

    # === Budgets ===
    print("\n===== BUDGETS =====")
    r = c.post(f"{API}/budgets/", headers=headers, json={
        "category": "Transport", "allocated_amount": 3000, "month": "2026-02-01"
    })
    pp("Create budget", r)
    budget_id = None
    if r.status_code in (200, 201):
        budget_id = r.json().get("id")

    pp("List budgets", c.get(f"{API}/budgets/", headers=headers, params={"month": "2026-02-01"}))
    pp("Create budget (no auth → 401)", c.post(f"{API}/budgets/", json={"category":"X","allocated_amount":100,"month":"2026-02-01"}))
    pp("Create budget (neg amt → 422)", c.post(f"{API}/budgets/", headers=headers, json={"category":"Food","allocated_amount":-1,"month":"2026-02-01"}))

    if budget_id:
        pp(f"Get budget", c.get(f"{API}/budgets/{budget_id}", headers=headers))
        pp("Update budget", c.put(f"{API}/budgets/{budget_id}", headers=headers, json={"allocated_amount":4000}))
        pp("Delete budget", c.delete(f"{API}/budgets/{budget_id}", headers=headers))

    # === Goals ===
    print("\n===== GOALS =====")
    r = c.post(f"{API}/goals/", headers=headers, json={
        "title": "Vacation Fund", "target_amount": 50000, "current_amount": 5000, "target_date": "2026-12-31"
    })
    pp("Create goal", r)
    goal_id = r.json().get("id") if r.status_code in (200, 201) else None
    pp("List goals", c.get(f"{API}/goals/", headers=headers))
    if goal_id:
        pp("Get goal", c.get(f"{API}/goals/{goal_id}", headers=headers))
        pp("Delete goal", c.delete(f"{API}/goals/{goal_id}", headers=headers))

    # === Loans ===
    print("\n===== LOANS =====")
    r = c.post(f"{API}/loans/", headers=headers, json={
        "name": "Car Loan", "principal_amount": 500000, "interest_rate": 9.5,
        "tenure_months": 60, "start_date": "2026-01-01"
    })
    pp("Create loan", r)
    loan_id = r.json().get("id") if r.status_code in (200, 201) else None
    pp("List loans", c.get(f"{API}/loans/", headers=headers))
    pp("EMI calculator", c.post(f"{API}/loans/calculate-emi", headers=headers, json={
        "principal": 500000, "annual_rate": 9.5, "tenure_months": 60
    }))
    if loan_id:
        pp("Get loan", c.get(f"{API}/loans/{loan_id}", headers=headers))

    # === Notifications ===
    print("\n===== NOTIFICATIONS =====")
    pp("List notifications", c.get(f"{API}/notifications", headers=headers))
    pp("Unread count", c.get(f"{API}/notifications/unread/count", headers=headers))
    pp("Notifications (no auth → 401)", c.get(f"{API}/notifications"))

    # === Exports ===
    print("\n===== EXPORTS =====")
    pp("Export expenses CSV", c.get(f"{API}/exports/expenses/csv", headers=headers))

    # === Enums ===
    print("\n===== ENUMS =====")
    pp("All enums", c.get(f"{API}/enums/all", headers=headers))

    # === GDPR ===
    print("\n===== GDPR =====")
    pp("Privacy policy", c.get(f"{API}/legal/privacy"))
    pp("Terms of service", c.get(f"{API}/legal/terms"))

    # === Admin (should 401/403 for normal user) ===
    print("\n===== ADMIN =====")
    pp("Admin users (normal user)", c.get(f"{API}/admin/users", headers=headers))

    print("\n===== DONE =====")
