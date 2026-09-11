-- Shopnoltd payment schema reconciliation.
--
-- This file is executed by an Argo Sync hook, so it must be safe to run again
-- after the payment schema has already reached 0005. psql conditionals keep a
-- successful deployment from destructively rebuilding payment tables on every
-- later Argo sync.

SELECT EXISTS (
    SELECT 1
    FROM public.alembic_version
    WHERE version_num = '0005_direct_payments'
) AS migration_complete \gset

\if :migration_complete
\echo 'Shopnoltd payment schema already at 0005_direct_payments; skipping reconciliation.'
\else

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
        'payment_methods',
        'webhook_events'
    ] LOOP
        IF to_regclass(format('public.%I', table_name)) IS NOT NULL THEN
            EXECUTE format('SELECT count(*) FROM public.%I', table_name) INTO row_count;
            IF row_count <> 0 THEN
                RAISE EXCEPTION
                    'REFUSING PAYMENT SCHEMA REPLACEMENT: public.% has % rows; expected 0',
                    table_name, row_count;
            END IF;
        END IF;
    END LOOP;
END
$$;

-- Do not use CASCADE. RESTRICT makes newly introduced dependencies fail closed.
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
    CONSTRAINT uq_wallet_tenant_user_currency UNIQUE (tenant_id, user_id, currency)
);

CREATE INDEX ix_wallets_tenant_id ON public.wallets (tenant_id);
CREATE INDEX ix_wallets_user_id ON public.wallets (user_id);

CREATE TABLE public.transactions (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
    user_id VARCHAR(64) NOT NULL REFERENCES public.users(id),
    wallet_id UUID NOT NULL REFERENCES public.wallets(id),
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
CREATE INDEX ix_tx_external_method ON public.transactions (external_id, method);
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

-- 0002: admin audit log. Keep it if it already exists; never destroy audit data.
CREATE TABLE IF NOT EXISTS public.admin_audit_log (
    id UUID PRIMARY KEY,
    actor VARCHAR(128) NOT NULL,
    action VARCHAR(16) NOT NULL,
    table_name VARCHAR(128) NOT NULL,
    record_id VARCHAR(128),
    before JSONB,
    after JSONB,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_admin_audit_log_actor ON public.admin_audit_log (actor);
CREATE INDEX IF NOT EXISTS ix_admin_audit_log_table_name ON public.admin_audit_log (table_name);
CREATE INDEX IF NOT EXISTS ix_admin_audit_log_created_at ON public.admin_audit_log (created_at);

-- 0005: direct-number payment accounts, intents and customer evidence.
CREATE TABLE public.direct_payment_accounts (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    provider VARCHAR(16) NOT NULL,
    account_type VARCHAR(16) NOT NULL,
    account_number VARCHAR(32) NOT NULL,
    display_name VARCHAR(128),
    currency VARCHAR(8) NOT NULL DEFAULT 'BDT',
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    verification_mode VARCHAR(32) NOT NULL DEFAULT 'manual',
    instructions VARCHAR(1000),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
);
CREATE INDEX ix_direct_payment_accounts_tenant_id
    ON public.direct_payment_accounts (tenant_id);
CREATE INDEX ix_direct_payment_accounts_provider
    ON public.direct_payment_accounts (provider);
CREATE UNIQUE INDEX uq_direct_account_number
    ON public.direct_payment_accounts (tenant_id, provider, account_number);

CREATE TABLE public.direct_payment_intents (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    order_id VARCHAR(128),
    account_id UUID NOT NULL REFERENCES public.direct_payment_accounts(id),
    provider VARCHAR(16) NOT NULL,
    amount NUMERIC(20,8) NOT NULL,
    currency VARCHAR(8) NOT NULL,
    expected_reference VARCHAR(64) NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'created',
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    CONSTRAINT uq_direct_payment_intents_expected_reference UNIQUE (expected_reference)
);
CREATE INDEX ix_direct_payment_intents_tenant_id ON public.direct_payment_intents (tenant_id);
CREATE INDEX ix_direct_payment_intents_user_id ON public.direct_payment_intents (user_id);
CREATE INDEX ix_direct_payment_intents_order_id ON public.direct_payment_intents (order_id);
CREATE INDEX ix_direct_payment_intents_status ON public.direct_payment_intents (status);
CREATE INDEX ix_direct_payment_intents_expires_at ON public.direct_payment_intents (expires_at);

CREATE TABLE public.direct_payment_submissions (
    id UUID PRIMARY KEY,
    intent_id UUID NOT NULL REFERENCES public.direct_payment_intents(id),
    provider VARCHAR(16) NOT NULL,
    txid VARCHAR(128) NOT NULL,
    sender_number VARCHAR(32),
    amount_claimed NUMERIC(20,8) NOT NULL,
    raw_evidence JSONB NOT NULL,
    verification_data JSONB,
    status VARCHAR(24) NOT NULL DEFAULT 'submitted',
    transaction_id UUID REFERENCES public.transactions(id),
    verified_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
);
CREATE INDEX ix_direct_payment_submissions_intent_id
    ON public.direct_payment_submissions (intent_id);
CREATE INDEX ix_direct_payment_submissions_status
    ON public.direct_payment_submissions (status);
CREATE UNIQUE INDEX uq_direct_submission_provider_txid
    ON public.direct_payment_submissions (provider, txid);

-- 0004 and 0005 are represented above, so the database can safely be stamped
-- at the actual Alembic head without silently skipping schema changes.
UPDATE public.alembic_version SET version_num = '0005_direct_payments';

COMMIT;

\endif
