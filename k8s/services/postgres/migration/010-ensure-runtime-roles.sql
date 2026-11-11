-- Ensure legacy runtime roles exist so later GRANT statements cannot fail.
-- No passwords are set here; login credentials must come from Kubernetes Secrets.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'shopno') THEN
    CREATE ROLE shopno NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'chatwoot_prod') THEN
    CREATE ROLE chatwoot_prod NOLOGIN;
  END IF;
END
$$;
