\connect social
-- 025 — short-lived encrypted OAuth account-selection sessions.
-- Provider tokens and per-account Page tokens are encrypted before storage.
CREATE TABLE IF NOT EXISTS omnichannel_oauth_pending (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(128) NOT NULL,
    provider VARCHAR(64) NOT NULL,
    platform VARCHAR(64) NOT NULL,
    encrypted_payload TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_omnichannel_oauth_pending_owner_expiry
    ON omnichannel_oauth_pending (tenant_id, user_id, expires_at);

-- The social-service connects as the least-privileged shopno role.
GRANT SELECT, INSERT, UPDATE, DELETE
    ON TABLE omnichannel_oauth_pending TO shopno;
