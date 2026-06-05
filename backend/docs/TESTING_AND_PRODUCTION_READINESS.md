# FinancialEdApp — Testing & Production Readiness Guide

> **Audience:** Developers, QA engineers, and release managers.  
> **Updated:** 2026-02-28

---

## Table of Contents
1. [Test Pyramid Overview](#1-test-pyramid-overview)
2. [Auth Testing — Login, Signup, Two-Factor (2FA)](#2-auth-testing)
3. [Budget & Financial Methods Testing](#3-budget--financial-methods-testing)
4. [Data Deletion & GDPR Compliance Testing](#4-data-deletion--gdpr-compliance-testing)
5. [Cross-User Data Isolation (Security)](#5-cross-user-data-isolation)
6. [Notifications Testing](#6-notifications-testing)
7. [Frontend UI/UX Validation](#7-frontend-uiux-validation)
8. [Running All Tests Locally](#8-running-all-tests-locally)
9. [CI/CD Integration](#9-cicd-integration)
10. [Production Readiness Checklist](#10-production-readiness-checklist)

---

## 1. Test Pyramid Overview

```
                         ┌─────────────┐
                         │  E2E / UI   │  (Playwright — planned)
                         └──────┬──────┘
                    ┌───────────┴────────────┐
                    │  Live Integration Tests │  tests/live/  (real Postgres + Redis)
                    └───────────┬────────────┘
               ┌────────────────┴────────────────┐
               │  BDD / Behaviour Tests (pytest-bdd) │  tests/integration/ + tests/features/
               └────────────────┬────────────────┘
          ┌──────────────────────┴──────────────────────┐
          │         Unit Tests (SQLite in-memory)         │  tests/api/, tests/services/
          └────────────────────────────────────────────────┘
```

| Layer | Location | DB | Markers | Speed |
|---|---|---|---|---|
| Unit | `tests/api/`, `tests/services/` | SQLite (in-memory) | `unit` | < 5 s |
| BDD | `tests/integration/` + `tests/features/*.feature` | SQLite + mocks | `bdd`, `integration` | < 30 s |
| Live Integration | `tests/live/` | Real Postgres + Redis | `live`, `live_auth`, etc. | < 2 min |
| E2E UI | `frontend/` (Playwright — planned) | Full stack | — | < 5 min |

---

## 2. Auth Testing

### 2.1 What Is Tested

| Scenario | File | Status |
|---|---|---|
| Register returns 201 + access/refresh tokens | `test_auth_live.py::TestRegistration` | ✅ |
| Duplicate email → 409 Conflict | `test_auth_live.py::TestRegistration` | ✅ |
| Weak/short password → 422 | `test_auth_live.py::TestRegistration` | ✅ |
| Invalid email format → 422 | `test_auth_live.py::TestRegistration` | ✅ |
| Login correct credentials → 200 + tokens | `test_auth_live.py::TestLogin` | ✅ |
| Login wrong password → 401 (no user-enumeration) | `test_auth_live.py::TestLogin` | ✅ |
| Login nonexistent email → 401 | `test_auth_live.py::TestLogin` | ✅ |
| Login inactive account → 401 | `test_auth_live.py::TestLogin` | ✅ |
| `/me` returns authenticated user's info | `test_auth_live.py::TestMeEndpoint` | ✅ |
| `/me` without token → 401 | `test_auth_live.py::TestMeEndpoint` | ✅ |
| `/me` with expired JWT → 401 | `test_auth_live.py::TestMeEndpoint` | ✅ |
| Token refresh with valid refresh token → new access_token | `test_auth_live.py::TestTokenRefresh` | ✅ |
| Token refresh with invalid token → 401 | `test_auth_live.py::TestTokenRefresh` | ✅ |
| 2FA setup returns TOTP provisioning URI | `test_auth_live.py::TestTwoFactorAuth` | ✅ |
| 2FA verify with valid TOTP code → 200 | `test_auth_live.py::TestTwoFactorAuth` | ✅ |
| 2FA verify with invalid code → 400/401 | `test_auth_live.py::TestTwoFactorAuth` | ✅ |
| 2FA setup requires authentication | `test_auth_live.py::TestTwoFactorAuth` | ✅ |
| Brute-force rate limiting (BDD) | `test_bdd_authentication.py` + `authentication.feature` | ✅ |
| Security headers on all responses | `test_auth_live.py::TestSecurityHeaders` | ✅ |
| CORS preflight handled | `test_auth_live.py::TestSecurityHeaders` | ✅ |

### 2.2 How 2FA Works (End-to-End)
```
User Login ──→ POST /api/v1/auth/login  → { access_token, refresh_token }
                      │
                      ▼
Enable 2FA   ──→ POST /api/v1/2fa/setup  → { secret, provisioning_uri (otpauth://…) }
                      │
                      ▼ (user scans QR with Google Authenticator / Authy)
                      │
Verify 2FA   ──→ POST /api/v1/2fa/verify  { code: "123456" }
                      │
                      ▼ (TOTP validated against stored secret via pyotp)
                 2FA enabled on account
```

### 2.3 Run Auth Tests Only
```bash
cd backend
source .venv/bin/activate
pytest tests/live/test_auth_live.py -v -m live_auth
# BDD:
pytest tests/integration/test_bdd_authentication.py -v -m bdd
```

---

## 3. Budget & Financial Methods Testing

### 3.1 Budget CRUD Test Coverage

| Scenario | File | Status |
|---|---|---|
| Create budget → 201 + `id` + `allocated_amount` | `test_budgets_live.py::TestBudgetCreation` | ✅ |
| Create without auth → 401 | `test_budgets_live.py` | ✅ |
| Negative amount → 422 | `test_budgets_live.py` | ✅ |
| Zero amount → 400/422 | `test_budgets_live.py` | ✅ |
| Missing category → 422 | `test_budgets_live.py` | ✅ |
| Duplicate user/month/category → 409 | `test_budgets_live.py` | ✅ |
| List budgets (only own) | `test_budgets_live.py::TestBudgetRetrieval` | ✅ |
| Filter by month | `test_budgets_live.py::TestBudgetRetrieval` | ✅ |
| Get by ID | `test_budgets_live.py::TestBudgetRetrieval` | ✅ |
| Update allocated amount | `test_budgets_live.py::TestBudgetUpdate` | ✅ |
| Delete budget | `test_budgets_live.py::TestBudgetDeletion` | ✅ |
| Budget alert at threshold | `test_budgets_live.py::TestBudgetAlerts` | ✅ |

### 3.2 Expense CRUD + Financial Math Coverage

| Scenario | File | Status |
|---|---|---|
| Create expense → 201 + correct `amount` | `test_expenses_live.py::TestExpenseCreation` | ✅ |
| Negative/zero amount → 422 | `test_expenses_live.py` | ✅ |
| List expenses with pagination | `test_expenses_live.py::TestExpenseRetrieval` | ✅ |
| Category total calculation | `test_expenses_live.py::TestFinancialCalculations` | ✅ |
| Monthly summary sums all expenses | `test_expenses_live.py::TestFinancialCalculations` | ✅ |
| Update expense fields | `test_expenses_live.py::TestExpenseUpdate` | ✅ |
| Delete expense | `test_expenses_live.py::TestExpenseDeletion` | ✅ |

### 3.3 BDD Feature Tests (Gherkin)
```
tests/features/budgets.feature
tests/features/expenses.feature
tests/features/rate_limiting.feature
tests/features/security.feature
```
Each scenario maps to step implementations in `tests/integration/`.

```bash
pytest tests/integration/test_bdd_expenses.py -v -m bdd
pytest tests/live/test_budgets_live.py -v -m live_budgets
pytest tests/live/test_expenses_live.py -v -m live_expenses
```

---

## 4. Data Deletion & GDPR Compliance Testing

### 4.1 What Is Tested

| Scenario | File | Status |
|---|---|---|
| GDPR export returns user's own data only | `test_notifications_gdpr_live.py::TestGDPR` | ✅ |
| GDPR export does NOT leak other users' data | `test_notifications_gdpr_live.py::TestGDPR` | ✅ |
| Account deletion removes user from auth DB | `test_notifications_gdpr_live.py::TestGDPR` | ✅ |
| Account deletion cascades to all data records | `test_notifications_gdpr_live.py::TestGDPR` | ✅ |
| Right-to-be-forgotten: login after deletion → 401 | `test_notifications_gdpr_live.py::TestGDPR` | ✅ |
| Goals CRUD (per-user scoped) | `test_notifications_gdpr_live.py::TestGoals` | ✅ |
| Loans CRUD (per-user scoped) | `test_notifications_gdpr_live.py::TestLoans` | ✅ |

### 4.2 GDPR Flow
```
User requests export → GET /api/v1/gdpr/export
    → Returns JSON: { user, profile, expenses, budgets, goals, loans, notifications }
    → All records owned by authenticated user only

User requests deletion → DELETE /api/v1/gdpr/account
    → Cascade deletes: notifications, expenses, budgets, goals, loans, profile
    → Deletes user row from auth DB
    → Subsequent login returns 401 (not 500)
```

```bash
pytest tests/live/test_notifications_gdpr_live.py -v -m live_gdpr
```

---

## 5. Cross-User Data Isolation

This is the **most critical security test category**. Every entity (budgets, expenses, goals, loans, notifications) must be scoped to the authenticated user's ID. No user should ever see another user's data.

### 5.1 How Isolation Is Enforced (Backend)

- All repository queries include a `WHERE user_id = :current_user_id` filter.
- JWT `sub` claim is extracted from the access token by `get_current_user` dependency.
- No endpoint accepts `user_id` as a query/body parameter from the client.
- Database-level: all data tables have `user_id` FK + indexes.

### 5.2 Test Coverage

| Scenario | Tested In |
|---|---|
| User A cannot read User B's `/me` | `TestCrossUserIsolation` (auth) |
| JWT tokens carry distinct `sub` claims | `TestCrossUserIsolation` (auth) |
| User A's budget list contains no User B budgets | `TestBudgetRetrieval` (budgets) |
| User B cannot DELETE User A's budget | `TestBudgetDeletion` (budgets) |
| User A's expenses not visible to User B | `TestExpenseIsolation` (expenses) |
| User B cannot modify User A's expense | `TestExpenseUpdate` (expenses) |
| Notification IDs have zero overlap across users | `TestNotifications` (notifications) |
| User B cannot mark User A's notification read | `TestNotifications` (notifications) |

```bash
# Run all cross-user isolation tests
pytest tests/live/ -v -k "isolation or cross_user"
```

---

## 6. Notifications Testing

### 6.1 What Is Tested

| Scenario | Status |
|---|---|
| List notifications requires auth | ✅ |
| Each user sees only their own notifications | ✅ |
| No notification ID overlap between users | ✅ |
| Mark notification as read via PATCH | ✅ |
| Verified `is_read=True` after marking | ✅ |
| User B cannot read/modify User A's notification | ✅ |

### 6.2 Notification Delivery (Backend)
- Notifications are created server-side (budget alerts, goal milestones, etc.)
- Real-time delivery via **WebSocket** (`/api/v1/ws/notifications`), backed by Redis pub/sub.
- Fallback: polling `GET /api/v1/notifications/` on page focus.

### 6.3 Frontend Notification UI
- Bell icon in header shows **unread badge count** (red bubble).
- Dropdown shows last 5 notifications with `read`/`unread` distinction.
- Clicking a notification marks it as read via `markNotificationAsRead()`.

```bash
pytest tests/live/test_notifications_gdpr_live.py -v -m live_notifications
```

---

## 7. Frontend UI/UX Validation

### 7.1 Authentication Pages

#### LoginPage (`/login`)
- ✅ Real-time email validation (debounced, 300 ms)  
- ✅ Password show/hide toggle  
- ✅ Animated error banner with clear button  
- ✅ Loading spinner during API call  
- ✅ Demo account quick-fill button  
- ✅ Link to `/register`  
- ✅ Footer: "🔒 Your data is secure and encrypted"

#### RegisterPage (`/register`)
- ✅ Name, email, password, confirm-password fields  
- ✅ Live password-strength meter (4 levels: weak → strong)  
- ✅ Confirm-password mismatch error  
- ✅ Min 8 chars enforced client-side  
- ✅ Redirects to `/login` on success

### 7.2 Application Layout
- ✅ Sidebar navigation: Dashboard, Expenses, Budgets, Loans, Goals, Reports, Chat, Settings  
- ✅ Header: notification bell with unread badge, user avatar with name/email dropdown  
- ✅ Responsive: sidebar collapses on mobile with hamburger menu  
- ✅ Profile dropdown shows `user.name` + `user.email` from auth state  
- ✅ "View Profile" + "Settings" + "Logout" options  
- ✅ All protected routes redirect to `/login` if not authenticated

### 7.3 Dashboard
- ✅ Greets user by name: `Welcome back, {user.name}!`  
- ✅ Loads expenses, budgets, goals, loans on mount  
- ✅ Re-fetches on tab visibility change (real-time feel)  
- ✅ Quick action buttons: "Add Expense" and "Reports"

### 7.4 Settings Page
- ✅ Profile update (name, email)  
- ✅ Password change with current/new/confirm fields  
- ✅ Currency preference  
- ✅ Notification preferences  
- ✅ Income manager (IncomeManager component)  
- ✅ GDPR export / account deletion section  
- ✅ Logout from all sessions

### 7.5 Missing: Contact & Owner Information

> **⚠️ PRODUCTION GAP IDENTIFIED**: The frontend currently does **not** display:
> - App owner / company name  
> - Contact email / support email  
> - Feature list on the landing page  
> - Privacy Policy / Terms of Service links  
>
> These are **required** for production. See the fix below.

---

## 8. Running All Tests Locally

### Prerequisites
```bash
# 1. Start infra containers (Postgres auth + data + Redis)
docker compose -f docker-compose.dev.yml up -d

# 2. Activate virtual environment
cd backend
source .venv/bin/activate

# 3. Verify backend is healthy
uvicorn app.main:app --reload --port 8000 &
curl http://localhost:8000/health
```

### Run Unit Tests (no containers needed)
```bash
pytest tests/api/ tests/services/ tests/core/ -v -m "not live" --tb=short
```

### Run BDD Tests
```bash
pytest tests/integration/ -v -m bdd --tb=short
```

### Run Live Integration Tests (requires running containers)
```bash
# All live tests
pytest tests/live/ -v -m live --tb=short

# Individual suites
pytest tests/live/test_auth_live.py          -v -m live_auth
pytest tests/live/test_budgets_live.py       -v -m live_budgets
pytest tests/live/test_expenses_live.py      -v -m live_expenses
pytest tests/live/test_notifications_gdpr_live.py -v -m "live_notifications or live_gdpr"
```

### Run Everything
```bash
pytest -v --tb=short 2>&1 | tee test-results.log
```

### Test Markers Quick Reference
| Command | What Runs |
|---|---|
| `pytest -m unit` | Fast unit tests (SQLite, mocked Redis) |
| `pytest -m bdd` | Gherkin BDD scenarios |
| `pytest -m live` | All live integration tests |
| `pytest -m live_auth` | Auth: login, signup, 2FA |
| `pytest -m live_budgets` | Budget CRUD + alerts |
| `pytest -m live_expenses` | Expense CRUD + math |
| `pytest -m live_notifications` | Notifications delivery |
| `pytest -m live_gdpr` | GDPR export + deletion |
| `pytest -m security` | Rate limiting, security headers |

---

## 9. CI/CD Integration

Add these stages to your pipeline (GitHub Actions example):

```yaml
jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r backend/requirements.txt
      - run: pytest backend/tests/api/ backend/tests/services/ -m "not live" --tb=short

  live-tests:
    runs-on: ubuntu-latest
    services:
      postgres_auth:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: finedu_admin
          POSTGRES_PASSWORD: finedu_admin_password
          POSTGRES_DB: auth_db
        ports: ["55432:5432"]
      postgres_data:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: finedu_admin
          POSTGRES_PASSWORD: finedu_admin_password
          POSTGRES_DB: financial_ed_db
        ports: ["55433:5432"]
      redis:
        image: redis:7-alpine
        options: --requirepass finedu_redis_password
        ports: ["56379:6379"]
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r backend/requirements.txt
      - run: pytest backend/tests/live/ -m live --tb=short
```

---

## 10. Production Readiness Checklist

### Backend
- [x] All credentials loaded from environment variables (no hardcoded secrets)
- [x] JWT signed with `JWT_SECRET_KEY` from env
- [x] Passwords hashed with bcrypt (never stored plaintext)
- [x] Rate limiting on auth endpoints (login: 5/60s, register: 3/60s)
- [x] Security headers: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`
- [x] CORS restricted to `ALLOWED_ORIGINS` from env
- [x] TOTP 2FA via pyotp
- [x] GDPR: data export + account deletion endpoints
- [x] Refresh tokens stored in DB (can be revoked)
- [x] Connection pooling configured for Postgres and Redis
- [x] Health check endpoint at `/health`
- [x] Structured JSON logging
- [x] All data scoped by `user_id` (no cross-user leakage)

### Database
- [x] Two separate Postgres instances (auth DB + data DB)
- [x] Init scripts create schemas and extensions
- [x] Alembic migrations ready
- [x] Docker volumes for persistent data

### Testing
- [x] Unit tests (fast, no I/O)
- [x] BDD Gherkin scenarios for auth, budgets, expenses, rate limiting, security
- [x] Live integration tests for all critical flows
- [x] Cross-user isolation validated
- [x] GDPR compliance validated
- [ ] E2E Playwright tests (frontend — planned)

### Frontend
- [x] Protected routes redirect unauthenticated users to `/login`
- [x] Client-side validation on all forms
- [x] Real-time email validation (debounced)
- [x] Password strength meter
- [x] Error banners with dismiss
- [x] Loading states on all async actions
- [x] Responsive layout (mobile + desktop)
- [x] Notification bell with unread count
- [x] User name/email shown in header
- [ ] **Contact / owner information on public pages** ← Add before go-live
- [ ] **Feature list / marketing copy on landing** ← Add before go-live
- [ ] **Privacy Policy + Terms of Service links** ← Required for GDPR compliance
- [ ] **Playwright E2E tests** ← Planned

---

*Generated by GitHub Copilot — FinancialEdApp project.*
