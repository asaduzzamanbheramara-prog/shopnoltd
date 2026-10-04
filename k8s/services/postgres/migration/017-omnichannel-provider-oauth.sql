\connect social
-- 017 — secure omnichannel provider OAuth credentials
CREATE TABLE IF NOT EXISTS omnichannel_oauth_tokens (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(128) NOT NULL,
    provider VARCHAR(64) NOT NULL,
    platform VARCHAR(64) NOT NULL,
    provider_account_id VARCHAR(255) NOT NULL,
    username VARCHAR(255),
    display_name VARCHAR(255),
    scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    encrypted_access_token TEXT NOT NULL,
    encrypted_refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'connected',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, provider, platform, provider_account_id)
);

CREATE INDEX IF NOT EXISTS idx_omnichannel_oauth_tokens_user
    ON omnichannel_oauth_tokens (tenant_id, user_id);

CREATE INDEX IF NOT EXISTS idx_omnichannel_oauth_tokens_status
    ON omnichannel_oauth_tokens (tenant_id, status);
