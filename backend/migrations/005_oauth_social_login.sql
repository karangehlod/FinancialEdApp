-- Migration 005: OAuth / social login accounts
-- Links external provider identities to local users.

CREATE TABLE IF NOT EXISTS oauth_accounts (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider         VARCHAR(32)  NOT NULL,           -- 'google' | 'apple'
    provider_user_id TEXT         NOT NULL,
    email            TEXT,
    access_token_enc TEXT,                             -- Fernet-encrypted
    refresh_token_enc TEXT,                            -- Fernet-encrypted
    token_expires_at TIMESTAMPTZ,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (provider, provider_user_id)
);

CREATE INDEX IF NOT EXISTS idx_oauth_accounts_user
    ON oauth_accounts (user_id);

CREATE INDEX IF NOT EXISTS idx_oauth_accounts_provider_uid
    ON oauth_accounts (provider, provider_user_id);

-- ── PKCE state table (short-lived, cleaned up after callback) ─────────────

CREATE TABLE IF NOT EXISTS oauth_state (
    state       TEXT         PRIMARY KEY,
    provider    VARCHAR(32)  NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ  NOT NULL DEFAULT now() + INTERVAL '10 minutes'
);

CREATE INDEX IF NOT EXISTS idx_oauth_state_expires
    ON oauth_state (expires_at);
