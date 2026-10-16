# Software & OS Center: billing and identity integration audit

**Status: read-only repository review; no credentials or production systems were accessed.**

## Finding

The existing repository contains more than one payment-related service. The catalogue must not assume that a successful checkout response means a user has paid or is entitled to install/run a privileged task.

The current `billing-engine/app/main.py` exposes `POST /checkout` with a request model containing client-supplied `amount`, `currency`, `customer_email`, and optional `reference`. In the reviewed file, the route creates/looks up a user from the supplied email and calls the selected gateway. The route itself does not establish a signed-in Shopnoltd identity or a server-owned catalogue price/entitlement. Therefore this endpoint must **not** be wired directly to unlock paid catalogue items without a separate security review and server-side order/entitlement contract.

The repository also has a versioned API facade at `platform/api-service/app/api/v1.py` that verifies bearer tokens for user-facing routes and proxies to downstream payment services. Its payment service routes and the separate billing engine are not interchangeable by assumption.

## Required contract before paid access

1. The server derives the customer identity from a verified Shopnoltd session/JWT; never trust an email supplied by the browser as proof of identity.
2. Product/plan IDs map to server-owned prices and currency rules. Ignore client-supplied prices.
3. Create an order with an unpredictable ID and idempotency protection.
4. Grant entitlement only after the server verifies a gateway-signed webhook or performs an authoritative server-to-server payment-status check. A browser redirect or `is_demo` response is not proof of payment.
5. Store entitlement with user ID, product/feature key, transaction/order ID, status, and expiry/revocation semantics.
6. Protect entitlement APIs with authentication and authorization; rate-limit them and audit grants/revocations.
7. Keep gateway secrets in the existing secret manager, never in frontend files or this public repository.
8. Test duplicate/replayed webhooks, failed/pending/refunded payments, wrong currency/amount, cross-user access, and demo-mode transactions.

## Safe scope now

The current catalogue is public metadata and official-source links. It does not collect payment details, claim paid access, run local commands, or install software. Keep that behaviour until the payment and identity contract is verified end-to-end.

## Desktop helper and recovery boundary

A future desktop helper must be a separately signed, versioned client with least-privilege operations. Start with read-only diagnostics. Never let catalogue HTML/JSON or a remote API provide arbitrary shell commands. Destructive operations require a local target-device summary, backup warning, and explicit confirmation. A recovery image must be reproducible, license-reviewed, checksummed/signed, and tested in virtual machines before publication.


## Identity mapping follow-up (verified against current source)

The payment service currently authenticates a token and uses the JWT `sub` directly as `user_id` in payment routes (including `platform/payment-service/app/api/deposits.py` and `platform/payment-service/app/api/transactions.py`). The OAuth service's `UserMirror` model distinguishes its internal `id` from `keycloak_id`; the `/users/me` response exposes the internal `id` as `id` and the Keycloak subject as `sub`. Separately, `k8s/services/postgres/migration/012-payment-schema-reconciliation.sql` defines `wallets.user_id` and `transactions.user_id` as foreign keys to `public.users(id)`.

**This is a concrete source-level identity/schema mismatch that must be investigated before release.** The payment routes write `sub`, while the reconciliation schema expects the internal `users.id`. If that schema is the one deployed and the IDs differ as the OAuth model indicates, payment writes can fail their foreign-key constraints. Repository inspection alone cannot establish which schema is currently deployed or whether another compatibility layer exists, so treat this as a high-priority verification/fix—not as a confirmed production incident.

Before adding a software entitlement table or granting catalogue access, resolve and test the canonical mapping explicitly:
- Decide whether payment/entitlement ownership stores the internal Shopnoltd user ID, the Keycloak subject, or both as separately named columns.
- If a JWT subject is used for authentication, resolve it through the trusted identity service to the canonical Shopnoltd user ID before database writes; never resolve accounts by browser-supplied email.
- Confirm that the deployed `public.users` table and the payment service use the same canonical identifier and tenant policy. Add an integration test proving a real authenticated subject maps to exactly one owner row.
- Verify existing payment writes and schema constraints in a disposable test database before adding any new foreign key or migration. Do not edit or run production migrations as part of this audit.

This is a release blocker for a paid entitlement implementation, not a claim that all existing payment routes are broken. The repository has multiple payment paths and schema histories, so the runtime database state must be checked before drawing that broader conclusion.


