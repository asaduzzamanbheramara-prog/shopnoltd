# Shopnoltd Ad Network Architecture

## Purpose
Shopnoltd will operate its own advertising network connecting approved advertisers with approved publishers. This is separate from Google AdSense. Advertisers fund campaigns in Shopnoltd; publishers register websites and ad inventory; Shopnoltd's ad server selects and serves eligible creatives and records delivery and billing events.

## Roles
- Advertiser: organization or business that creates campaigns, creatives, targeting and budget.
- Publisher: website/app owner that verifies properties, creates ad zones and installs Shopnoltd ad tags.
- Platform admin: approves advertisers/publishers/properties/creatives, controls policy, pricing, fraud and payouts.
- Ad server: evaluates inventory, campaign eligibility, pacing, frequency caps, targeting and delivery.
- Financial ledger: existing Shopnoltd payment/wallet system remains the source of truth for advertiser charges and publisher earnings.

## Core entities
- Advertiser: advertiser_accounts, advertiser_users, campaigns, line_items, creatives, creative_assets, campaign_targeting, campaign_budgets, campaign_delivery, campaign_events.
- Publisher: publisher_accounts, publisher_users, publisher_sites, publisher_site_verifications, ad_zones, ad_zone_sizes, publisher_earnings, publisher_payouts.
- Delivery/trust: ad_requests, ad_impressions, ad_clicks, ad_conversions, frequency_counters, fraud_events, blocked_domains, blocked_creatives, supply_chain_events.
Every financial event must be linked to immutable delivery/event identifiers so repeated requests cannot double-charge or double-credit.

## Delivery flow
1. Publisher registers a site.
2. Shopnoltd verifies ownership before inventory is eligible.
3. Publisher creates an ad zone and receives a Shopnoltd tag.
4. Advertiser creates a campaign, line item and creative.
5. Advertiser funds the campaign through the existing Shopnoltd financial system.
6. Browser loads the publisher tag.
7. Ad server validates site, zone, consent/privacy state and request constraints.
8. Ad server selects eligible campaigns using targeting, budget, pacing and frequency rules.
9. Ad response contains the creative plus a signed delivery identifier.
10. Impression/click events are recorded idempotently.
11. Advertiser reporting and publisher earnings are derived from the same delivery ledger.
12. Approved publisher earnings become payable through the existing payout workflow.

## Initial pricing model
Support CPM, CPC, CPA and flat sponsorship/fixed placement in the data model, even if only one is enabled initially.
Do not mix advertiser billing and publisher revenue as independently editable balances. Calculate publisher share from authoritative delivery/billing records and post financial entries through the existing ledger.

## Targeting
Phase 1: site/domain, ad zone, country/region, language, device category, browser/OS category, schedule, campaign start/end, frequency cap, contextual category, minimum/maximum CPM/CPC constraints.
Avoid collecting unnecessary personal data. Consent and privacy controls must be respected before optional audience processing.

## Supply-chain transparency
Shopnoltd should support an ads.txt endpoint/integration and a sellers.json representation. IAB Tech Lab describes ads.txt as a public declaration of authorized digital sellers; version 1.1 adds OWNERDOMAIN and MANAGERDOMAIN. Shopnoltd should expose its seller identity consistently and generate publisher-specific authorized-seller records.

## Security requirements
- Publisher-site ownership verification is mandatory before serving paid campaigns.
- Ad tags must use non-guessable public publisher/zone identifiers.
- Impression and click endpoints must use signed, short-lived delivery tokens.
- Click redirects must prevent open-redirect abuse.
- Campaign budgets must be enforced transactionally/idempotently.
- Advertiser, publisher and admin roles must remain isolated.
- Admin moderation actions must be audited.
- Financial ledger records must not be editable through generic CRUD.
- Creative upload must validate MIME type, size, dimensions and active content policy.
- Destination URLs must be validated and normalized.
- Rate limiting and bot/fraud signals must be applied to delivery and click endpoints.

## Shopnoltd integration boundaries
- Keycloak / existing authentication for identity and roles.
- api-service as the authenticated public API facade where appropriate.
- Existing payment-service / wallet / billing ledger for advertiser funding and publisher payouts.
- Existing analytics/event infrastructure for reporting where its semantics are sufficient.
- GitOps/Kubernetes for deployment.
- A dedicated ad-service is preferred over extending the donation-oriented foundation-service campaign model.

## API surface (target)
### Advertiser
- POST /api/v1/ads/advertisers
- GET /api/v1/ads/advertisers/me
- POST /api/v1/ads/campaigns
- GET /api/v1/ads/campaigns
- GET /api/v1/ads/campaigns/{id}
- PATCH /api/v1/ads/campaigns/{id}
- POST /api/v1/ads/campaigns/{id}/line-items
- POST /api/v1/ads/creatives
- POST /api/v1/ads/campaigns/{id}/fund
- GET /api/v1/ads/reports/advertiser
### Publisher
- POST /api/v1/ads/publishers
- POST /api/v1/ads/publishers/sites
- POST /api/v1/ads/publishers/sites/{id}/verify
- POST /api/v1/ads/publishers/sites/{id}/zones
- GET /api/v1/ads/publishers/sites/{id}/tag/{zone_id}
- GET /api/v1/ads/reports/publisher
- GET /api/v1/ads/payouts
### Public delivery
- POST /api/v1/ads/serve
- GET /api/v1/ads/click/{delivery_token}
- POST /api/v1/ads/event
These delivery endpoints should not require normal user login; they must authenticate inventory using registered publisher/site/zone identity plus signed delivery controls.
### Admin
- advertiser approval/suspension
- publisher/site approval/suspension
- creative review
- campaign pause/resume
- fraud review
- pricing/revenue-share configuration
- supply-chain records
- reporting/audit

## Rollout gates
1. Repository/service audit.
2. Add database schema and migration.
3. Implement ad-service read/write API with role isolation.
4. Implement public ad-serving endpoint and idempotent event ledger.
5. Add advertiser/publisher dashboard pages.
6. Add admin moderation/reporting.
7. Add ad tag generator and publisher verification.
8. Add ads.txt/sellers.json support.
9. Add automated unit/API/security tests.
10. Build with GitHub Actions/GHCR.
11. Deploy through Argo CD.
12. Run advertiser -> campaign -> publisher -> serve -> click -> report -> payout functional test before declaring the network operational.

## Important boundary
Shopnoltd cannot inject advertisements into arbitrary third-party websites without their participation. A publisher must authorize Shopnoltd inventory and install/use the Shopnoltd ad tag or another approved integration.