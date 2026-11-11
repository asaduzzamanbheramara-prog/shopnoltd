-- Forward-only repair for the payment wallet tenant uniqueness invariant.
-- The payment service runtime does not run Alembic; the canonical PostgreSQL
-- migration hook applies this file after the existing 023 model migrations.
-- This script is idempotent and never rewrites wallet rows.

\connect payments

BEGIN;

DO $$
DECLARE
    current_version text;
BEGIN
    IF to_regclass('public.wallets') IS NULL THEN
        RAISE EXCEPTION 'public.wallets is missing; refusing payment wallet repair';
    END IF;

    IF to_regclass('public.alembic_version') IS NULL THEN
        RAISE EXCEPTION 'public.alembic_version is missing; refusing payment wallet repair';
    END IF;

    SELECT version_num INTO current_version FROM public.alembic_version;
    IF current_version IS NULL
       OR current_version NOT IN (
           '0006_payment_accounts',
           '0007_wallet_tenant_user_currency'
       ) THEN
        RAISE EXCEPTION
            'unexpected payment Alembic version %, expected 0006 or 0007; refusing repair',
            current_version;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM public.wallets
        GROUP BY tenant_id, user_id, currency
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION
            'wallets contains duplicate tenant/user/currency keys; refusing uniqueness repair';
    END IF;
END
$$;

-- Do not silently accept a conflicting object with the intended index name.
DO $$
DECLARE
    existing_definition text;
BEGIN
    SELECT pg_get_indexdef(i.indexrelid)
      INTO existing_definition
      FROM pg_index i
      JOIN pg_class c ON c.oid = i.indexrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'public'
       AND c.relname = 'ix_wallet_tenant_user_currency';

    IF existing_definition IS NOT NULL
       AND (
           existing_definition NOT LIKE 'CREATE UNIQUE INDEX%'
           OR existing_definition NOT LIKE '%(tenant_id, user_id, currency)%'
       ) THEN
        RAISE EXCEPTION
            'ix_wallet_tenant_user_currency exists with an unexpected definition; refusing repair';
    END IF;
END
$$;

ALTER TABLE public.wallets
    DROP CONSTRAINT IF EXISTS ix_wallet_user_currency;
DROP INDEX IF EXISTS public.ix_wallet_user_currency;

CREATE UNIQUE INDEX IF NOT EXISTS ix_wallet_tenant_user_currency
    ON public.wallets (tenant_id, user_id, currency);

-- Verify the intended invariant before advancing the migration marker.
DO $$
DECLARE
    verified_definition text;
BEGIN
    SELECT pg_get_indexdef(i.indexrelid)
      INTO verified_definition
      FROM pg_index i
      JOIN pg_class c ON c.oid = i.indexrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'public'
       AND c.relname = 'ix_wallet_tenant_user_currency';

    IF verified_definition IS NULL
       OR verified_definition NOT LIKE 'CREATE UNIQUE INDEX%'
       OR verified_definition NOT LIKE '%(tenant_id, user_id, currency)%' THEN
        RAISE EXCEPTION 'tenant-scoped wallet unique index verification failed';
    END IF;
END
$$;

UPDATE public.alembic_version
SET version_num = '0007_wallet_tenant_user_currency'
WHERE version_num = '0006_payment_accounts';

COMMIT;