## Database-boundary follow-up (repository configuration review)

The checked-in defaults point the OAuth service at database `oauth` and the payment service at database `payments`. The Kubernetes payment deployment overrides `DATABASE_URL` from the separate secret `payment-service-canonical-db`. The shared PostgreSQL migration Job instead connects to `POSTGRES_DB` from `postgres-secret` (falling back to `postgres` in its shell command) and runs the shared `k8s/services/postgres/migration/*.sql` files there; it does not read the payment service's `DATABASE_URL` secret.

This means repository source alone does **not** prove that the shared payment-table reconciliation migration targets the same database used by the payment service. It also cannot make a PostgreSQL foreign key in the payment database reference the OAuth service's `oauth.users` table, because PostgreSQL foreign keys cannot span databases. The `public.users(id)` references in migration `012-payment-schema-reconciliation.sql` therefore require an explicit database-target/schema review before they can be considered a valid identity constraint.

**Required before release:** verify the actual value of `payment-service-canonical-db/DATABASE_URL`, `postgres-secret/POSTGRES_DB`, the migration Job's effective target, and the deployed schema using read-only checks. Do not print credentials or connection strings in CI logs. Then choose and document one ownership model for payment rows (prefer the verified JWT subject as a stable external identity key, or a canonical internal ID resolved through a trusted identity service) and enforce it consistently across wallets, transactions, transfers, and entitlements. Any schema repair must be a new, idempotent migration tested against disposable copies of both the migration target and payment-service database; do not edit historical migrations as a substitute for repairing an already-deployed database.

This remains an explicit release blocker. No production database was accessed or changed during this repository review.

## Follow-up: migration target and destructive reconciliation gate

A second read-only pass verified the migration Job manifest, rather than relying only on a search excerpt:

- `k8s/services/postgres/migration/migrate-job.yaml` imports `postgres-secret` and runs every mounted SQL file against `POSTGRES_HOST` (default `postgres`) and `POSTGRES_DB` (default `postgres`). It does **not** read the payment deployment's `payment-service-canonical-db` secret.
- `k8s/services/payment-service/deployment.yaml` separately supplies `DATABASE_URL` from `payment-service-canonical-db`.
- `platform/oauth-service/app/models/models.py` defines `users.id` as an application-generated UUID string and `users.keycloak_id` as a separate unique identity. `platform/oauth-service/app/api/users.py` returns these as `id` and `sub`, respectively.
- `012-payment-schema-reconciliation.sql` contains a guarded table-replacement path: when its completion sentinel is absent, it checks several existing payment tables for rows, then drops/recreates those tables with user foreign keys. The row-count guard and RESTRICT constraints are useful fail-closed checks, but they do not prove that the target database is correct or that all business-critical data is represented in the checked tables.

### Release-blocking decision

This is not just an unknown runtime value: the repository manifests show that the migration Job and payment service obtain connection settings from different configuration sources. It is still unknown whether those secrets intentionally resolve to the same PostgreSQL database/schema in the deployed cluster. The SQL also assumes `public.users(id)` is present in the migration target. Do not run or re-run this reconciliation Job, alter its target, or apply another payment migration until an authorized operator confirms the target safely.

### Required read-only verification (do not print secret values)

1. Confirm the payment service's effective database host/database/schema and the migration Job's effective host/database/schema using approved tooling that redacts credentials. Compare only non-secret connection metadata; never print a full connection URL or password.
2. On each intended target, inspect `current_database()`, `current_schema()`, the `public.users` table definition, the payment tables, foreign-key definitions, and the migration sentinel. Use a read-only database role and avoid selecting customer/payment rows.
3. Verify whether `public.users.id` contains the same canonical identifier as the payment JWT subject. The source model says these are distinct fields; do not assume they are interchangeable.
4. In disposable test databases, test both the already-applied and first-application paths of `012-payment-schema-reconciliation.sql`, including non-empty payment tables and missing/wrong `public.users`. Confirm that unsafe cases stop without dropping or modifying data.
5. Only after the canonical identity and database target are proven should a separate reviewed change introduce an explicit identity-resolution boundary and integration tests. Do not solve this by trusting a client email, blindly changing a foreign key, or guessing which database is canonical.

No cluster, secret, or database was accessed by this repository-only audit. Paid catalogue access remains disabled/not implemented by this PR.
