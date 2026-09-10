# Shopnoltd Full Functionality Gate

This is the release contract for Shopnoltd/ShopnoltdToolbox. **Implemented code is not the same as verified live functionality.** A capability is marked live only after its real runtime path succeeds with the deployment's current configuration.

## 1. Browser and API contract

- [ ] Root portal loads on desktop/tablet/mobile browsers.
- [ ] Every primary navigation button resolves to a real route.
- [ ] Direct URLs remain functional after refresh (SPA fallback + ingress).
- [ ] Protected routes preserve authentication and return users to their requested destination after login.
- [ ] Browser business mutations use `api.shopnoltd.dpdns.org`; internal payment/domain/AI/storage service hosts are not required by the browser.
- [ ] API, web and service CORS policies allow the supported Shopnoltd origins only.

## 2. Authentication and authorization

- [ ] Direct Keycloak login works.
- [ ] Access-token refresh works without duplicating identities.
- [ ] Logout clears local session state and prevents protected API reuse.
- [ ] Google/Gmail broker login works when the Keycloak provider is configured.
- [ ] GitHub broker login works when the Keycloak provider is configured.
- [ ] Admin and normal-user permissions are enforced server-side.
- [ ] The same authenticated identity works across portal, billing, payment, exchange, AI, domains, social/blog, Work and protected tools.

## 3. Social

- [ ] Feed and Discover load real data.
- [ ] Create/edit/delete post works according to ownership policy.
- [ ] Direct post URLs resolve.
- [ ] Like/unlike and reactions persist.
- [ ] Comments/replies persist.
- [ ] Shares/reposts persist.
- [ ] Follow/unfollow persists.
- [ ] View/watch tracking persists without turning self-reported actions into automatic rewards.
- [ ] Notifications are generated and displayed.
- [ ] Privacy/moderation rules are enforced by the service.

## 4. Blog

- [ ] Admin can create a draft.
- [ ] User/author can create and edit their permitted posts.
- [ ] Admin/authorized author can publish/unpublish.
- [ ] Authorized user can delete their permitted draft/content.
- [ ] Public users can read published posts.
- [ ] Draft/unpublished posts are not public.
- [ ] Cover image upload/delete uses authenticated storage mutation through the unified API.
- [ ] Tenant isolation prevents cross-tenant authoring/read access.

## 5. Work

- [ ] Work can be created with title, requirements, link/media, reward and currency.
- [ ] Currency is selected from the supported catalog and reward conversion uses a live FX quote.
- [ ] Total, completed, active and remaining task/amount counters are consistent.
- [ ] Creator can edit, publish and close work.
- [ ] Worker can open a direct Work URL and accept a published task.
- [ ] Before Work evidence is required before Start Work.
- [ ] Start/Working/End lifecycle survives browser refresh/resume.
- [ ] Server time, not client-submitted duration, controls elapsed work time.
- [ ] Watch credit requires plausible playback progression and required evidence.
- [ ] Submission is blocked until the required verification gates are satisfied.
- [ ] Employer approval/rejection is authenticated and audited.
- [ ] Approved earnings use the existing immutable financial ledger; no second wallet is created.

## 6. Wallet, billing, payment and FX

- [ ] Wallet can be read by an authenticated user in a selected supported currency.
- [ ] Ledger and transaction history reconcile.
- [ ] Checkout amount is derived from the selected plan/product and live FX quote; no hidden hardcoded payment amount is accepted.
- [ ] Currency and gateway compatibility are validated server-side.
- [ ] Exchange conversion debits source and credits destination atomically.
- [ ] Every money movement has an immutable ledger entry and idempotency reference.
- [ ] Repeated checkout/webhook delivery cannot double-credit a wallet.
- [ ] Failed/cancelled payments do not credit a wallet.
- [ ] Withdrawal reserves/debits funds safely and is auditable.
- [ ] Refund/adjustment operations are idempotent and auditable.

### Gateway matrix

| Gateway/method | Repository adapter | Live only when configured | Notes |
|---|---:|---:|---|
| Stripe | yes | yes | Includes compatible wallet methods such as Google Pay when enabled by Stripe/account/browser |
| PayPal | yes | yes | Provider credentials + webhook configuration required |
| Razorpay | yes | yes | Provider credentials + webhook configuration required |
| SSLCommerz | yes | yes | Sandbox/live mode must match runtime configuration |
| bKash | yes | yes | Provider credentials + callback/verification required |
| Nagad | yes | yes | Provider credentials + callback/verification required |
| Moneybag | yes | yes | Sandbox/live contract and signed IPN verification required |
| Crypto/NOWPayments | yes | yes | Provider-supported assets/currencies only |
| Payoneer | payout | yes | Payout integration, not a customer checkout processor |
| Rocket | manual unless verified adapter exists | no fabricated online claim | Must remain explicitly manual until a verified online integration is present |
| Payeer | manual unless verified adapter exists | no fabricated online claim | Must remain explicitly manual until a verified online integration is present |

