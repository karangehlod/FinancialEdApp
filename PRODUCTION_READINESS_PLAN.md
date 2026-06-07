# 🚀 FinancialEdApp — Production Readiness Plan
> **Goal:** Achieve 10/10 across all categories for 1M+ user scale  
> **Audit Date:** February 28, 2026  
> **Target Completion:** Progressive sprints

---

## 📊 Current Score vs Target

| Category | Current | Target | Priority |
|---|---|---|---|
| Architecture / Design | 7/10 | 10/10 | P1 |
| Rate Limiting | 2/10 | 10/10 | **P0** |
| Caching | 2/10 | 10/10 | **P0** |
| Database Query Optimization | 4/10 | 10/10 | **P0** |
| Security | 5/10 | 10/10 | **P0** |
| Observability | 4/10 | 10/10 | P1 |
| Feature Completeness | 5/10 | 10/10 | P1/P2 |
| Test Coverage | 5/10 | 10/10 | P1 |
| **1M User Readiness** | **3/10** | **10/10** | All |

---

## 🔴 P0 — CRITICAL BLOCKERS (Fix Immediately)

### P0-1: Database Connection Pool — Default pool_size=5 will crash at scale
**File:** `backend/app/db/session.py`  
**Problem:** No pool configuration. Default `pool_size=5, max_overflow=10` means only 15 concurrent DB connections total across all workers.  
**Fix:**
```python
auth_engine = create_async_engine(
    settings.AUTH_DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)
```
**Status:** ⬜ TODO → ✅ Done

---

### P0-2: Rate Limiting — Defined But Never Applied
**Files:** `backend/app/core/rate_limiting.py`, `backend/app/main.py`  
**Problem:**
- `RedisRateLimiter` (sliding window, correct) is defined but never wired into any middleware
- `RateLimitMiddleware` uses a racy non-atomic counter and is not registered in `main.py`
- `RateLimitConfig` per-route rules are never applied
- Auth endpoints (`/login`, `/register`) have no actual rate limiting in production
- `_get_identifier()` reads `user-id` header — trivially spoofable

**Fix:**
- Wire `RedisRateLimiter` into a proper `RateLimitMiddleware` using Lua scripts for atomic increments
- Register middleware in `main.py` with route-level config
- Use JWT `sub` claim for authenticated routes, IP+fingerprint for unauthenticated
- Add `Retry-After` and `X-RateLimit-*` headers on all responses
- Add account lockout after N failed login attempts (tracked in Redis)

**Status:** ⬜ TODO → ✅ Done

---

### P0-3: Redis Caching — Infrastructure Exists, Zero Data Cached
**Files:** `backend/app/core/provider_implementations.py`, all services  
**Problem:**
- `RedisCache` class is initialized but never used for business data
- Every `GET /expenses`, `GET /budgets`, `GET /goals` hits the database cold
- `get_current_user` creates new `BcryptPasswordHasher` + `JWTTokenProvider` + `AuthService` on **every request**
- `RedisCache.get()` returns raw string with no JSON deserialization
- No cache invalidation on create/update/delete
- No cache key namespacing strategy

**Fix:**
- Add `@cached` decorator pattern for service methods
- Cache user profile, budget summaries, goals list, expense aggregates (TTL: 5 min)
- Cache token→user resolution (TTL: match access token expiry)
- Add JSON serialization/deserialization to `RedisCache`
- Add cache invalidation hooks in `ExpenseService`, `BudgetService`, `GoalService`
- Make provider instances app-level singletons via FastAPI lifespan

**Status:** ⬜ TODO → ✅ Done

---

### P0-4: Missing Database Indexes
**File:** `database_setup.sql`, new migration  
**Problem:**
- `database_setup.sql` uses MySQL-style `INDEX` inside `CREATE TABLE` — silently ignored by PostgreSQL
- No compound indexes on hot query paths
- `merchant ILIKE '%...%'` does full scans — needs pg_trgm GIN index
- `notifications` table has no index on `(user_id, is_read, created_at)`

**Fix (PostgreSQL syntax):**
```sql
-- Expenses (most queried)
CREATE INDEX CONCURRENTLY idx_expenses_user_date ON expenses(user_id, date DESC);
CREATE INDEX CONCURRENTLY idx_expenses_user_category ON expenses(user_id, category);
CREATE INDEX CONCURRENTLY idx_expenses_user_date_cat ON expenses(user_id, date DESC, category);
CREATE INDEX CONCURRENTLY idx_expenses_merchant_trgm ON expenses USING GIN(merchant gin_trgm_ops);

-- Budgets
CREATE INDEX CONCURRENTLY idx_budgets_user_month ON budgets(user_id, month DESC);
CREATE INDEX CONCURRENTLY idx_budgets_user_month_cat ON budgets(user_id, month, category);

-- Goals
CREATE INDEX CONCURRENTLY idx_goals_user_status ON goals(user_id, status);
CREATE INDEX CONCURRENTLY idx_goals_user_type ON goals(user_id, goal_type);

-- Loans
CREATE INDEX CONCURRENTLY idx_loans_user_status ON loans(user_id, status);
CREATE INDEX CONCURRENTLY idx_loans_user_due ON loans(user_id, next_due_date);

-- Notifications
CREATE INDEX CONCURRENTLY idx_notifications_user_read ON notifications(user_id, is_read, created_at DESC);

-- Loan payments
CREATE INDEX CONCURRENTLY idx_loan_payments_loan ON loan_payments(loan_id, payment_date DESC);
```

