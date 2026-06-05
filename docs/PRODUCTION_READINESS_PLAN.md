# Production-Readiness Fix Plan — FinancialEdApp

> **Created:** March 21, 2026  
> **Status:** IN PROGRESS  
> **Scope:** Backend (Phase 1–3) → Frontend (Phase 4–5)  
> **Tracking:** Each ticket has an ID, acceptance criteria, affected files, and a ✅ / 🔴 completion column.

---

## How to Use This Document

1. Work through tickets **in order** — later tickets depend on earlier ones.
2. After finishing each ticket, mark its **Status** column `✅ Done` and add the PR/commit reference.
3. Run the **Acceptance Tests** listed for each ticket before marking done.
4. Do not merge a ticket branch until all acceptance criteria are green.

---

## Summary of All Tickets

| ID | Title | Phase | Severity | Status |
|----|-------|-------|----------|--------|
| BE-01 | Consolidate duplicate security utilities | Backend | 🔴 Critical | ✅ Done |
| BE-02 | Fix deprecated `datetime.utcnow()` everywhere | Backend | 🟡 Medium | ✅ Done |
| BE-03 | Create `LoanRepository` + `ILoanRepository` | Backend | 🔴 Critical | ✅ Done |
| BE-04 | Refactor `LoanService` to use `LoanRepository` | Backend | 🔴 Critical | ✅ Done |
| BE-05 | Split `LoanService` into focused sub-services (SRP) | Backend | 🟠 High | ✅ Done |
| BE-06 | `ExpenseService` inherit `BaseService` | Backend | 🔴 Critical | ✅ Done |
| BE-07 | Fix unused generic `T` in `BaseService` | Backend | 🟡 Medium | ✅ Done |
| BE-08 | Standardize service factory pattern across all routers | Backend | 🟠 High | ✅ Done |
| BE-09 | Consolidate duplicate `LoanStatusEnum` / `LoanStatus` | Backend | 🟡 Medium | ✅ Done |
| BE-10 | Tighten CSP header — remove `unsafe-inline` scripts | Backend | 🟠 High | ✅ Done |
| BE-11 | Remove legacy `_redis_cache` global in `dependencies.py` | Backend | 🟡 Medium | ✅ Done |
| FE-01 | Migrate `BudgetsPage.jsx` → `BudgetsPage.tsx` | Frontend | 🔴 Critical | 🔴 TODO |
| FE-02 | Migrate `GoalsPage.jsx` → `GoalsPage.tsx` | Frontend | 🔴 Critical | 🔴 TODO |
| FE-03 | Migrate `LoansPage.jsx` → full `LoansPage.tsx` | Frontend | 🔴 Critical | 🔴 TODO |
| FE-04 | Migrate `SettingsPage.jsx` → `SettingsPage.tsx` | Frontend | 🔴 Critical | 🔴 TODO |
| FE-05 | Migrate `ReportsPage.jsx` → `ReportsPage.tsx` | Frontend | 🔴 Critical | 🔴 TODO |
| FE-06 | Merge `AdminPage.jsx` into `AdminPage.tsx` | Frontend | 🔴 Critical | 🔴 TODO |
| FE-07 | Fix `api.ts` 401 handler — replace `window.location.href` | Frontend | 🔴 Critical | 🔴 TODO |
| FE-08 | Remove duplicate axios refresh call in `authStore.ts` | Frontend | 🟠 High | 🔴 TODO |
| FE-09 | Split `store/index.ts` into domain store files | Frontend | 🟠 High | 🔴 TODO |
| FE-10 | Split `Layout.tsx` into sub-components | Frontend | 🟠 High | 🔴 TODO |
| FE-11 | Fix `tokenManager.ts` dual API (named exports + default) | Frontend | 🟡 Medium | 🔴 TODO |
| FE-12 | Migrate `OverviewTab` to TypeScript with typed props | Frontend | 🟡 Medium | 🔴 TODO |
| FE-13 | Add frontend unit tests for stores + critical pages | Frontend | 🟡 Medium | 🔴 TODO |

---

## Phase 1 — Backend Critical Fixes

---

### BE-01 · Consolidate Duplicate Security Utilities

**Priority:** 🔴 Critical  
**Status:** 🔴 TODO  
**Principle violated:** DRY, DIP  

