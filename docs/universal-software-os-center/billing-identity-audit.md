# Software & OS Center: billing and identity integration audit

**Status:** repository-source review updated against the payment tenant-isolation branch. No production credentials, cluster secrets, or production databases were accessed.

## Billing and paid-catalogue boundary

The repository contains more than one payment-related service. The catalogue must not assume that a successful checkout response means a user has paid or is entitled to install/run a privileged task.

The separate `billing-engine/app/main.py` exposes `POST /checkout` with client-supplied `amount`, `currency`, `customer_email`, and optional `reference`. That route must not be wired directly to unlock paid catalogue items without a separate security review and a server-side order/entitlement contract.

The versioned API facade at `platform/api-service/app/api/v1.py` verifies bearer tokens for user-facing routes and proxies to downstream payment services. Its routes and the separate billing engine are not interchangeable by assumption.

Before paid access is enabled:
1. Derive customer identity from a verified Shopnoltd session/JWT; never trust a browser-supplied email as proof of identity.
2. Map product/plan IDs to server-owned prices and currency rules; ignore client-supplied prices.
3. Create unpredictable order IDs with idempotency protection.
4. Grant entitlement only after a verified gateway-signed webhook or authoritative server-to-server payment-status check. A browser redirect or `is_demo` response is not proof of payment.
5. Store owner, product/feature key, transaction/order ID, status, and expiry/revocation semantics.
6. Protect entitlement APIs with authentication, authorization, rate limits, and audit records.
7. Keep gateway secrets in the secret manager, never in frontend files or this repository.
8. Test duplicate/replayed webhooks, failed/pending/refunded payments, wrong currency/amount, cross-user access, and demo-mode transactions.

The current catalogue is public metadata and official-source links. It does not collect payment details, claim paid access, run local commands, or install software. Keep that safe scope until payment and identity are verified end-to-end.

## Payment identity model: source-level correction

The payment service uses the verified Keycloak JWT `sub` as its payment `user_id`. The OAuth `UserMirror` model has a separate internal `id` and `keycloak_id`; they are not interchangeable identifiers.

The payment schema reconciliation SQL at `k8s/services/postgres/migration/012-payment-schema-reconciliation.sql` now documents that payment `user_id` values are JWT subjects and does **not** declare foreign keys to OAuth `users.id`. The payment migration `0008_payment_external_identity` removes the legacy `{wallets,transactions,wallet_ledger_entries,payment_methods}_user_id_fkey` constraints, because a PostgreSQL foreign key cannot reference a different service database and the stored JWT subject is not the OAuth mirror UUID.

The downgrade for migration 0008 intentionally does not recreate those invalid foreign keys. Reintroducing them would make valid payment writes fail. Tenant ownership remains enforced by the payment service's authenticated, tenant-scoped queries; this does not remove the need to audit existing rows and runtime claims.

**What is validated:** the repository migration chain and the migration behavior against disposable PostgreSQL databases are covered by CI, including the 0008 forward migration and removal of the legacy constraints.

**What is not validated:** CI does not prove that production has applied 0008, that the live payment service connects to the same PostgreSQL host used by the shared migration Job, or that all existing JWT subjects and tenant claims are valid.

## Database target and migration execution boundary

The payment Deployment obtains `DATABASE_URL` from Kubernetes Secret `payment-service-canonical-db`. The shared PostgreSQL migration Job obtains its connection host and credentials from `postgres-secret`; it does not read `payment-service-canonical-db`.

The payment SQL scripts `012-payment-schema-reconciliation.sql` and `024-payment-wallet-tenant-unique.sql` explicitly issue `\\connect payments`. Thus, for those scripts, the shared Job's effective PostgreSQL host and credentials are used to connect to the `payments` database. The Job's initial `POSTGRES_DB` value is not the final database selected by those scripts. The payment service's own `DATABASE_URL` remains a separate configuration source.

Repository source therefore establishes the intended database name for these SQL scripts, but it does **not** establish that the shared Job's effective host is the same PostgreSQL server as the payment service's secret URL. Do not infer host equivalence from service names or checked-in defaults.

The first-application path in migration 012 is guarded by a completion sentinel and row-count checks, then uses `DROP TABLE ... RESTRICT` and recreates payment tables. Those guards are fail-closed protections, not proof that every business-critical data location is included in the row-count checks. Do not run or rerun this reconciliation Job against production until its completion sentinel and target have been confirmed read-only.

## Release gates (must remain open until proven)

1. Using authorized read-only cluster access, compare only the non-secret host, port, and database metadata from `payment-service-canonical-db/DATABASE_URL` with the effective `POSTGRES_HOST`/port used by `postgres-secret`. Never print full URLs or secret values.
2. On the confirmed payment database, inspect `current_database()`, `current_schema()`, the Alembic version, the four legacy FK constraints, the migration-012 completion sentinel, and relevant table/index definitions. Do not select customer or payment rows.
3. Confirm Alembic is at `0008_payment_external_identity` and that no legacy JWT-subject-to-local-user foreign keys remain. If not, plan a separately reviewed, backup-protected migration; do not apply it as part of this repository audit.
4. Audit existing payment rows and tenant claims without exporting personal data. Identify users with missing/blank tenant claims and conflicting ownership before any backfill.
5. In disposable databases, test both first-application and already-applied paths of migration 012, including non-empty tables and missing/wrong prerequisites. Verify that unsafe cases stop without data loss.
6. Run staging end-to-end tests for deposits, withdrawals, transfers, signed webhooks, idempotency, refunds, wallet ledger integrity, and entitlement grants/revocations.
7. Prove encrypted backup-key recovery and an isolated restore before production schema changes or deployment.

Until these gates pass, keep PR #554 in Draft and do not promote payment images, apply production migrations, or enable paid catalogue entitlements.

## Desktop helper and recovery boundary

A future desktop helper must be a separately signed, versioned client with least-privilege operations. Start with read-only diagnostics. Never let catalogue HTML/JSON or a remote API provide arbitrary shell commands. Destructive operations require a local target-device summary, backup warning, and explicit confirmation. A recovery image must be reproducible, license-reviewed, checksummed/signed, and tested in virtual machines before publication.
