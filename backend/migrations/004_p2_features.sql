-- Migration 004: P2 feature columns
-- WebSocket sessions, 2FA, GDPR consent, multi-currency, financial profile.

-- ── TOTP 2FA ──────────────────────────────────────────────────────────────

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS totp_secret_enc  TEXT,          -- Fernet-encrypted TOTP secret
    ADD COLUMN IF NOT EXISTS two_factor_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS totp_backup_codes  TEXT[];      -- JSON array of hashed backup codes

-- ── GDPR consent ──────────────────────────────────────────────────────────

ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS consent_given      BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS consent_timestamp  TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS data_export_requested_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS deletion_requested_at    TIMESTAMPTZ;

-- ── Multi-currency support ─────────────────────────────────────────────────

ALTER TABLE financial_profiles
    ADD COLUMN IF NOT EXISTS currency  VARCHAR(3) NOT NULL DEFAULT 'USD';

ALTER TABLE expenses
    ADD COLUMN IF NOT EXISTS currency       VARCHAR(3),
    ADD COLUMN IF NOT EXISTS amount_usd     NUMERIC(14, 4);  -- normalised amount for analytics

-- ── WebSocket session table ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS websocket_sessions (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    connection_id TEXT        NOT NULL UNIQUE,
    connected_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
    last_ping    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ws_sessions_user
    ON websocket_sessions (user_id);