#### Problem
Three separate files contain overlapping password-hashing and JWT logic:
- `backend/app/core/security.py` — standalone bcrypt + JWT functions (61 lines)
- `backend/app/utils/security.py` — passlib `CryptContext` + JWT (48 lines)
- `backend/app/core/provider_implementations.py` — `BcryptPasswordHasher` + `JWTTokenProvider` ✅ (canonical)

Callers of `core/security.py` and `utils/security.py` bypass the singleton providers, meaning bcrypt runs with a freshly allocated cost factor on **every call** rather than reusing the app-state singleton.

**Callers of `core/security.py` (must be migrated):**
- `app/dependencies.py` → `decode_token`
- `app/api/v1/websocket.py` → `decode_token`
- `app/seed_users.py` → `hash_password`
- `tests/conftest.py` → `hash_password`, `create_access_token`
- `tests/core/test_security.py` → all functions
- `tests/integration/test_bdd_*.py` → various functions

**Callers of `utils/security.py`:**
- Any file importing `from app.utils.security import ...` (audit with grep)

#### Acceptance Criteria
- [ ] `core/security.py` is **deleted**.
- [ ] `utils/security.py` is **deleted**.
- [ ] All production code imports `decode_token` from `app.core.provider_implementations.JWTTokenProvider` (via injected dependency) or from a single thin re-export shim if a module-level function is truly required (e.g., `dependencies.py`).
- [ ] Test files updated to use the test-safe helpers (see below).
- [ ] A thin `app/core/security_compat.py` shim is created **only** for test fixtures that cannot use DI, forwarding to `JWTTokenProvider` / `BcryptPasswordHasher`. This shim is importable by tests but clearly doc-commented as test-only.
- [ ] `grep -r "from app.core.security import" .` returns **zero** production-code hits.
- [ ] `grep -r "from app.utils.security import" .` returns **zero** hits.
- [ ] All existing tests still pass: `pytest backend/tests/ -x`.

#### Files to Change
| Action | File |
|--------|------|
| DELETE | `backend/app/core/security.py` |
| DELETE | `backend/app/utils/security.py` |
| CREATE | `backend/app/core/security_compat.py` (test shim) |
| UPDATE | `backend/app/dependencies.py` — replace `decode_token` import |
| UPDATE | `backend/app/api/v1/websocket.py` — replace `decode_token` import |
| UPDATE | `backend/app/seed_users.py` — replace `hash_password` import |
| UPDATE | `backend/tests/conftest.py` — use shim |
| UPDATE | `backend/tests/core/test_security.py` — test shim, not deleted module |
| UPDATE | `backend/tests/integration/test_bdd_*.py` — use shim |

---

### BE-02 · Fix Deprecated `datetime.utcnow()` Everywhere

**Priority:** 🟡 Medium  
**Status:** 🔴 TODO  
**Principle violated:** Code quality / Python 3.12+ compatibility  

#### Problem
`datetime.utcnow()` is deprecated since Python 3.12 and will raise a `DeprecationWarning` in all production logs. The correct replacement is `datetime.now(timezone.utc)`.

**Affected production files (non-test):**
- `app/services/base_service.py` (×2)
- `app/services/oauth_service.py` (×3)
- `app/services/notification_service.py` (×4)
- `app/services/loan_service.py` (×3)
- `app/services/budget_service.py` (×1)
- `app/services/chat/tools.py` (×1)
- `app/services/goal_notification_service.py` (×2)
- `app/api/v1/budgets.py` (×1)
- `app/api/v1/health.py` (×8)
- `app/api/v1/goals.py` (×1)
- `app/repositories/user_repository.py` (×2)
- `app/repositories/oauth_account_repository.py` (×2)
- `app/repositories/financial_profile_repository.py` (×1)
- `app/repositories/user_profile_repository.py` (×1)
- `app/core/provider_implementations.py` (×2 in `JWTTokenProvider`)
- `app/utils/security.py` (×2 — removed in BE-01)

**Also fix test files** (not blocking but clean):
- `tests/conftest.py` (×14+)
- `tests/services/test_notification_service.py` (×8)
- `tests/services/test_goal_notification_service.py` (×1)

#### Acceptance Criteria
- [ ] `grep -rn "datetime.utcnow()" backend/app/` returns **zero** results.
- [ ] All usages replaced with `datetime.now(timezone.utc)`.
- [ ] `from datetime import timezone` added to every affected file.
- [ ] All tests pass: `pytest backend/tests/ -x`.

