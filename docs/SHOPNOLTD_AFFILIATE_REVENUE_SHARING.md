# Shopnoltd Affiliate Revenue Sharing

## Purpose

The affiliate marketplace lets authenticated Shopnoltd users browse approved offers, generate unique tracking links, and review conversion status. Shopnoltd retains a configurable platform share of each network-confirmed payout.

## Current implementation

- Active offers are listed from the API database, not from hard-coded marketing examples.
- Every click start creates a unique click record tied to the authenticated Shopnoltd user.
- Tracking destinations must use HTTPS.
- Offer country restrictions are enforced using the Cloudflare country header. Restricted offers fail closed when the country is unknown.
- Admin offer management requires a platform-wide Keycloak realm role.
- Admins can create offers as drafts, set the user commission share, confirm whether incentive promotion is permitted, and activate/pause offers.
- User share is bounded to 0–90%; the platform retains at least 10%.
- A USD/BDT reference rate is read from the existing exchange service. If no current rate is available, the UI does not invent a BDT amount.
- User and admin summary endpoints report conversion states separately.

## Revenue and settlement rules

1. A click is attribution evidence only. It is not a commission.
2. A network conversion callback must be authenticated and mapped to the exact Affmine macros before it can be enabled.
3. A conversion starts as pending. Approval alone is not cash received.
4. Approved but unpaid network conversions remain approved_unpaid; they are not spendable wallet funds.
5. Network payout must be reconciled before user commission is marked payable.
6. Wallet credit must be idempotent and performed by the payment service's validated financial API, never by direct database writes from the API service.
7. Rejections and reversals must be recorded and must reverse any unpaid commission. Paid reversals require an auditable recovery/negative-balance policy.
8. Commission percentage and FX rate are snapshotted per conversion. Later policy/rate changes must not rewrite history.

## API routes

- GET /api/v1/affiliate/offers — active offers eligible for the requester's country.
- POST /api/v1/affiliate/offers/{offer_id}/start — create a click and return the user's personal network tracking URL.
- GET /api/v1/affiliate/me/summary — user's click and conversion summary.
- GET /api/v1/affiliate/rates/usd-bdt — live USD/BDT reference rate.
- GET /api/v1/affiliate/admin/offers — admin offer inventory.
- POST /api/v1/affiliate/admin/offers — add a draft offer.
- PATCH /api/v1/affiliate/admin/offers/{offer_id}/commission — set future user/platform split.
- PATCH /api/v1/affiliate/admin/offers/{offer_id}/eligibility — record incentive permission; revoking it pauses the offer.
- POST /api/v1/affiliate/admin/offers/{offer_id}/activate and deactivate — control availability.
- GET /api/v1/affiliate/admin/summary — admin conversion and revenue split summary.

## Required Affmine setup before live earnings

Affmine must confirm the publisher API and the exact click-subparameter, conversion postback URL, secure-code/token mechanism, payout amount macro, transaction ID macro, status mapping, currency, and payout reconciliation/export. Public documentation for other Affise-family products is not proof that the Affmine account uses identical macros.

Until that is confirmed, the conversion postback intentionally returns 503 and no commission is credited to any wallet. Do not enable incentives for offers whose advertiser terms prohibit them.

## Deployment gate

The feature branch and PR must pass API tests, web build, security scans, and release validation. Production database migration, secret configuration, deployment, and wallet-credit activation remain separate gated steps.