## 7. Moneybag sandbox verification

Expected path:

`portal -> unified API checkout -> Moneybag hosted checkout -> signed IPN -> verification -> exactly-once wallet credit -> immutable ledger/audit`

Verify success, failure, cancellation, duplicate callback, delayed callback, invalid signature, amount mismatch, currency mismatch, unknown transaction and not-yet-verified payment. Runtime secrets remain outside Git.

## 8. Domains

- [ ] `shopnoltd.com` availability/pricing/registration lifecycle works through the configured registrar sandbox/live mode.
- [ ] Registration charge and registrar order are reconciled safely.
- [ ] Renewal is idempotent.
- [ ] Registrar failure does not leave an incorrectly charged wallet.
- [ ] Crash recovery reconciles the state after wallet charge but before registrar completion.
- [ ] Authenticated domain management lists the current user's paid domains.
- [ ] `a.shopnoltd.dpdns.org` is provisioned as a tenant DNS/subdomain record, not as an independently registrable domain.
- [ ] Free-domain ownership/isolation is enforced server-side.

## 9. AI

- [ ] Active model catalog loads through the unified API.
- [ ] Inference works with the configured default model.
- [ ] OpenAI works when configured.
- [ ] Anthropic works when configured.
- [ ] Ollama works when configured.
- [ ] Google/Gemini works when configured.
- [ ] Azure OpenAI/custom provider works when configured.
- [ ] Provider/model admin CRUD and activation are role-protected.
- [ ] Fallback/priority behavior works.
- [ ] Unconfigured providers fail clearly; no fabricated output is returned.

## 10. Database control plane

- [ ] Admin database inventory loads through the unified API.
- [ ] Tables/entities can be inspected and searched where their owning service exposes that capability.
- [ ] Analysis statistics are available.
- [ ] CSV/JSON/XLSX export works where supported.
- [ ] PDF reports work where supported.
- [ ] Blog/content data supports validated add, update/modify, upsert/merge, delete, replace-rows import, save and publish/unpublish.
- [ ] Import is previewed/validated before commit.
- [ ] Destructive imports/deletes require explicit confirmation.
- [ ] Database changes create audit records where the owning service supports them.
- [ ] Financial, identity, audit and security stores do **not** expose unrestricted generic SQL/CRUD from the browser.
- [ ] Analysis visualization is responsive and resolution-independent for HD/4K displays; 3D presentation is visual only and does not bypass data authorization.
- [ ] Backup/export and restore procedures are tested without committing secrets.

## 11. ShopnoltdCollect, Android Cloud, devices and VPN

- [ ] ShopnoltdCollect branding is present and no old product branding is introduced.
- [ ] APK/download links resolve to the intended Shopnoltd artifacts.
- [ ] Android Cloud launches an authenticated interactive device when enabled.
- [ ] Device registry supports Windows/Linux/macOS/Android/iPhone/iPad/browser entries according to implemented agent capability.
- [ ] Device online/last-seen/local/public/VPN metadata is displayed only to authorized users.
- [ ] VPN enrollment/connect/disconnect is authenticated and auditable.
- [ ] No enrollment/admin tokens are committed to Git or rendered into public frontend code.

## 12. Infrastructure and GitOps

- [ ] Kubernetes manifests render successfully with kustomize.
- [ ] Required Deployments/Services/Ingresses/NetworkPolicies/probes are present for the active platform surface.
- [ ] Shared PostgreSQL/Redis remain healthy.
- [ ] ArgoCD reconciles the main branch revision successfully.
- [ ] Only affected services are rebuilt when possible.
- [ ] GHCR image promotion succeeds.
- [ ] Rollout status and API readiness are verified after deployment.
- [ ] Public smoke tests cover root, API, auth, billing, payment, exchange, domain, AI, social, devices, Android Cloud, chat and VPN entry points.

## 13. Operational rule

Inactive but implemented integrations remain visible with their **actual** configuration state. They are activated only when valid credentials/provider configuration exists. Unsupported operations stay explicitly unavailable. Never report fake payment success, fake registration, fake AI output, fake device connectivity or fake database writes.

A release is **fully functional** only when implementation checks, deployment reconciliation and real runtime verification all pass.