# Shopnoltd Full Functionality Gate

This checklist is the release contract for Shopnoltd/ShopnoltdToolbox. A capability is only called **live** after its real runtime path is tested. An adapter or UI alone is not proof of live operation.

## Product

- [ ] ShopnoltdToolbox public portal loads and navigation works.
- [ ] ShopnoltdCollect branding and authenticated access work.
- [ ] Admin and normal-user permissions are enforced server-side.
- [ ] Direct Keycloak login works.
- [ ] Google/Gmail broker login works.
- [ ] GitHub broker login works.
- [ ] The same authenticated identity works across portal, billing, payment, exchange, AI, domains, social/blog, and other protected services.

## Blog

- [ ] Admin can create a draft.
- [ ] Admin can edit a draft.
- [ ] Admin can publish/unpublish.
- [ ] Admin can delete.
- [ ] Public users can read published posts.
- [ ] Draft/unpublished posts are not public.
- [ ] Tenant isolation prevents cross-tenant authoring/read access.

## Domains

- [ ] `shopnoltd.com` availability/pricing/registration lifecycle works through the configured registrar sandbox.
- [ ] Renewal works and is idempotent.
- [ ] Registrar failure refunds exactly once.
- [ ] Recovery/reconciliation handles a crash after wallet charge but before registrar completion.
- [ ] `a.shopnoltd.dpdns.org` is provisioned as a DNS/subdomain tenant, not submitted as an independent registrable domain.

## Billing, payment, wallets, and FX

- [ ] Wallet can be read by authenticated user and selected currency.
- [ ] Wallet ledger and transactions are consistent.
- [ ] Deposit/checkouts accept the requested amount without hidden hardcoded amount assumptions.
- [ ] Currency is request-driven and validated against gateway capability.
- [ ] FX rate and conversion work for supported currency pairs.
- [ ] Repeated checkout/webhook delivery cannot double-credit a wallet.
- [ ] Failed/cancelled payments do not credit the wallet.
- [ ] Refund/adjustment operations have stable idempotency references.

## Gateway matrix

| Gateway | Integration | Checkout | Webhook | Verification | Payout | Currency source |
|---|---|---:|---:|---:|---:|---|
| Stripe | native | yes | yes | yes | no | gateway catalog |
| PayPal | native | yes | yes | yes | no | gateway catalog |
| Binance Pay | native | yes | yes | yes | no | gateway catalog |
| Razorpay | native | yes | yes | yes | no | gateway catalog |
| SSLCommerz | native | yes | yes | yes | no | gateway catalog |
| bKash | native | yes | yes | yes | no | gateway catalog |
| Nagad | native | yes | yes | yes | no | gateway catalog |
| Moneybag | native | yes | yes | yes | no | BDT sandbox contract |
| Crypto/NOWPayments | native | yes | yes | yes | provider-dependent | live provider catalog |
| Payoneer | native | no | provider-dependent | provider-dependent | yes | payout contract |
| Payeer | manual | manual | no native claim | manual | no | explicit manual state |
| Rocket | manual | manual | no native claim | manual | no | BDT/manual |

Google Pay is represented as a Stripe payment method/wallet capability, not as a fabricated independent processor.

## Moneybag sandbox

The expected path is:

`portal/API checkout -> Moneybag hosted checkout -> signed IPN -> payment verification -> exactly-once wallet credit -> ledger/transaction audit`

Test all of:

- success
- failed
- cancelled
- duplicate webhook
- delayed webhook
- invalid signature
- mismatched amount
- mismatched currency
- unknown transaction
- verification not yet successful

The Moneybag dashboard webhook must target the public Shopnoltd API relay configured for the deployment. Secrets remain Kubernetes runtime configuration only.

## AI

- [ ] Provider/model registry works.
- [ ] OpenAI works when configured.
- [ ] Anthropic works when configured.
- [ ] Ollama works when configured.
- [ ] Google/Gemini works when configured.
- [ ] Azure OpenAI/custom provider works when configured.
- [ ] Model activation and fallback work.
- [ ] Unconfigured providers fail clearly instead of returning fabricated output.

## Operational rule

Inactive but implemented integrations remain visible in the capability catalog with their actual state. They are activated when valid credentials/configuration exist. Unsupported operations remain explicitly unavailable; no fake success, demo transaction, or simulated money movement is permitted.

Branding/name-letter cleanup happens only after this functionality gate is green.
