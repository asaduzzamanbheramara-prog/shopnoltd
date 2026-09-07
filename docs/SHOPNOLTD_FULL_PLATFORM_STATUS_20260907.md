# ShopnoltdToolbox platform status — 2026-09-07

This document records what is implemented in the integration branch and what is deliberately not claimed as complete.

## Financial system

- `billing-engine` remains the wallet and ledger authority.
- Unified API exposes capabilities, wallet, ledger, transactions, exchange, and checkout contracts.
- Gateway availability is separated from catalogue/provider support/configuration.
- Checkout can now receive `base_amount` + `base_currency`; the API facade obtains the settlement conversion server-side and rejects a mismatching browser-provided settlement amount.
- Browser conversion is display-only; it is not financial authority.
- Catalogue-only gateways remain visible as supported/planned providers but cannot be selected as live checkout adapters.
- Payout providers remain separate from customer checkout gateways.

## Gateway coverage

Implemented adapters remain available for the existing supported gateways. The gateway catalogue also retains future providers without falsely reporting them as implemented. Payment methods, card networks, bank rails, wallets and crypto rails are modeled as capabilities rather than incorrectly treating every payment rail as a processor.

## Domain system

- Domain self-service routes are authenticated through the verified identity subject.
- Registration/renewal routes no longer fabricate successful registration or renewal.
- A domain purchase must follow: registrar availability/price → authoritative Shopnoltd price → FX conversion → compatible gateway checkout → verified payment → registrar operation → persisted domain state.
- The registrar adapter layer still requires a complete production-grade registration implementation before an active domain can honestly be returned.

## Device system

The central device model is:

`Identity → Enrollment → Ownership → Permissions → Capabilities → Automation → Events → Health → Audit → Revocation`

Supported device contract entries include Windows, Linux, macOS and Android ShopnoltdCollect. Device actions are capability-checked and allowlisted; arbitrary remote command execution is prohibited.

## ShopnoltdCollect Android

ShopnoltdCollect remains based on the existing Kobo/ODK Collect engine and retains its collection capabilities. A Shopnoltd platform contract has been added in the Android repository with a stable product/device type and capability declaration. The central main repository must point its git submodule at the verified Android commit as a separate repository integration step; the Android commit is not silently rewritten into the main repository.

## Automation

A versioned automation contract now defines schedules, webhooks, payment/domain/wallet/device/collection/exchange triggers, allowlisted actions, retries, dead-letter handling, tenant isolation, capability checks, audit requirements, and financial safeguards. The contract is not permission to execute arbitrary commands.

## Release gate

Do not merge or deploy the branch solely because these contracts exist. Required release evidence is:

1. API-service syntax/unit checks.
2. Authenticated capabilities endpoint check.
3. Wallet and ledger checks for every advertised currency.
4. Currency × gateway compatibility checks.
5. Checkout validation/error-code checks.
6. Sandbox success verification for every configured gateway.
7. FX quote/convert verification.
8. Domain registrar sandbox checks and verified-payment-to-registration flow.
9. Android build and instrumentation/unit checks.
10. Device enrollment, heartbeat, capability, revoke and tenant-isolation checks.
11. Automation retry/idempotency/audit checks.
12. Kubernetes rollout and live health/readiness checks.

Until those gates pass, the system should report `configured`, `implemented`, `available`, `healthy`, and `verified` separately rather than collapsing them into one green status.
