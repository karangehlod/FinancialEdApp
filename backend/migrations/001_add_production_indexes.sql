-- Migration 001: production performance indexes
-- Apply with: psql $DATA_DATABASE_URL -f 001_add_production_indexes.sql
-- Safe to re-run: CREATE INDEX IF NOT EXISTS / CONCURRENTLY skips existing indexes.

-- Enable pg_trgm for GIN text search on merchant/description fields
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Expenses: most-common query patterns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_expenses_user_date
    ON expenses (user_id, date DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_expenses_user_category
    ON expenses (user_id, category);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_expenses_user_date_category
    ON expenses (user_id, date DESC, category);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_expenses_description_trgm
    ON expenses USING GIN (description gin_trgm_ops);

-- Budgets: filter by user + period
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_budgets_user_period
    ON budgets (user_id, year DESC, month DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_budgets_user_category_period
    ON budgets (user_id, category, year DESC, month DESC);

-- Goals: active goals lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_goals_user_status
    ON goals (user_id, status)
    WHERE status = 'active';

-- Loans: active loans for EMI/reminder queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_loans_user_status
    ON loans (user_id, status)
    WHERE status = 'active';

-- Notifications: unread lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_user_unread
    ON notifications (user_id, created_at DESC)
    WHERE is_read = FALSE;

-- Auth DB: refresh token lookups (apply against auth database)
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_refresh_tokens_user_valid
--     ON refresh_tokens (user_id, is_revoked)
--     WHERE is_revoked = FALSE;
