\connect social
-- 021 — bounded, auditable provider action execution metadata
ALTER TABLE platform_actions
  ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE platform_actions
  ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ;
ALTER TABLE platform_actions
  ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_platform_actions_worker_queue
  ON platform_actions (status, next_attempt_at, created_at)
  WHERE status IN ('queued', 'retry_wait');
ALTER TABLE platform_actions ADD COLUMN IF NOT EXISTS approval_status VARCHAR(24) NOT NULL DEFAULT 'pending';
ALTER TABLE platform_actions ADD COLUMN IF NOT EXISTS approved_by VARCHAR(128);
ALTER TABLE platform_actions ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS ix_platform_actions_approved_worker_queue ON platform_actions (status, next_attempt_at, created_at) WHERE status IN ('queued', 'retry_wait') AND approval_status = 'approved';
