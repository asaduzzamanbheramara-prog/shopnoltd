#!/usr/bin/env bash
set -euo pipefail

: "${TEST_DATABASE_URL:?TEST_DATABASE_URL must point to the disposable CI database}"
base_migration="k8s/services/postgres/migration/016-omnichannel-crm.sql"
migration="k8s/services/postgres/migration/021-omnichannel-action-executor.sql"
blog_migration="k8s/services/postgres/migration/022-blog-scheduled-publication.sql"

# Reproduce the relevant pre-existing social schema, not a partial hand-built
# platform_actions table. Migration 016 grants privileges to the production
# service role, so create that role in the disposable CI cluster if absent.
psql "$TEST_DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'shopno') THEN
    CREATE ROLE shopno NOLOGIN;
  END IF;
END $$;
SQL

# Apply the real baseline contract and migration 021 twice to prove idempotency.
psql "$TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -f "$base_migration"
psql "$TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -f "$migration"
psql "$TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -f "$migration"

# The baseline contract is older than blog_posts, so model the pre-existing table
# contract that migration 022 extends; never test an ALTER against an empty DB.
psql "$TEST_DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS blog_posts (
  id VARCHAR(64) PRIMARY KEY,
  status VARCHAR(16) NOT NULL DEFAULT 'draft'
);
SQL
psql "$TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -f "$blog_migration"
psql "$TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -f "$blog_migration"

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

INSERT INTO platform_actions (id, platform, action, status)
VALUES ('00000000-0000-4000-8000-000000000021', 'telegram', 'send_message', 'queued');

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
END $;
SQL

psql "$TEST_DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
DO $
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='blog_posts' AND column_name='scheduled_at'
  ) THEN
    RAISE EXCEPTION 'migration 022 did not create scheduled_at';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname='public' AND indexname='ix_blog_posts_scheduled_publication'
  ) THEN
    RAISE EXCEPTION 'migration 022 did not create scheduled publication index';
  END IF;
END $;
SQL

echo "PASS: migrations 021 and 022 are repeatable; action approval defaults to pending and blog scheduling column/index exist."
