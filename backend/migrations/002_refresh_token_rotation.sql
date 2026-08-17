-- Migration 002: refresh token rotation columns
-- Adds token rotation chain, device tracking, and revocation support.
-- Apply against: AUTH database

ALTER TABLE refresh_tokens
    ADD COLUMN IF NOT EXISTS is_revoked        BOOLEAN      NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS revoked_at        TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS replaced_by       UUID         REFERENCES refresh_tokens(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS device_info       TEXT,
    ADD COLUMN IF NOT EXISTS last_used_at      TIMESTAMPTZ;

-- Index for fast valid-token lookups (the hot path on every API request)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_refresh_tokens_user_valid
    ON refresh_tokens (user_id, is_revoked)
    WHERE is_revoked = FALSE;

-- Index to find and purge expired tokens efficiently
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_refresh_tokens_expires
    ON refresh_tokens (expires_at)
    WHERE is_revoked = FALSE;
