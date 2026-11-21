\connect social
-- 026 — make provider connections explicitly owned by a Shopnoltd user.
-- Existing OAuth rows are backfilled from their encrypted-token ownership.
-- Legacy rows without a provable owner remain unassigned and are not exposed
-- through user-scoped connection APIs.
ALTER TABLE social_connections
    ADD COLUMN IF NOT EXISTS owner_user_id VARCHAR(128);

UPDATE social_connections c
   SET owner_user_id = t.user_id
  FROM omnichannel_oauth_tokens t
 WHERE c.owner_user_id IS NULL
   AND c.tenant_id = t.tenant_id
   AND c.platform = t.platform
   AND c.platform_account_id = t.provider_account_id
   AND COALESCE(c.metadata->>'provider', t.provider) = t.provider;

CREATE INDEX IF NOT EXISTS idx_social_connections_owner
    ON social_connections (tenant_id, owner_user_id, platform, created_at DESC);

-- Keep the existing tenant/platform/account uniqueness constraint as a
-- deliberate exclusive-ownership guard. Cross-user sharing must be explicit
-- and permission-backed rather than achieved by overwriting OAuth credentials.

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE social_connections TO shopno;