**Status:** ⬜ TODO → ✅ Done

---

### P0-5: Fix Alembic Configuration
**File:** `backend/alembic/env.py`  
**Problem:** `settings.get_database_url()` — method doesn't exist on `Settings`. Alembic migrations fail silently.  
**Fix:** Use `settings.DATA_DATABASE_URL` directly.

**Status:** ⬜ TODO → ✅ Done

---

### P0-6: Security — Remove console.log Token Logging
**File:** `frontend/src/services/api.js`  
**Problem:** Lines 18-24 log the Bearer token preview on every request. In production, this leaks auth tokens to browser console and any browser extension.  
**Fix:** Remove all `console.log` from interceptors, use structured frontend logger that respects `NODE_ENV`.

**Status:** ⬜ TODO → ✅ Done

---

### P0-7: Provider Singletons — New instances on every request
**File:** `backend/app/dependencies.py`, `backend/app/api/v1/auth.py`  
**Problem:** `get_current_user` creates `BcryptPasswordHasher(rounds=12)` + `JWTTokenProvider` + `AuthService` on every single request. Bcrypt with rounds=12 is intentionally slow — instantiating it per-request wastes CPU.  
**Fix:** Register providers as FastAPI app-level dependencies using `lifespan` context or module-level singletons wired at startup.

**Status:** ⬜ TODO → ✅ Done

---

### P0-8: Refresh Token Validation — Table Exists, Never Used
**Files:** `backend/app/db/models/auth.py`, `backend/app/services/auth_service.py`  
**Problem:** `RefreshToken` table is defined but tokens are never stored in it on login, and never verified against it on refresh. Any crafted refresh token with a valid signature will work.  
**Fix:**
- Store token hash in `refresh_tokens` table on login
- Validate existence + expiry on `/auth/refresh`
- Delete from table on logout
- Add `rotated_at` and `revoked` columns for rotation strategy

**Status:** ⬜ TODO → ✅ Done

---

## 🟠 P1 — HIGH PRIORITY (This Sprint)

### P1-1: Response Caching Strategy
- Cache GET endpoints with user-scoped keys: `cache:user:{user_id}:expenses:page:{n}`
- TTL hierarchy: user profile (30 min), budget summary (5 min), expense list (2 min), analytics (10 min)
- Invalidate on any mutating operation in the same domain
- Add `ETag`/`Last-Modified` headers for conditional requests

**Status:** ⬜ TODO

---

### P1-2: Email Verification + Password Reset
- `POST /auth/verify-email?token=...` endpoint
- `POST /auth/forgot-password` → send reset email
- `POST /auth/reset-password` → validate token, update hash
- Rate limit: 3 attempts per hour per email
- Token: signed JWT with 1-hour expiry, stored hash in Redis

**Status:** ⬜ TODO

---

### P1-3: Account Lockout After Failed Logins
- Track failed attempts per email in Redis with sliding window
- Lock after 5 failures in 15 minutes
- Auto-unlock after 30 minutes or via email reset
- Alert on repeated lockouts (possible credential stuffing)

**Status:** ⬜ TODO

---

### P1-4: OpenTelemetry Initialization
- Initialize `TracerProvider` with OTLP/Jaeger exporter in `main.py` lifespan
- Instrument FastAPI, SQLAlchemy, Redis automatically
- Add `trace_id` to all log records via logging handler
- Record `DB_QUERY_DURATION` histogram via SQLAlchemy event listeners

**Status:** ⬜ TODO

---

### P1-5: Protect `/metrics` Endpoint
- Add IP allowlist middleware or HTTP Basic auth on `/metrics`
- Or move to internal port (9090) separate from API port (8000)
- Add Grafana dashboard JSON definition
- Add Prometheus AlertManager rules for: p99 > 2s, error rate > 1%, cache hit rate < 80%

**Status:** ⬜ TODO

---

### P1-6: Background Task Queue (ARQ/Celery)
- Notifications: process asynchronously after expense/budget events
- Recurring expense generation: daily cron job
- Loan reminder emails: cron job
- Goal milestone detection: triggered on goal update
- Use ARQ (Redis-backed) for simplicity, or Celery with Redis broker

