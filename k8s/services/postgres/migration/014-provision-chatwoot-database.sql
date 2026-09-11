-- Idempotently provision the PostgreSQL database used by Chatwoot.
-- Chatwoot defaults to the database name `chatwoot_production` when
-- POSTGRES_DATABASE is not explicitly set. Keep this database creation in
-- the platform migration control plane so a fresh/reconciled cluster does
-- not fail before the Rails process can run its own schema migrations.
SELECT 'CREATE DATABASE chatwoot_production'
WHERE NOT EXISTS (
  SELECT FROM pg_database WHERE datname = 'chatwoot_production'
)\gexec

GRANT ALL PRIVILEGES ON DATABASE chatwoot_production TO shopno;

-- Rails connects as the application role, not the PostgreSQL superuser.
-- The schema grant must be made inside the Chatwoot database, not shopnoltd.
\\connect chatwoot_production
GRANT USAGE, CREATE ON SCHEMA public TO shopno;
