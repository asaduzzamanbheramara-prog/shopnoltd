\connect social
-- 021 - per-user social automation schedules and approval-gated drafts
-- Safe additive migration. No provider side effects are enabled by this schema.

ALTER TABLE social_connections
  ADD COLUMN IF NOT EXISTS owner_user_id VARCHAR(128);

ALTER TABLE omnichannel_oauth_tokens
  ADD COLUMN IF NOT EXISTS refresh_token_expires_at TIMESTAMPTZ;

UPDATE social_connections c
SET owner_user_id = t.user_id
FROM omnichannel_oauth_tokens t
WHERE c.owner_user_id IS NULL
  AND c.tenant_id = t.tenant_id
  AND c.platform = t.platform
  AND c.platform_account_id = t.provider_account_id;

CREATE INDEX IF NOT EXISTS ix_social_connections_owner
  ON social_connections (tenant_id, owner_user_id, platform);

CREATE TABLE IF NOT EXISTS social_automation_schedules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id VARCHAR(64) NOT NULL,
  user_id VARCHAR(128) NOT NULL,
  connection_id UUID NOT NULL REFERENCES social_connections(id) ON DELETE CASCADE,
  platform VARCHAR(32) NOT NULL,
  content_template TEXT NOT NULL CHECK (length(trim(content_template)) BETWEEN 1 AND 10000),
  timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Dhaka',
  local_time TIME NOT NULL,
  days_of_week SMALLINT[] NOT NULL DEFAULT ARRAY[0,1,2,3,4,5,6]::SMALLINT[],
  next_run_at TIMESTAMPTZ NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT FALSE,
  last_run_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (cardinality(days_of_week) BETWEEN 1 AND 7),
  CHECK (days_of_week <@ ARRAY[0,1,2,3,4,5,6]::SMALLINT[])
);

ALTER TABLE social_automation_schedules
  ADD COLUMN IF NOT EXISTS paused_reason VARCHAR(255);

CREATE UNIQUE INDEX IF NOT EXISTS ux_social_automation_schedule_owner_slot
  ON social_automation_schedules (tenant_id, user_id, connection_id, local_time);

CREATE INDEX IF NOT EXISTS ix_social_automation_due
  ON social_automation_schedules (next_run_at, id)
  WHERE enabled = TRUE;

CREATE TABLE IF NOT EXISTS social_post_drafts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id VARCHAR(64) NOT NULL,
  user_id VARCHAR(128) NOT NULL,
  schedule_id UUID REFERENCES social_automation_schedules(id) ON DELETE SET NULL,
  connection_id UUID NOT NULL REFERENCES social_connections(id) ON DELETE CASCADE,
  platform VARCHAR(32) NOT NULL,
  content TEXT NOT NULL CHECK (length(trim(content)) BETWEEN 1 AND 10000),
  status VARCHAR(24) NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft','pending_approval','approved','queued','published','rejected','failed','cancelled')),
  scheduled_for TIMESTAMPTZ,
  content_sha256 CHAR(64) NOT NULL,
  approved_by VARCHAR(128),
  approved_at TIMESTAMPTZ,
  platform_action_id UUID REFERENCES platform_actions(id) ON DELETE SET NULL,
  idempotency_key VARCHAR(255) NOT NULL,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS ix_social_post_drafts_user_status
  ON social_post_drafts (tenant_id, user_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_social_post_drafts_schedule
  ON social_post_drafts (schedule_id, scheduled_for);

GRANT USAGE ON SCHEMA public TO shopno;
GRANT SELECT, INSERT, UPDATE, DELETE
  ON social_automation_schedules, social_post_drafts TO shopno;
