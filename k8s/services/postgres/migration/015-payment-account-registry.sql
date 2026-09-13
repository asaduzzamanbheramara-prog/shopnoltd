-- Shopnoltd payment-account registry reconciliation.
-- This file is intentionally idempotent because the PostgreSQL migration Job
-- executes every SQL file on each GitOps migration hook.

BEGIN;

CREATE TABLE IF NOT EXISTS public.payment_accounts (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    provider VARCHAR(32) NOT NULL,
    account_label VARCHAR(128) NOT NULL,
    account_type VARCHAR(32) NOT NULL DEFAULT 'manual',
    currency VARCHAR(8) NOT NULL DEFAULT 'BDT',
    display_name VARCHAR(128),
    masked_account VARCHAR(128),
    public_identifier VARCHAR(128),
    private_value VARCHAR(256),
    instructions VARCHAR(1000),
    qr_url VARCHAR(2048),
    payment_url VARCHAR(2048),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_payment_accounts_tenant
    ON public.payment_accounts (tenant_id);
CREATE INDEX IF NOT EXISTS ix_payment_accounts_provider
    ON public.payment_accounts (provider);
CREATE INDEX IF NOT EXISTS ix_payment_accounts_status
    ON public.payment_accounts (status);
CREATE INDEX IF NOT EXISTS ix_payment_accounts_tenant_sort
    ON public.payment_accounts (tenant_id, sort_order);

-- Advance the service migration marker only when the previous payment head is
-- present. Never move an unknown/newer database backwards.
UPDATE public.alembic_version
SET version_num = '0006_payment_accounts'
WHERE version_num = '0005_direct_payments';

COMMIT;