**Status:** ⬜ TODO

---

### P1-7: Soft Delete Across All Tables
- Add `deleted_at TIMESTAMP NULL` to: expenses, budgets, goals, loans, notifications
- All repository queries filter `WHERE deleted_at IS NULL`
- Hard delete only via admin API after 90-day retention
- Enables audit trail and GDPR "right to erasure" (set deleted_at, anonymize PII)

**Status:** ⬜ TODO

---

### P1-8: Atomic Budget Update (Fix Partial Commit Bug)
- `ExpenseService.create_expense` commits the expense, then updates budget
- If budget update fails, expense is committed but budget is stale
- Fix: wrap both operations in a single transaction with savepoints
- Or use domain events + eventual consistency with background task

**Status:** ⬜ TODO

---

### P1-9: Input Sanitization Beyond Pydantic
- Add `bleach` for text fields (description, merchant, notes)
- Validate `merchant` against max length + character whitelist
- Add SQL injection double-check (SQLAlchemy parameterizes, but validate anyway)
- Add content-type validation on upload endpoints

**Status:** ⬜ TODO

---

### P1-10: Test Coverage to 90%+
- Add unit tests for all services (currently missing user_service, notification_service)
- Add integration tests for all API endpoints
- Add load tests via Locust (target: 1000 RPS sustained, p99 < 500ms)
- Add E2E tests with Playwright for critical flows (register → expense → budget alert)
- Add coverage gate in CI (fail if < 85%)

**Status:** ⬜ TODO

---

## 🟡 P2 — MEDIUM PRIORITY (Next Sprint)

### P2-1: Kubernetes HPA + Resource Limits
```yaml
# Add HorizontalPodAutoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: 3
  maxReplicas: 50
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

**Status:** ⬜ TODO

---

### P2-2: CI/CD Pipeline
- GitHub Actions: lint → test → build → push image → deploy
- Separate workflows: PR checks, staging deploy, production deploy
- Secret scanning (trufflehog)
- SAST scanning (bandit for Python, semgrep)
- Coverage gate: fail if < 85%
- Auto-rollback on health check failure

**Status:** ⬜ TODO

---

### P2-3: Two-Factor Authentication (TOTP)
- `POST /auth/2fa/enable` → generate TOTP secret, return QR code
- `POST /auth/2fa/verify` → validate TOTP code
- `POST /auth/2fa/disable` → require password confirmation
- Store encrypted TOTP secret in `users` table
- Require TOTP on login if enabled (add `requires_2fa` to token response)

**Status:** ⬜ TODO

---

### P2-4: Real-time Notifications (WebSocket)
- `WS /ws/notifications/{user_id}` — authenticated WebSocket connection
- Broadcast budget alerts, loan reminders, goal milestones in real-time
- Redis Pub/Sub as the message bus between workers
- Fallback to polling for clients that don't support WebSocket

**Status:** ⬜ TODO

---

### P2-5: GDPR Compliance
- `GET /auth/data-export` — full user data dump (JSON/ZIP)
- `DELETE /auth/account` — anonymize PII, set `deleted_at`
- Cookie consent banner integration
- Data retention policy: auto-delete inactive accounts after 2 years
- Privacy policy endpoint: `GET /legal/privacy`

**Status:** ⬜ TODO

---

### P2-6: OAuth / Social Login
- Google OAuth 2.0 (`/auth/oauth/google/authorize` + `/auth/oauth/google/callback`)
- Apple Sign-in (`/auth/oauth/apple/authorize` + `/auth/oauth/apple/callback`)
- Link/unlink social accounts to existing accounts (`/auth/oauth/providers`, `DELETE /auth/oauth/{provider}`)
- `authlib` + `PyJWT` for ID token verification (RS256 via provider JWKs)
- Fernet-encrypted provider token storage
- OAuth state CSRF protection via Redis
- `OAuthAccount` DB model + migration `005_oauth_social_login.sql`
- `OAuthAccountRepository`, `OAuthService`, `/api/v1/oauth.py` router
- Frontend: `useOAuth.js` hook, `OAuthButtons.jsx` component, `OAuthCallbackPage.jsx`
- Auto-links to existing local account by email; safety guard blocks unlinking last sign-in method

**Status:** ⬜ TODO → ✅ Done

---

### P2-7: Multi-Currency Real-Time Conversion
- Integrate Open Exchange Rates API (or Fixer.io)
- Cache rates in Redis with 1-hour TTL
- Background job to refresh rates every hour
- Store all amounts in base currency, display in user's preferred currency

**Status:** ⬜ TODO

---

### P2-8: Admin Dashboard API
- `GET /admin/users` — paginated user list (requires `ADMIN_READ` permission)
- `GET /admin/metrics/summary` — aggregate statistics
- `POST /admin/users/{id}/suspend` — suspend user account
- `GET /admin/audit-log` — system audit trail
- Rate limited separately from user API

**Status:** ⬜ TODO

---

### P2-9: Read Replica Routing
- Add `READ_REPLICA_DATABASE_URL` to settings
- Route `SELECT` queries (analytics, reports) to replica
- Route `INSERT/UPDATE/DELETE` to primary
- Implement via `get_read_db()` dependency for analytics endpoints

**Status:** ⬜ TODO

---

### P2-10: CDN + Frontend Performance
- Serve static assets via CloudFront / Cloudflare
- Enable gzip/brotli compression
- Add React Query / SWR for request deduplication and caching
- Add list virtualization (react-virtual) for large datasets
- Remove unused dependencies (two charting libraries: chart.js + recharts)
- Add bundle size analysis (vite-bundle-analyzer)

**Status:** ⬜ TODO

---

## 📋 Fix Tracking

### P0 Fixes (This Session)
| ID | Description | File(s) | Status |
|---|---|---|---|
| P0-1 | DB Connection Pool | `db/session.py` | ⬜ |
| P0-2 | Wire Rate Limiting | `main.py`, `rate_limiting.py`, `middleware.py` | ⬜ |
| P0-3 | Cache Serialization + Data Caching | `provider_implementations.py`, services | ⬜ |
| P0-4 | Database Indexes | new migration file | ⬜ |
| P0-5 | Fix Alembic | `alembic/env.py` | ⬜ |
| P0-6 | Remove console.log | `frontend/src/services/api.js` | ⬜ |
| P0-7 | Provider Singletons | `dependencies.py`, `main.py` | ⬜ |
| P0-8 | Refresh Token DB Validation | `auth_service.py`, `auth.py` | ⬜ |

---

## 🏗️ Architecture Decisions

### Caching Strategy
```
L1: In-process (none, stateless API)
L2: Redis (primary cache)
  - Key format: cache:{domain}:{user_id}:{resource}:{params_hash}
  - TTL by domain:
    - user_profile: 1800s
    - budget_summary: 300s  
    - expense_list: 120s
    - analytics: 600s
    - token_user: ACCESS_TOKEN_EXPIRE_MINUTES * 60
  - Invalidation: key-based on mutation