#### Replacement Pattern
```python
# BEFORE
from datetime import datetime
datetime.utcnow()

# AFTER
from datetime import datetime, timezone
datetime.now(timezone.utc)
```

---

### BE-03 · Create `LoanRepository` + `ILoanRepository`

**Priority:** 🔴 Critical  
**Status:** 🔴 TODO  
**Principle violated:** DIP, SRP, Repository Pattern  

#### Problem
`LoanService` directly executes `self.db.execute(select(Loan)...)` inline throughout 823 lines, mixing business logic with data access. No `LoanRepository` exists despite `ExpenseRepository`, `BudgetRepository`, `UserRepository` etc. all following the pattern.

#### Acceptance Criteria
- [ ] `backend/app/repositories/interfaces.py` has `ILoanRepository` ABC with these methods:
  - `create_loan(user_id, loan_data) -> Loan`
  - `get_loan_by_id(loan_id, user_id) -> Optional[Loan]`
  - `get_loans_by_user(user_id, status) -> List[Loan]`
  - `update_loan(loan_id, **kwargs) -> Optional[Loan]`
  - `delete_loan(loan_id, user_id) -> bool`
  - `get_loan_payments(loan_id) -> List[LoanPayment]`
  - `create_payment(loan_id, payment_data) -> LoanPayment`
- [ ] `backend/app/repositories/loan_repository.py` created implementing `ILoanRepository`.
- [ ] `LoanRepository` injected into `LoanService.__init__` (ticket BE-04).
- [ ] `LoanRepository` has its own unit test file at `tests/repositories/test_loan_repository.py`.
- [ ] All existing loan integration tests still pass.

#### Files to Create / Change
| Action | File |
|--------|------|
| UPDATE | `backend/app/repositories/interfaces.py` — add `ILoanRepository` |
| CREATE | `backend/app/repositories/loan_repository.py` |
| CREATE | `backend/tests/repositories/test_loan_repository.py` |

---

### BE-04 · Refactor `LoanService` to Use `LoanRepository`

**Priority:** 🔴 Critical  
**Status:** 🔴 TODO  
**Depends on:** BE-03  
**Principle violated:** DIP, SRP  

#### Problem
After BE-03, `LoanService` must be updated to use `LoanRepository` for all DB access instead of inline `self.db.execute(...)`.

#### Acceptance Criteria
- [ ] `LoanService.__init__` accepts `loan_repository: ILoanRepository` as a dependency.
- [ ] All `self.db.execute(select(Loan)...)` calls replaced with `self.loan_repository.*` calls.
- [ ] `LoanService` no longer imports `select`, `and_`, `desc`, `func` from SQLAlchemy.
- [ ] `LoanService` does NOT hold a direct `db: AsyncSession` reference (repository owns the session).
- [ ] Unit tests for `LoanService` use `MagicMock` for `ILoanRepository` — no real DB required.
- [ ] All integration tests pass.

#### Files to Change
| Action | File |
|--------|------|
| UPDATE | `backend/app/services/loan_service.py` |
| UPDATE | `backend/app/api/v1/loans.py` — update factory function |
| CREATE | `backend/tests/services/test_loan_service.py` |

---

### BE-05 · Split `LoanService` into Focused Sub-Services (SRP)

**Priority:** 🟠 High  
**Status:** 🔴 TODO  
**Depends on:** BE-04  
**Principle violated:** SRP  

#### Problem
`loan_service.py` (823 lines) handles CRUD, payments, EMI calculations, analytics, schedule generation, and financial profile side-effects — 6+ distinct responsibilities.

#### Target Structure
```
backend/app/services/
  loan_crud_service.py        ← CRUD: create, read, update, delete
  loan_payment_service.py     ← Payment recording + status updates
  loan_analytics_service.py   ← Analytics queries, summaries, monthly breakdowns
  loan_service.py             ← Facade: orchestrates the three above (backward-compat)
```

`loan_calculators.py` and `loan_validators.py` already exist and are fine — keep them.

#### Acceptance Criteria
- [ ] `LoanCrudService` handles create/read/update/delete loans only.
- [ ] `LoanPaymentService` handles `record_payment`, `get_payments`, `update_payment_status`.
- [ ] `LoanAnalyticsService` handles analytics, schedule, monthly summaries.
- [ ] `LoanService` facade delegates to sub-services and implements `ILoanService` for backward compatibility.
- [ ] No single new file exceeds 300 lines.
- [ ] All existing API tests pass (the router calls `LoanService` which is a facade — no router changes needed).
- [ ] Each sub-service has unit tests with mocked repository.

