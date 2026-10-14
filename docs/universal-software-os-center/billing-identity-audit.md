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