```

### Rate Limiting Strategy
```
Algorithm: Sliding Window (Redis sorted sets) — atomic Lua script
Keys:
  - Authenticated: rate_limit:user:{user_id}:{endpoint_group}
  - Unauthenticated: rate_limit:ip:{ip}:{endpoint_group}
  
Limits:
  - /auth/login: 5/min per IP (lockout after 5 failures)
  - /auth/register: 3/min per IP
  - /auth/forgot-password: 3/hour per email
  - /api/v1/* (authenticated): 300/min per user
  - /api/v1/exports: 10/min per user
  - Default: 60/min per IP (unauthenticated)
```

### Database Connection Pool (per worker process)
```
Pool size: 20 connections
Max overflow: 40 connections  
Timeout: 30 seconds
Recycle: 1800 seconds (30 min)
Pre-ping: True
→ Max connections per worker: 60
→ With 4 workers: 240 connections per pod
→ PostgreSQL max_connections: 500 → supports ~2 pods
→ Recommendation: Use PgBouncer as connection pooler
```

---

## 📁 File Change Index

```
backend/
  app/
    db/
      session.py                     ← P0-1: Pool config
    core/
      rate_limiting.py               ← P0-2: Atomic sliding window
      middleware.py                  ← P0-2: Fix RateLimitMiddleware
      provider_implementations.py    ← P0-3: Cache serialization
      cache_service.py               ← P0-3: NEW — Cache decorator pattern
    services/
      auth_service.py                ← P0-8: Refresh token DB
      expense_service.py             ← P0-3: Cache invalidation
      budget_service.py              ← P0-3: Cache invalidation
      goal_service.py                ← P0-3: Cache invalidation
    repositories/
      user_repository.py             ← P0-8: Refresh token repo
    dependencies.py                  ← P0-7: Singleton providers
    main.py                          ← P0-2, P0-7: Wire middleware + lifespan
  alembic/
    env.py                           ← P0-5: Fix URL method
  migrations/
    001_add_production_indexes.sql   ← P0-4: NEW — All indexes
    002_add_soft_delete.sql          ← P1-7: NEW — soft delete columns

frontend/
  src/
    services/
      api.js                         ← P0-6: Remove console.log
    utils/
      logger.js                      ← P0-6: NEW — Env-aware logger
```

---

*Last updated: February 28, 2026*  
*Next review: After P0 completion*