#### Files to Create / Change
| Action | File |
|--------|------|
| CREATE | `backend/app/services/loan_crud_service.py` |
| CREATE | `backend/app/services/loan_payment_service.py` |
| CREATE | `backend/app/services/loan_analytics_service.py` |
| REFACTOR | `backend/app/services/loan_service.py` → thin facade |
| CREATE | `backend/tests/services/test_loan_crud_service.py` |
| CREATE | `backend/tests/services/test_loan_payment_service.py` |
| CREATE | `backend/tests/services/test_loan_analytics_service.py` |

---

### BE-06 · `ExpenseService` Must Inherit `BaseService`

**Priority:** 🔴 Critical  
**Status:** 🔴 TODO  
**Principle violated:** OOP, DRY  

#### Problem
`ExpenseService(IExpenseService)` extends only the interface ABC, missing `BaseService` inheritance. This loses structured logging (`log_operation`, `log_error`, `handle_error`) that every other service uses, leading to inconsistent ad-hoc `logger.error(f"…")` calls and no audit trail.

#### Acceptance Criteria
- [ ] `ExpenseService(BaseService, IExpenseService)` declared.
- [ ] All bare `logger.error(f"…", exc_info=True)` replaced with `self.handle_error(operation, exc, details)`.
- [ ] All bare `logger.info(f"…")` replaced with `self.log_operation(operation, details)`.
- [ ] `__init__` calls `super().__init__()`.
- [ ] Existing unit tests for `ExpenseService` still pass.
- [ ] New tests verify `log_operation` and `handle_error` are called on success and error paths.

#### Files to Change
| Action | File |
|--------|------|
| UPDATE | `backend/app/services/expense_service.py` |
| UPDATE | `backend/tests/services/test_expense_service.py` (if exists) or CREATE |

---

### BE-07 · Fix Unused Generic `T` in `BaseService`

**Priority:** 🟡 Medium  
**Status:** 🔴 TODO  
**Principle violated:** Clean code, OOP clarity  

#### Problem
`BaseService(ABC, Generic[T])` declares a generic type variable `T` that no method signature uses and no subclass specifies. It creates confusion about what `T` represents.

**Two options:**
- **Option A (Recommended):** Remove `Generic[T]` — `BaseService` is a behavior mixin, not a generic container.
- **Option B:** Enforce `T` as the primary domain model type returned by services (e.g., `AuthService(BaseService[User])`). This requires updating all subclasses.

> **Decision:** Use Option A — simpler, no risk, no subclass changes needed.

#### Acceptance Criteria
- [ ] `BaseService` declaration changed from `class BaseService(ABC, Generic[T]):` to `class BaseService(ABC):`.
- [ ] `TypeVar('T')` import removed from `base_service.py`.
- [ ] `from typing import Generic` import removed (if only used for `T`).
- [ ] All subclasses (`AuthService`, `UserService`, etc.) compile without type errors.
- [ ] `mypy backend/app/services/base_service.py` returns no errors.

#### Files to Change
| Action | File |
|--------|------|
| UPDATE | `backend/app/services/base_service.py` |

---

### BE-08 · Standardize Service Factory Pattern Across All Routers

**Priority:** 🟠 High  
**Status:** 🔴 TODO  
**Principle violated:** DRY, consistency  

