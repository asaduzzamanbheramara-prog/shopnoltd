-- Shopnoltd payment schema reconciliation.
--
-- Preconditions are intentionally strict: the legacy payment tables must be
-- empty. This migration preserves users and every unrelated application table
-- and replaces only the isolated legacy payment tables with the schema used
-- by payment-service and billing-engine.

BEGIN;

DO $$
DECLARE
    table_name text;
    row_count bigint;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'wallets',
        'transactions',
        'wallet_ledger_entries',
        'payment_methods'
    ] LOOP
        EXECUTE format('SELECT count(*) FROM public.%I', table_name) INTO row_count;
        IF row_count <> 0 THEN
            RAISE EXCEPTION
                'REFUSING PAYMENT SCHEMA REPLACEMENT: public.% has % rows; expected 0',
                table_name, row_count;
        END IF;
    END LOOP;
END
$$;

-- Do not use CASCADE here. The pre-migration dependency audit established
-- that these tables have no application-level dependents. RESTRICT makes any
-- newly introduced dependency fail closed instead of being silently removed.
DROP TABLE IF EXISTS public.webhook_events RESTRICT;
DROP TABLE public.transactions RESTRICT;
DROP TABLE public.wallet_ledger_entries RESTRICT;
DROP TABLE public.wallets RESTRICT;
DROP TABLE public.payment_methods RESTRICT;

CREATE TABLE public.wallets (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
    user_id VARCHAR(64) NOT NULL REFERENCES public.users(id),
    currency VARCHAR(8) NOT NULL,
    balance NUMERIC(20,8) NOT NULL DEFAULT 0,
    frozen NUMERIC(20,8) NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_wallet_user_currency UNIQUE (user_id, currency)
);

CREATE INDEX ix_wallets_tenant_id ON public.wallets (tenant_id);
CREATE INDEX ix_wallets_user_id ON public.wallets (user_id);

CREATE TABLE public.transactions (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
    user_id VARCHAR(64) REFERENCES public.users(id),
    wallet_id UUID REFERENCES public.wallets(id),
    type VARCHAR(32) NOT NULL DEFAULT 'deposit',
    method VARCHAR(32) NOT NULL DEFAULT 'manual',
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    amount NUMERIC(20,8) NOT NULL,
    fee NUMERIC(20,8) NOT NULL DEFAULT 0,
    currency VARCHAR(8) NOT NULL,
    external_id VARCHAR(128),
    reference VARCHAR(128),
    idempotency_key VARCHAR(128),
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    approved_by VARCHAR(64),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITHOUT TIME ZONE,

    -- Compatibility fields retained for the existing billing gateway/webhook
    -- implementation while both services converge on the canonical model.
    gateway VARCHAR(64),
    gateway_reference TEXT,
    is_demo BOOLEAN,
    raw_response TEXT,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_transactions_tenant_id ON public.transactions (tenant_id);
CREATE INDEX ix_transactions_user_id ON public.transactions (user_id);
CREATE INDEX ix_transactions_status ON public.transactions (status);
CREATE INDEX ix_transactions_external_id ON public.transactions (external_id);
CREATE INDEX ix_transactions_created_at ON public.transactions (created_at);
CREATE UNIQUE INDEX uq_transaction_deposit_idempotency
    ON public.transactions (tenant_id, user_id, type, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE TABLE public.wallet_ledger_entries (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES public.users(id),
    currency VARCHAR(8) NOT NULL,
    entry_type VARCHAR NOT NULL,
    amount NUMERIC(20,8) NOT NULL,
    balance_after NUMERIC(20,8) NOT NULL,
    reason TEXT NOT NULL,
    reference VARCHAR,
    created_by VARCHAR,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_wallet_ledger_entries_user_id
    ON public.wallet_ledger_entries (user_id);
CREATE INDEX ix_wallet_ledger_entries_user_currency_created
    ON public.wallet_ledger_entries (user_id, currency, created_at);

CREATE TABLE public.payment_methods (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR(64) REFERENCES public.users(id),
    gateway VARCHAR,
    label TEXT,
    gateway_token TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX ix_payment_methods_user_id
    ON public.payment_methods (user_id);

CREATE TABLE public.webhook_events (
    id UUID PRIMARY KEY,
    provider VARCHAR(32) NOT NULL,
    event_key VARCHAR(128) NOT NULL,
    transaction_id UUID REFERENCES public.transactions(id),
    status VARCHAR(32) NOT NULL DEFAULT 'received',
    payload_hash VARCHAR(64) NOT NULL,
    received_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP WITHOUT TIME ZONE
);

CREATE UNIQUE INDEX uq_webhook_provider_event
    ON public.webhook_events (provider, event_key);

-- The database was previously stamped at 0002 while the 0003 revision file
-- exists in source. This reconciliation performs the 0003 webhook work plus
-- the isolated legacy-table replacement, so mark the linear Alembic chain as
-- complete rather than allowing 0003 to attempt to recreate webhook_events.
UPDATE public.alembic_version
SET version_num = '0003_webhook_events'
WHERE version_num = '0002_admin_audit_log';

COMMIT;
