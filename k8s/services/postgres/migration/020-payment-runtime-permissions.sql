-- Runtime database permissions for payment-service-owned tables.
--
-- The canonical PostgreSQL migration job runs as the database owner. Runtime
-- services connect as the least-privileged "shopno" role, so tables created by
-- the migration hook must explicitly grant only the DML needed by
-- payment-service. This migration is idempotent and never changes ownership.

BEGIN;

GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE
    public.wallets,
    public.transactions,
    public.webhook_events,
    public.direct_payment_accounts,
    public.direct_payment_intents,
    public.direct_payment_submissions,
    public.payment_accounts
TO shopno;

-- Audit history is append-only from the payment service. The generic admin
-- control plane needs read access; service code only appends audit records.
GRANT SELECT, INSERT ON TABLE public.admin_audit_log TO shopno;

COMMIT;