#### Problem
Some routers use a proper `Depends(get_X_service)` factory (e.g., `auth.py`'s `get_auth_service`); others inline-instantiate the service inside the endpoint handler (e.g., `expenses.py` line: `service = ExpenseService(db, cache_service=...)`). Inline instantiation:
- Cannot be mocked in endpoint tests
- Duplicates construction logic
- Makes testing harder

**Routers with inline service construction (must be fixed):**
- `expenses.py`
- `loans.py`
- `budgets.py`
- `goals.py`
- `notifications.py`

#### Acceptance Criteria
- [ ] Every router has a `get_X_service(...)` dependency factory function at the top of the router file.
- [ ] All endpoint handlers receive the service via `service: XService = Depends(get_x_service)`.
- [ ] No `service = XService(db, ...)` inside endpoint function bodies.
- [ ] Endpoint unit tests can mock the service by overriding the dependency.
- [ ] All integration tests still pass.

#### Files to Change
| Action | File |
|--------|------|
| UPDATE | `backend/app/api/v1/expenses.py` |
| UPDATE | `backend/app/api/v1/loans.py` |
| UPDATE | `backend/app/api/v1/budgets.py` |
| UPDATE | `backend/app/api/v1/goals.py` |
| UPDATE | `backend/app/api/v1/notifications.py` |

---

### BE-09 · Consolidate Duplicate `LoanStatusEnum` / `LoanStatus`

**Priority:** 🟡 Medium  
**Status:** 🔴 TODO  
**Principle violated:** DRY  

#### Problem
- `loan_domain.py` defines `LoanStatusEnum` (values: `"Active"`, `"Closed"`, etc.)
- `schemas/loan.py` defines `LoanStatus` (separate enum, potentially different values)

Both represent the same domain concept. Using two enums risks value drift and forces callers to convert between them.

#### Acceptance Criteria
- [ ] A single `LoanStatus` enum lives in `loan_domain.py` (the domain layer).
- [ ] `schemas/loan.py` imports and re-exports `LoanStatus` from `loan_domain.py`.
- [ ] `LoanStatusEnum` in `loan_domain.py` **renamed** to `LoanStatus`.
- [ ] `grep -rn "LoanStatusEnum" backend/` returns **zero** hits.
- [ ] Same consolidation applied to `PaymentStatusEnum` / `PaymentStatus`.
- [ ] All tests pass.

#### Files to Change
| Action | File |
|--------|------|
| UPDATE | `backend/app/services/loan_domain.py` — rename enums |
| UPDATE | `backend/app/schemas/loan.py` — import from domain |
| UPDATE | All files referencing `LoanStatusEnum` / `PaymentStatusEnum` |

---

### BE-10 · Tighten CSP Header — Remove `unsafe-inline` for Scripts

**Priority:** 🟠 High  
**Status:** 🔴 TODO  
**Principle violated:** Security best practice  

#### Problem
`SecurityHeadersMiddleware` sets:
```
script-src 'self' 'unsafe-inline'
```
`'unsafe-inline'` disables XSS protection provided by CSP for scripts, defeating the purpose of the header.

#### Acceptance Criteria
- [ ] `'unsafe-inline'` removed from `script-src` in `SecurityHeadersMiddleware`.
- [ ] A nonce-based or hash-based approach configured **OR** a `NONCE_DISABLED=true` env flag that gates the relaxed policy to development only.
- [ ] Integration test verifies `script-src` does **not** contain `unsafe-inline` in production mode.
- [ ] `style-src 'unsafe-inline'` evaluated — if Tailwind injects inline styles at runtime, document the exception.

#### Files to Change
| Action | File |
|--------|------|
| UPDATE | `backend/app/core/middleware.py` — `SecurityHeadersMiddleware` |
| CREATE | `backend/tests/core/test_security_headers.py` |

---

### BE-11 · Remove Legacy `_redis_cache` Global in `dependencies.py`

**Priority:** 🟡 Medium  
**Status:** 🔴 TODO  
**Principle violated:** Clean architecture, DRY  

#### Problem
`dependencies.py` has a module-level global `_redis_cache: Optional[RedisCache] = None` with `get_redis_cache()` / `set_redis_cache()` functions — a legacy backward-compat shim. The canonical location is `app.state.cache_service` (set during lifespan startup). The global leaks state between tests and makes the dependency lifecycle unclear.

#### Acceptance Criteria
- [ ] `_redis_cache` global removed from `dependencies.py`.
- [ ] `get_redis_cache()` reads from `request.app.state` instead of the global.
- [ ] `set_redis_cache()` removed (no longer needed — lifespan sets `app.state` directly).
- [ ] All callers of `set_redis_cache()` (only `main.py` lifespan) updated.
- [ ] Tests that relied on the global replaced with proper `app.state` overrides.
- [ ] `grep -n "_redis_cache" backend/` returns **zero** hits.

#### Files to Change
| Action | File |
|--------|------|
| UPDATE | `backend/app/dependencies.py` |
| UPDATE | `backend/app/main.py` (lifespan — remove `set_redis_cache` call) |
| UPDATE | Any test files setting `_redis_cache` |

---

## Phase 2 — Frontend Critical Fixes

---

### FE-01 · Migrate `BudgetsPage.jsx` → `BudgetsPage.tsx`

**Priority:** 🔴 Critical  
**Status:** 🔴 TODO  

#### Problem
`BudgetsPage.tsx` is a 15-line stub placeholder that `App.tsx` imports. The real implementation is in `BudgetsPage.jsx` (479 lines). Users see an empty placeholder page.

#### Acceptance Criteria
- [ ] All JSX/logic from `BudgetsPage.jsx` migrated into `BudgetsPage.tsx` with full TypeScript types.
- [ ] No `any` casts — all props and state variables explicitly typed.
- [ ] `BudgetsPage.jsx` **deleted**.
- [ ] `App.tsx` import unchanged (still `./pages/BudgetsPage` → resolves to `.tsx`).
- [ ] Page renders correctly in browser at `/budgets`.
- [ ] `tsc --noEmit` returns no errors for the file.

#### Files to Change
| Action | File |
|--------|------|
| REWRITE | `frontend/src/pages/BudgetsPage.tsx` |
| DELETE | `frontend/src/pages/BudgetsPage.jsx` |

---

### FE-02 · Migrate `GoalsPage.jsx` → `GoalsPage.tsx`

**Priority:** 🔴 Critical  
**Status:** 🔴 TODO  

#### Problem
`GoalsPage.tsx` either does not exist as a proper page or is a stub. The real implementation is `GoalsPage.jsx` (485 lines).

#### Acceptance Criteria
- [ ] All JSX/logic from `GoalsPage.jsx` migrated to `GoalsPage.tsx` with full TypeScript types.
- [ ] `GoalAllocationStrategy` component typed.
- [ ] `GoalsPage.jsx` **deleted**.
- [ ] Page renders at `/goals`.
- [ ] `tsc --noEmit` clean.

#### Files to Change
| Action | File |
|--------|------|
| REWRITE | `frontend/src/pages/GoalsPage.tsx` |
| DELETE | `frontend/src/pages/GoalsPage.jsx` |

---

### FE-03 · Migrate `LoansPage.jsx` → Full `LoansPage.tsx`

**Priority:** 🔴 Critical  
**Status:** 🔴 TODO  

#### Problem
`LoansPage.tsx` is a 15-line stub. `LoansPage.jsx` contains the full implementation.

#### Acceptance Criteria
- [ ] Full implementation migrated to `LoansPage.tsx`.
- [ ] `LoansPage.jsx` **deleted**.
- [ ] Page renders at `/loans`.
- [ ] `tsc --noEmit` clean.

---

### FE-04 · Migrate `SettingsPage.jsx` → `SettingsPage.tsx`

**Priority:** 🔴 Critical  
**Status:** 🔴 TODO  

#### Acceptance Criteria
- [ ] Full implementation migrated to `SettingsPage.tsx`.
- [ ] `SettingsPage.jsx` **deleted**.
- [ ] Page renders at `/settings`.
- [ ] `tsc --noEmit` clean.

---

### FE-05 · Migrate `ReportsPage.jsx` → `ReportsPage.tsx`

**Priority:** 🔴 Critical  
**Status:** 🔴 TODO  

#### Acceptance Criteria
- [ ] Full implementation migrated to `ReportsPage.tsx`.
- [ ] `ReportsPage.jsx` **deleted**.
- [ ] Page renders at `/reports`.
- [ ] `tsc --noEmit` clean.

---

### FE-06 · Merge `AdminPage.jsx` into `AdminPage.tsx`

**Priority:** 🔴 Critical  
**Status:** 🔴 TODO  

#### Problem
Both `AdminPage.jsx` (445 lines) and `AdminPage.tsx` (501 lines) exist with partially overlapping implementations. Need to reconcile them into a single canonical TypeScript file using the more complete version as the base.

#### Acceptance Criteria
- [ ] Single `AdminPage.tsx` contains the full, deduplicated implementation.
- [ ] `AdminPage.jsx` **deleted**.
- [ ] Page renders at `/admin` (admin users only).
- [ ] `tsc --noEmit` clean.

---

### FE-07 · Fix `api.ts` 401 Handler — Replace `window.location.href`

**Priority:** 🔴 Critical  
**Status:** 🔴 TODO  
**Principle violated:** SRP, clean architecture  

#### Problem
In `api.ts` response interceptor, failed refresh leads to:
```typescript
window.location.href = '/login'
```
This causes a full page reload, destroying React state and bypassing React Router. The correct approach is to call a logout callback that triggers the auth store.

#### Acceptance Criteria
- [ ] `window.location.href = '/login'` removed from `api.ts`.
- [ ] `api.ts` exposes a `setLogoutCallback(fn: () => void)` function.
- [ ] `useInitAuth` hook (or `authStore`) calls `setLogoutCallback(() => logout())` on mount.
- [ ] On 401 refresh failure, the callback is invoked instead of hard redirect.
- [ ] React Router then redirects to `/login` via the auth store's `isAuthenticated` state change.
- [ ] Manual test: expire tokens → verify redirect happens without full page reload.

#### Files to Change
| Action | File |
|--------|------|
| UPDATE | `frontend/src/services/api.ts` |
| UPDATE | `frontend/src/hooks/useAuth.ts` |

---

### FE-08 · Remove Duplicate Axios Refresh Call in `authStore.ts`

**Priority:** 🟠 High  
**Status:** 🔴 TODO  
**Principle violated:** DRY  

#### Problem
`authStore.ts` `initAuth()` directly calls `axios.post(…/auth/refresh, …)` — the same logic already handled by `api.ts`'s response interceptor. This creates two competing token-refresh paths that can race.

#### Acceptance Criteria
- [ ] Direct `axios` import removed from `authStore.ts`.
- [ ] `initAuth()` calls `authService.refreshToken()` for silent refresh (which goes through the interceptor).
- [ ] No race condition: a single refresh in-flight at a time.
- [ ] All existing auth flow tests pass.

#### Files to Change
| Action | File |
|--------|------|
| UPDATE | `frontend/src/store/authStore.ts` |

---

### FE-09 · Split `store/index.ts` into Domain Store Files

**Priority:** 🟠 High  
**Status:** 🔴 TODO  
**Principle violated:** SRP  

#### Problem
`store/index.ts` (538 lines) contains 6 Zustand stores. Each store is a separate concern and should be its own file for maintainability and testability.

#### Target Structure
```
frontend/src/store/
  index.ts              ← Re-exports all stores (barrel)
  profileStore.ts       ← useProfileStore
  expenseStore.ts       ← useExpenseStore
  budgetStore.ts        ← useBudgetStore
  goalStore.ts          ← useGoalStore
  loanStore.ts          ← useLoanStore
  notificationStore.ts  ← useNotificationStore
  themeStore.ts         ← already separate ✅
  authStore.ts          ← already separate ✅
```

#### Acceptance Criteria
- [ ] Each store in its own file.
- [ ] `store/index.ts` only re-exports all stores (barrel file, <20 lines).
- [ ] All existing imports (`from '@/store/index'`) continue working unchanged.
- [ ] No circular imports introduced.
- [ ] All page components still compile and run correctly.

---

### FE-10 · Split `Layout.tsx` into Sub-Components

**Priority:** 🟠 High  
**Status:** 🔴 TODO  
**Principle violated:** SRP  

#### Problem
`Layout.tsx` (668 lines) contains `Sidebar`, `Header`, `Layout`, and `PageContainer` — four distinct components with independent responsibilities.

#### Target Structure
```
frontend/src/components/layout/
  Sidebar.tsx
  Header.tsx
  Layout.tsx          ← shell component only
  PageContainer.tsx
  index.ts            ← re-exports all
```

#### Acceptance Criteria
- [ ] Each component in its own file under `components/layout/`.
- [ ] `components/Layout.tsx` (top-level) becomes a barrel re-exporting from `components/layout/index.ts`.
- [ ] All existing imports `from '../components/Layout'` work unchanged.
- [ ] No prop interface changes — all components keep same API.
- [ ] `tsc --noEmit` clean after refactor.

---

### FE-11 · Fix `tokenManager.ts` Dual API

**Priority:** 🟡 Medium  
**Status:** 🔴 TODO  
**Principle violated:** DRY, clean API  

#### Problem
`tokenManager.ts` exports both:
- Named exports: `storeToken`, `clearTokens`, `getAccessToken`, etc.
- A default export `tokenManager` object wrapping the same functions.

Two parallel APIs for the same thing lead to inconsistent usage across the codebase.

#### Acceptance Criteria
- [ ] Audit all imports of `tokenManager` — choose **one** pattern (default export object recommended for semantic grouping).
- [ ] Named exports removed **or** default object export removed — not both.
- [ ] All callers updated to use the single chosen API.
- [ ] `tsc --noEmit` clean.

---

### FE-12 · Migrate `OverviewTab` to TypeScript with Typed Props

**Priority:** 🟡 Medium  
**Status:** 🔴 TODO  

#### Problem
`DashboardPage.tsx` casts `OverviewTab` as:
```typescript
const OverviewTabBridge = OverviewTab as React.ComponentType<Record<string, unknown>>
```
This suppresses type-checking for a component that receives critical typed data.

#### Acceptance Criteria
- [ ] `OverviewTab` (and its dependencies) migrated from `.jsx` to `.tsx`.
- [ ] Props interface defined: `expenses`, `budgets`, `goals`, `loans` — typed.
- [ ] `OverviewTabBridge` cast removed from `DashboardPage.tsx`.
- [ ] `tsc --noEmit` clean.

---

### FE-13 · Add Frontend Unit Tests for Stores + Critical Pages

**Priority:** 🟡 Medium  
**Status:** 🔴 TODO  

#### Problem
No unit tests exist for store actions or page components. Key business logic in stores is untested.

#### Acceptance Criteria
- [ ] `authStore` tests: `login`, `logout`, `initAuth` (valid token, expired token, refresh failure).
- [ ] `expenseStore` tests: `fetchExpenses`, `addExpense`, `deleteExpense`.
- [ ] `budgetStore` tests: `fetchBudgets`, `addBudget`.
- [ ] `LoginPage` render test: form renders, validation errors shown, submit calls `login`.
- [ ] `DashboardPage` render test: loading state, data displayed after fetch.
- [ ] All tests run with `npm test` in `frontend/`.
- [ ] Coverage report generated.

#### Files to Create
| Action | File |
|--------|------|
| CREATE | `frontend/src/__tests__/store/authStore.test.ts` |
| CREATE | `frontend/src/__tests__/store/expenseStore.test.ts` |
| CREATE | `frontend/src/__tests__/store/budgetStore.test.ts` |
| CREATE | `frontend/src/__tests__/pages/LoginPage.test.tsx` |
| CREATE | `frontend/src/__tests__/pages/DashboardPage.test.tsx` |

---

## Phase 3 — Final Verification Checklist

Run this checklist after all tickets are complete before tagging a production release.

### Backend
- [ ] `pytest backend/tests/ -x --tb=short` → all green
- [ ] `grep -rn "datetime.utcnow()" backend/app/` → zero results
- [ ] `grep -rn "from app.core.security import" backend/app/` → zero results
- [ ] `grep -rn "from app.utils.security import" backend/` → zero results
- [ ] `grep -rn "LoanStatusEnum" backend/` → zero results
- [ ] `grep -rn "_redis_cache" backend/app/` → zero results
- [ ] `grep -rn "self\.db\.execute" backend/app/services/loan` → zero results
- [ ] No service file over 400 lines
- [ ] Coverage ≥ 80%: `pytest --cov=app --cov-report=term-missing`

### Frontend
- [ ] `npx tsc --noEmit` → zero errors
- [ ] `ls frontend/src/pages/*.jsx` → no `.jsx` files remain
- [ ] `grep -rn "window.location.href" frontend/src/` → zero results
- [ ] `grep -rn "from 'axios'" frontend/src/store/` → zero results
- [ ] `npm test` → all tests pass
- [ ] `npm run build` → build succeeds with no warnings

### Both
- [ ] Docker build: `docker-compose build` → succeeds
- [ ] Docker smoke test: `docker-compose up -d` → all health checks green
- [ ] Manual test: login → dashboard → expenses → budgets → goals → loans → logout

---

## Appendix — Ticket Work Order

Recommended implementation order to minimize merge conflicts:

```
BE-07 → BE-02 → BE-01 → BE-09 → BE-11
       ↓
      BE-06 → BE-03 → BE-04 → BE-05 → BE-08 → BE-10
       ↓
      FE-07 → FE-08 → FE-09 → FE-10 → FE-11
       ↓
      FE-01 → FE-02 → FE-03 → FE-04 → FE-05 → FE-06
       ↓
      FE-12 → FE-13
```

**Start with:** BE-07 (zero-risk, one file, clears confusing type noise)  
**Highest-impact next:** BE-01 (eliminates dangerous duplicate bcrypt paths)  
**Biggest risk ticket:** BE-05 (LoanService split — needs integration test coverage before and after)
