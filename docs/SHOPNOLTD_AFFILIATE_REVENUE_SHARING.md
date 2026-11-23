# Shopnoltd Affiliate Revenue Sharing

## Purpose

The affiliate marketplace is operated by Shopnoltd as the sole program intermediary. Authenticated Shopnoltd users browse Shopnoltd-managed tasks, generate unique tracking links, and review conversion status in their Shopnoltd account. Affmine's publisher relationship is with Shopnoltd; users do not need an Affmine account and must not be routed into direct Affmine support, account management, or communications. Shopnoltd manages user-facing task instructions, support, attribution presentation, commission calculations, and payout communication. Required advertiser/network tracking and legally or contractually required disclosures must remain accurate; this policy does not conceal traffic sources or bypass offer terms.

## Current implementation

- Active offers are listed from the API database, not from hard-coded marketing examples.
- Every click start creates a unique click record tied to the authenticated Shopnoltd user.
- Tracking destinations must use HTTPS.
- Offer country restrictions are enforced using the Cloudflare country header. Restricted offers fail closed when the country is unknown. Device restrictions are enforced from the request User-Agent against Affmine platform IDs (1 Windows, 2 Mac, 3 Android, 4 iOS, 5 other mobile).
- Admin offer management requires a platform-wide Keycloak realm role.
- Admins can create offers as drafts, set the user commission share, confirm whether incentive promotion is permitted, and activate/pause offers.
- User share is bounded to 0–90%; the platform retains at least 10%.
- A USD/BDT reference rate is read from the existing exchange service. If no current rate is available, the UI does not invent a BDT amount.
- User and admin summary endpoints report conversion states separately.

## Intermediary and user-communication policy

1. Shopnoltd is the user's sole operator and support channel for this program. User-facing pages, notifications, task instructions, earnings statements, and payout communications are provided by Shopnoltd.
2. Users are not asked to register with, contact, or open support cases with Affmine. Affmine publisher administration and reconciliation are handled by Shopnoltd.
3. Personal tracking IDs are used only for attribution and reconciliation. Share only the minimum data required by the network contract; do not send user passwords, Shopnoltd credentials, or unnecessary personal/contact data to Affmine.
4. Some offer destinations may be advertiser-operated. Do not promise that users will never see or interact with an advertiser's own landing page. Display material task conditions and required disclosures before a user starts.
5. Never misrepresent traffic, identity, incentive status, or the relationship to an advertiser/network. Activate an offer only after written confirmation that the exact incentivized task model and intended traffic source are allowed.

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

- GET /api/v1/affiliate/offers — active offers eligible for the requester's country and detected device platform.
- POST /api/v1/affiliate/offers/{offer_id}/start — create a click and return the user's personal network tracking URL.
- GET /api/v1/affiliate/me/summary — user's click and conversion summary.
- GET /api/v1/affiliate/rates/usd-bdt — live USD/BDT reference rate.
- POST /api/v1/affiliate/admin/sync-affmine — fetch active campaigns from Affmine Publisher API v1.0 and import/update them as Drafts.
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


## Earnings sandbox (test-only)

- Sandbox endpoints are disabled by default and return 404 unless the isolated test environment explicitly sets `AFFILIATE_SANDBOX_ENABLED=true`. Do not enable this flag in production.
- Sandbox conversions are stored in the separate `shopnoltd_affiliate_sandbox_conversions` table, never in the live network conversion table.
- Authenticated users can create mock conversions with a USD payout from 0.01 to 1,000 and a user share from 0% to 90%; the remainder is the simulated Shopnoltd share.
- The user dashboard labels all values as simulated and non-withdrawable. The admin dashboard reports sandbox totals separately.
- Users can delete only their own sandbox records. This does not alter real conversions, payments, or wallet balances.
- Sandbox routes: `POST /api/v1/affiliate/sandbox/simulate`, `GET /api/v1/affiliate/sandbox/me/summary`, `DELETE /api/v1/affiliate/sandbox/me/reset`, and platform-admin-only `GET /api/v1/affiliate/sandbox/admin/summary`.
- Sandbox results are never counted as Affmine conversions, real revenue, payable earnings, or wallet funds. Do not present simulated earnings as actual income.
- This is application-level test functionality, not a substitute for Affmine's own sandbox or written permission for live incentivized campaigns.


## Affmine Publisher API v1.0 campaign import

- Configure `AFFMINE_AFF_ID` and `AFFMINE_API_KEY` only in the API service's server-side secret store. Never put either credential in React, browser storage, source control, logs, or a public URL.
- The admin-only sync endpoint calls `https://network.affmine.com/api/v1/getCampaigns` with only the documented Publisher API v1.0 parameters: `aff_id`, `api_key`, and `format=json`. It imports the campaigns returned by the feed without inventing undocumented status, GEO, platform, incentive, or pagination filters. If the feed later documents pagination, add it only with a confirmed cursor/offset contract.
- New campaigns are inserted as Draft with incentive permission disabled. Sync does not activate offers or enable incentive traffic. Existing admin eligibility/status decisions are preserved.
- Campaigns with valid three-letter ISO currency codes and positive payout values are imported with the original network currency preserved. Offer cards format payouts and estimated user shares in that currency; they are not silently converted to USD. Invalid currency codes are counted and skipped. Conversion summaries and USD/BDT reference estimates remain USD-only until the network postback and FX contract are verified.
- Missing or non-HTTPS campaign URLs are retained as empty tracking URLs; activation and click-start fail closed until a valid HTTPS URL and confirmed click-sub-ID macro are configured.
- Affmine's allowed_platform and incentive values are stored as network metadata. An empty/unrestricted allowed_platform value is normalized to all five documented platform IDs; platform eligibility is applied to offer listing and click start. The network incentive flag is not proof of campaign-level approval for Shopnoltd's exact reward/task model.
- The sample Affiliate ID/API key in the supplied documentation must not be used as account credentials. Use the actual account-issued credentials only in the server-side secret store.
- Sync endpoint: `POST /api/v1/affiliate/admin/sync-affmine`.

## Affmine campaign application automation boundary

- The currently supplied Affmine Publisher API v1.0 specification documents the `getCampaigns` feed. It does not document a campaign-application or `Apply to Run` endpoint, nor an API field that reliably proves campaign-level approval for this publisher.
- Therefore, the Shopnoltd sync job may import and classify feed records, but it must not submit guessed requests, simulate dashboard clicks, or treat feed visibility as campaign approval.
- Campaigns are never auto-activated solely because they appear in the feed. New records remain Draft and reward-disabled until campaign-level permission, the exact Shopnoltd incentivized task model, traffic source, click macro, and tracking terms are confirmed.
- If Affmine supplies an authenticated application endpoint and documents its request, response, approval-state, and rate-limit contract in writing, implement it behind a feature flag with idempotency, audit logging, and explicit publisher authorization. Until then, any required application is handled through Affmine's publisher dashboard.
- Ask Affmine support to confirm in writing: (1) whether this publisher account requires per-campaign applications; (2) whether API-based campaign applications are supported and provide the official endpoint/schema; (3) whether Shopnoltd's worldwide user-reward/offerwall model is permitted, and which campaigns permit incentivized traffic; and (4) how approved/rejected/pending campaign states are exposed in the feed.
- This is an intentional compliance boundary, not an incomplete auto-click workaround. Do not use browser automation to submit applications or bypass campaign review.
