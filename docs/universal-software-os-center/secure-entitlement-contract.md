# Secure paid-access (entitlement) contract

## Status

Design contract only. This document does not activate paid access, modify payment routes, or grant entitlements. Implementation must remain disabled until the identity, transaction, persistence, and webhook requirements below are met and tested.

## Why this is a separate step

The current repository contains more than one billing/payment path. The legacy `billing-engine` checkout request accepts a client-provided amount, currency, customer email, and optional reference. Its `Subscription` model does not itself bind a subscription to a user ID or transaction. The versioned API also proxies authenticated deposit requests to the payment service. These are not sufficient evidence that a particular product purchase has been authoritatively paid and assigned to the authenticated account.

Do not reuse a browser-supplied email, amount, plan, transaction status, return URL, or local-storage flag as authorization evidence.

## Proposed read contract

`GET /api/v1/me/entitlements`

- Requires a valid Shopnoltd access token.
- Derives the account identity from the verified token subject (`sub`); never accepts a caller-supplied user ID as the authority.
- Returns only entitlements belonging to that authenticated account and tenant.
- Does not create, extend, or repair an entitlement as a side effect of a GET request.
- Uses `Cache-Control: no-store` for account-specific results.

Illustrative response:

```json
{
  "schema_version": 1,
  "entitlements": [
    {
      "product_id": "software-os-center-premium",
      "status": "active",
      "valid_from": "2026-10-14T00:00:00Z",
      "valid_until": "2026-11-14T00:00:00Z"
    }
  ]
}
```

The example is a contract illustration, not a live endpoint or a real user's entitlement. An empty array means no active entitlement was found. Clients must fail closed when the endpoint is unavailable or the response is invalid.

## Purchase and grant invariants

1. **Server-owned pricing:** checkout accepts a stable product/price identifier, not an authoritative amount. The server loads the current price and currency from a versioned catalogue and calculates the payable amount.
2. **Authenticated ownership:** the purchase is bound to the verified token subject and tenant. Customer email is contact information, not account identity.
3. **Authoritative payment confirmation:** a redirect, query parameter, browser event, or client-reported status never grants access. The payment provider's server-to-server webhook or authenticated server-side transaction verification must confirm the expected transaction.
4. **Amount and currency match:** verified paid amount and currency must match the server-created order. A mismatch is quarantined for review, not granted.
5. **Idempotency:** provider event IDs and order IDs are persisted with unique constraints. Replayed callbacks must not create duplicate grants or extend expiry more than once.
6. **Explicit transaction states:** only a verified, settled transaction can grant access. Pending, failed, cancelled, reversed, disputed, and unverified/demo transactions cannot grant access.
7. **Durable ownership:** an entitlement record stores an immutable account subject, tenant, product ID, source transaction/order ID, status, validity interval, and audit timestamps. Enforce uniqueness for the relevant purchase/grant identity in the database.
8. **Revocation and refunds:** verified refunds, chargebacks, reversals, account suspension, and expiry must update access according to an explicit policy. Revocation must be auditable.
9. **Server-side enforcement:** every paid API operation checks entitlement server-side. Hiding a button or checking local storage is UX only, not authorization.
10. **Least privilege:** the entitlement service has no arbitrary filesystem, shell, installer, disk-formatting, or recovery-media privileges.

## Required implementation sequence

- [ ] Select one canonical payment service and document its authenticated identity contract.
- [ ] Confirm how verified token `sub` and tenant map to durable account records.
- [ ] Define a server-owned product/price catalogue with currency, amount, duration, and version.
- [ ] Add durable order and entitlement tables with foreign keys/unique constraints and migrations; do not rely on `create_all` alone for production schema evolution.
- [ ] Implement checkout creation using the authenticated account and server-owned price.
- [ ] Verify each supported provider's webhook signature and event semantics; reject unsigned callbacks and demo transactions.
- [ ] Implement replay-safe grant, renewal, refund, chargeback, expiry, and revocation transitions.
- [ ] Add tests for cross-account access, cross-tenant access, amount/currency mismatch, forged success redirect, duplicate webhook, out-of-order webhook, pending/demo payment, refund, expiry, and unavailable entitlement service.
- [ ] Enforce entitlements on server endpoints before connecting any paid UI.
- [ ] Complete a security review and test in a non-production environment before enabling checkout or releasing.

## API error and outage behavior

- Missing/invalid token: `401`.
- Authenticated account without the requested entitlement: `403`.
- Unknown product/price or invalid purchase input: `400` or `422`.
- Payment confirmation pending: report pending; do not grant access.
- Entitlement service/database unavailable: fail closed for paid operations and return a retryable server error. Do not silently fall back to browser state.
- Unauthorized cross-account or cross-tenant lookup: do not reveal another account's records.

## Desktop helper boundary

The existing Electron shell has `nodeIntegration: false`, `contextIsolation: true`, and `sandbox: true`. Preserve these defaults. Any future native helper must expose a small, explicit allow-list of typed operations; no generic command execution or unrestricted filesystem bridge. A website entitlement alone must never authorize destructive local operations.

## Release gate

This contract is satisfied only when the implementation, database migration, automated tests, and server-side enforcement are all present. Documentation, a passing frontend build, or a successful checkout redirect alone does not satisfy the gate.
