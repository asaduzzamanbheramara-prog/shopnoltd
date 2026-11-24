-- Forward-only, idempotent repair for existing payment databases.
-- Historical transactions remain unchanged; the new key is nullable.
\connect payments

DO $$
DECLARE
    existing_type text;
    existing_index text;
BEGIN
    IF to_regclass('public.transactions') IS NULL THEN
        RAISE EXCEPTION 'public.transactions is missing; refusing idempotency repair';
    END IF;

    SELECT format_type(a.atttypid, a.atttypmod)
      INTO existing_type
      FROM pg_attribute a
     WHERE a.attrelid = 'public.transactions'::regclass
       AND a.attname = 'idempotency_key'
       AND a.attnum > 0
       AND NOT a.attisdropped;

    IF existing_type IS NOT NULL AND existing_type <> 'character varying(128)' THEN
        RAISE EXCEPTION 'transactions.idempotency_key has unexpected type: %', existing_type;
    END IF;

    SELECT pg_get_indexdef(i.indexrelid)
      INTO existing_index
      FROM pg_index i
      JOIN pg_class c ON c.oid = i.indexrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'public'
       AND c.relname = 'uq_transaction_deposit_idempotency';

    IF existing_index IS NOT NULL
       AND (
           existing_index NOT LIKE 'CREATE UNIQUE INDEX%'
           OR existing_index NOT LIKE '%(tenant_id, user_id, type, idempotency_key)%'
           OR existing_index NOT LIKE '%WHERE (idempotency_key IS NOT NULL)%'
       ) THEN
        RAISE EXCEPTION 'uq_transaction_deposit_idempotency exists with an unexpected definition';
    END IF;
END
$$;

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(128);

CREATE UNIQUE INDEX IF NOT EXISTS uq_transaction_deposit_idempotency
    ON public.transactions (tenant_id, user_id, type, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
