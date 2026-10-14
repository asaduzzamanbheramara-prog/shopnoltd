"""Idempotent PostgreSQL migrations for the provisioning outbox."""
from sqlalchemy import text

PROVISIONING_CONSTRAINT_MIGRATION = """
DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_account_provisioning_resource_type'
          AND conrelid = (
              SELECT c.oid FROM pg_class AS c
              JOIN pg_namespace AS n ON n.oid = c.relnamespace
              WHERE c.relname = 'account_provisioning_jobs'
                AND n.nspname = current_schema()
          )
    ) THEN
        ALTER TABLE account_provisioning_jobs
        ADD CONSTRAINT ck_account_provisioning_resource_type
        CHECK (resource_type IN ('subdomain', 'mailbox')) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_account_provisioning_status'
          AND conrelid = (
              SELECT c.oid FROM pg_class AS c
              JOIN pg_namespace AS n ON n.oid = c.relnamespace
              WHERE c.relname = 'account_provisioning_jobs'
                AND n.nspname = current_schema()
          )
    ) THEN
        ALTER TABLE account_provisioning_jobs
        ADD CONSTRAINT ck_account_provisioning_status
        CHECK (status IN ('pending', 'processing', 'active', 'failed')) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_account_provisioning_attempts_nonnegative'
          AND conrelid = (
              SELECT c.oid FROM pg_class AS c
              JOIN pg_namespace AS n ON n.oid = c.relnamespace
              WHERE c.relname = 'account_provisioning_jobs'
                AND n.nspname = current_schema()
          )
    ) THEN
        ALTER TABLE account_provisioning_jobs
        ADD CONSTRAINT ck_account_provisioning_attempts_nonnegative
        CHECK (attempts >= 0) NOT VALID;
    END IF;
END
$migration$;
"""


async def ensure_account_provisioning_constraints(connection) -> None:
    """Apply outbox checks to existing tables without scanning historical rows."""
    await connection.execute(text(PROVISIONING_CONSTRAINT_MIGRATION))
