-- Forward-only, idempotent repair for the payment transaction status width.
-- SQL migrations run after 027-payment-transaction-idempotency.sql.
\connect payments

BEGIN;

DO $$
DECLARE
    existing_type text;
    current_revision text;
    idempotency_index text;
BEGIN
    IF to_regclass('public.transactions') IS NULL THEN
        RAISE EXCEPTION 'public.transactions is missing; refusing status-width migration';
    END IF;

    SELECT format_type(a.atttypid, a.atttypmod)
      INTO existing_type
      FROM pg_attribute a
     WHERE a.attrelid = 'public.transactions'::regclass
       AND a.attname = 'status'
       AND a.attnum > 0
       AND NOT a.attisdropped;

    IF existing_type = 'character varying(16)' THEN
        ALTER TABLE public.transactions
            ALTER COLUMN status TYPE VARCHAR(24);
    ELSIF existing_type <> 'character varying(24)' THEN
        RAISE EXCEPTION 'transactions.status has unexpected type: %', existing_type;
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name = 'transactions'
           AND column_name = 'idempotency_key'
           AND data_type = 'character varying'
           AND character_maximum_length = 128
    ) THEN
        RAISE EXCEPTION 'transactions.idempotency_key is not ready; refusing to advance Alembic revision';
    END IF;

    SELECT pg_get_indexdef(i.indexrelid)
      INTO idempotency_index
      FROM pg_index i
      JOIN pg_class c ON c.oid = i.indexrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'public'
       AND c.relname = 'uq_transaction_deposit_idempotency';

    IF idempotency_index IS NULL
       OR idempotency_index NOT LIKE 'CREATE UNIQUE INDEX%'
       OR idempotency_index NOT LIKE '%(tenant_id, user_id, type, idempotency_key)%'
       OR idempotency_index NOT LIKE '%WHERE (idempotency_key IS NOT NULL)%' THEN
        RAISE EXCEPTION 'uq_transaction_deposit_idempotency is missing or unexpected';
    END IF;

    SELECT version_num INTO current_revision FROM public.alembic_version;
    IF current_revision NOT IN ('0007_wallet_tenant_user_currency', '0008_transaction_idempotency', '0009_transaction_status_varchar') THEN
        RAISE EXCEPTION 'unexpected payment Alembic revision: %', current_revision;
    END IF;

    UPDATE public.alembic_version
       SET version_num = '0009_transaction_status_varchar'
     WHERE version_num <> '0009_transaction_status_varchar';
END
$$;

COMMIT;
