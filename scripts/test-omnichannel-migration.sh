#!/usr/bin/env bash
set -euo pipefail

: "${TEST_DATABASE_URL:?TEST_DATABASE_URL must point to the disposable CI database}"
migration="k8s/services/postgres/migration/021-omnichannel-action-executor.sql"

# Build the minimum pre-existing table contract that migration 021 extends.
psql "$TEST_DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE platform_actions (
  id UUID PRIMARY KEY,
  status VARCHAR(24) NOT NULL DEFAULT 'queued',
  response_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
SQL

# Run twice to prove the migration is safe to retry.
psql "$TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -f "$migration"
psql "$TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -f "$migration"

psql "$TEST_DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
DO $$
DECLARE
  missing_column TEXT;
BEGIN
  SELECT required.name INTO missing_column
  FROM (VALUES ('attempt_count'), ('claimed_at'), ('next_attempt_at'),
               ('approval_status'), ('approved_by'), ('approved_at')) AS required(name)
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns c
    WHERE c.table_schema='public'
      AND c.table_name='platform_actions'
      AND c.column_name=required.name
  )
  LIMIT 1;
  IF missing_column IS NOT NULL THEN
    RAISE EXCEPTION 'migration missing required column: %', missing_column;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname='public' AND indexname='ix_platform_actions_approved_worker_queue'
  ) THEN
    RAISE EXCEPTION 'approved action queue index was not created';
  END IF;
END $$;

INSERT INTO platform_actions (id, status)
VALUES ('00000000-0000-4000-8000-000000000021', 'queued');

DO $$
DECLARE
  actual_status TEXT;
BEGIN
  SELECT approval_status INTO actual_status
  FROM platform_actions
  WHERE id='00000000-0000-4000-8000-000000000021';
  IF actual_status IS DISTINCT FROM 'pending' THEN
    RAISE EXCEPTION 'new action approval_status must default to pending, got %', actual_status;
  END IF;
END $$;
SQL

echo "PASS: migration 021 applies twice, creates approval/worker columns and index, and defaults actions to pending."
