-- Migration 003: soft-delete infrastructure
-- Adds deleted_at columns (if not present), audit table, PG trigger function,
-- and partial indexes that exclude soft-deleted rows from all normal queries.

-- ── Soft-delete columns ────────────────────────────────────────────────────

ALTER TABLE expenses      ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE budgets       ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE goals         ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE loans         ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- ── Partial indexes excluding soft-deleted rows ────────────────────────────

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_expenses_not_deleted
    ON expenses (user_id, date DESC) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_budgets_not_deleted
    ON budgets (user_id, year DESC, month DESC) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_goals_not_deleted
    ON goals (user_id, status) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_loans_not_deleted
    ON loans (user_id, status) WHERE deleted_at IS NULL;

-- ── Audit table ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS soft_delete_audit (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name    TEXT         NOT NULL,
    record_id     UUID         NOT NULL,
    deleted_by    UUID,                          -- user who triggered deletion
    deleted_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    hard_delete_after TIMESTAMPTZ               -- set for scheduled purge
);

CREATE INDEX IF NOT EXISTS idx_soft_delete_audit_table_record
    ON soft_delete_audit (table_name, record_id);

CREATE INDEX IF NOT EXISTS idx_soft_delete_audit_hard_delete
    ON soft_delete_audit (hard_delete_after)
    WHERE hard_delete_after IS NOT NULL;

-- ── Helper function ────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION soft_delete_record(
    p_table        TEXT,
    p_record_id    UUID,
    p_deleted_by   UUID DEFAULT NULL,
    p_retain_days  INT  DEFAULT 90        -- days before hard-delete is allowed
) RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE format(
        'UPDATE %I SET deleted_at = now() WHERE id = $1 AND deleted_at IS NULL',
        p_table
    ) USING p_record_id;

    INSERT INTO soft_delete_audit (table_name, record_id, deleted_by, hard_delete_after)
    VALUES (p_table, p_record_id, p_deleted_by, now() + (p_retain_days || ' days')::INTERVAL);
END;
$$;
