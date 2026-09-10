# Shopnoltd

Shopnoltd is a multi-service platform with a React web portal, authenticated FastAPI API layer, Keycloak identity, financial services, domains, AI, social/blog, Work, ShopnoltdCollect/Android Cloud, VPN/device services, storage, and Kubernetes/GitOps deployment.

**Source of truth:** GitHub `main`. Production delivery is GitHub Actions → GHCR → ArgoCD/k3s. Browser business operations use the unified `https://api.shopnoltd.dpdns.org` origin; internal service DNS and credentials remain server-side.

## Functional surface

| Area | Browser capability | Security boundary |
|---|---|---|
| Authentication | Keycloak direct login, refresh/session handling, role-protected admin routes; Google/GitHub broker support when configured in Keycloak | Keycloak/OIDC |
| Social | Feed, Discover, posts, direct post URLs, likes, comments/replies, shares, follows, views, notifications | social-service |
| Blog | Public published posts; user/admin draft, edit, publish/unpublish, delete, cover media | social-service + tenant scope |
| Work | Browse, create, configure task links/media, publish/close, accept, persisted Before/Start/Working/End lifecycle, server-time/watch verification, evidence, submission and approval | api-service + financial ledger |
| Wallet/finance | Wallets, ledger, transactions, checkout, gateway catalog, FX quote/conversion and protected settlement | payment/billing/exchange services |
| Domains | Paid-domain availability/registration/renewal and authenticated domain management | domain-service + registrar |
| Free domains | Tenant-scoped `*.shopnoltd.dpdns.org` provisioning and deactivation | freedomain-service |
| AI | Authenticated inference and active model catalog; provider/model administration for authorized admins | ai-platform |
| Database control | Service-owned inspection, search, analysis, export, PDF reporting, and guarded content CRUD/import | owning service policies; no unrestricted SQL |
| Storage | Authenticated object mutations through the unified API; published public assets remain cacheable | storage-service |
| Android/Collect | ShopnoltdCollect branding and Android Cloud/device workflows where the corresponding deployment is enabled | android-cloud/device services |
| VPN/devices | Authenticated device/VPN lifecycle and browser connection entry points | vpn/device services |

## Financial gateway policy

The billing engine contains adapters for Stripe, PayPal, Razorpay, SSLCommerz, bKash, Nagad, Moneybag and crypto/NOWPayments, with Payoneer handled as a payout integration. Google Pay is treated as a payment-method capability of a compatible processor (for example Stripe), not as a fabricated independent processor. Rocket/Payeer/manual methods remain explicitly manual unless a verified online provider integration is configured.

A gateway is shown as **live** only when its required runtime credentials/configuration and provider contract are present. Secrets are never committed to Git. Repeated callbacks must be idempotent and wallet credit must happen exactly once.

## Database control policy

Database operations are deliberately **service-owned**, not an unrestricted browser SQL console. The admin UI provides the requested operational lifecycle where the owning service supports it: check/inspect, add, update/modify, upsert/merge, delete, replace-row imports, save, import/export, analysis and reports. Financial, identity, audit and security records remain protected behind their domain APIs so an accidental generic edit cannot create or destroy money or credentials.

Blog data additionally supports tenant-scoped CRUD, draft/publish/unpublish, transactional CSV/JSON/XLSX import/export, validation, audit records and PDF reporting. Analysis charts are responsive and resolution-independent for HD/4K displays; CSS perspective is used for a lightweight 3D presentation without pretending that a 2D report is a true 3D data cube.

## Domains

- `shopnoltd.com` is a paid-domain/registrar workflow and must be registered through the configured registrar integration.
- `a.shopnoltd.dpdns.org` is a free tenant subdomain under the Shopnoltd parent zone; it is not treated as an independently registrable domain.
- Paid-domain registration and renewal remain service-owned and billing-aware.

## Authentication

All protected portal pages use the same Keycloak access token. Direct login and configured social brokers are handled by Keycloak so billing, payment, exchange, AI, domains, social/blog and Work do not maintain separate browser identities.

Google/Gmail and GitHub login buttons cannot be made operational by frontend code alone: the corresponding Keycloak Identity Provider must have valid provider credentials and callback configuration in the deployment runtime.

## Work accounting

Work rewards are server-authoritative. Before Work evidence is required before Start; Work elapsed time is measured server-side; watch credit requires plausible playback progress and visibility/readiness; social actions are evidence-only unless independently verified; required evidence/watch gates submission; and approved earnings use the same financial ledger rather than a second wallet.

## CI/CD and release gate

Every main push/PR is checked for Kubernetes rendering, required frontend routes, financial/Work contracts and the required API/browser facades. Deployed main changes wait for the self-hosted k3s GitOps reconciliation and then run public endpoint smoke tests. A release is not considered fully live merely because a UI component or adapter exists; runtime credentials and end-to-end verification are required.

See `docs/FULL-FUNCTIONALITY-GATE.md` and `docs/OBSERVABILITY-RELEASE-GATE.md` for the executable release contract.

## Important runtime rule

Do not commit API keys, webhook secrets, passwords, enrollment tokens, kubeconfigs or test credentials. The Moneybag credentials and other secrets pasted into chat should be treated as exposed and rotated/replaced in the provider and Kubernetes runtime configuration before production use.
