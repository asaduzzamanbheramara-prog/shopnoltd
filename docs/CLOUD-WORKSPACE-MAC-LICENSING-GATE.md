# Shopnoltd Cloud Workspace: Mac licensing and billing gates

## Product decision

Shopnoltd Cloud Workspace is the common customer entry point for cloud device environments.

- Browser Code Workspace: existing authenticated Shopnoltd app workspace. It is a coding workspace, not a full Linux desktop.
- Android Cloud: existing browser-based Android emulator service.
- Mac Cloud: planned subscription service with two separate intended use cases:
  - Developer Workspace: Xcode, Swift development, builds and automated testing.
  - General Mac Desktop: ordinary macOS desktop applications and browsing.
- Both Mac use cases must run on eligible Apple-branded Mac hardware. A Linux container or a macOS-themed desktop is not a macOS substitute.

## Current implementation and truthful availability

- Customer entry point: `/cloud`.
- Existing Code Workspace: `/app?panel=code`; uses existing app environment and access controls.
- Existing Android workspace: `/android-cloud`.
- Android controller configuration currently sets `ANDROID_CLOUD_MAX_SESSIONS=1`.
- Android emulator data currently uses a session-local Kubernetes `emptyDir`; it is temporary and must not be advertised as persistent user storage.
- A Cloud-specific free-session quota, Cloud product checkout, server-side Cloud entitlement, usage meter, and provider invoice/settlement ledger are not implemented by the current UI PR.
- General Shopnoltd checkout and wallet functionality are not proof that a Cloud order or Cloud entitlement exists. Do not accept or represent a generic payment as a Cloud subscription.
- Mac Cloud is unavailable. No Mac host provisioning, Mac session API, Mac billing entitlement, or Mac runtime is enabled.

## Free and paid service policy

1. Cloud Workspace discovery/browsing is free.
2. Existing Code Workspace and Android Cloud remain governed by their current account, session, capacity and access controls. Do not promise a new free quota or unlimited sessions until an enforceable backend quota exists.
3. Do not add Kasm, Guacamole, Android emulator replicas, or other new compute workloads to the current cluster without a measured capacity review. Software licensing being free does not make compute, storage, bandwidth or operations free.
4. Any published paid Cloud plan must disclose platform, price, currency, billing period/usage unit, limits, storage/retention, cancellation and refund terms before checkout.
5. The customer pays Shopnoltd first. Payment must be verified server-side and linked to a unique Cloud order and idempotency key.
6. An authorized Admin separately approves provider procurement/renewal and records the provider invoice reference, currency, amount, payment date, evidence reference and approving admin.
7. Provisioning is blocked unless customer payment, server-side entitlement, Admin provider-funding approval, provider capacity, and applicable platform licensing all pass.
8. Refunds, failed payments, chargebacks, provider invoice costs, taxes/fees and Shopnoltd margin must be reconcilable per order and billing period.

## Licensing gate for Mac Cloud

Before offering Mac Cloud to customers:

1. Obtain written confirmation from Apple Developer Relations or an appropriate commercial licensing provider for the exact intended service.
2. Treat developer services and general-purpose desktop access as separate licensing questions.
3. If relying on the macOS developer-service exception, verify every applicable condition, including eligible development services, a minimum 24-consecutive-hour lease, exclusive customer use/control, customer agreement to the applicable license, and required advance notice to Apple.
4. Do not assume that the developer-service exception authorizes a general-purpose shared Mac desktop subscription.
5. Confirm the provider's right to host, virtualize, remotely display and lease the selected macOS version and hardware.
6. Retain written approval and applicable license terms as launch evidence.

## Required backend work before paid launch

- Define Cloud product/SKU records and immutable price/plan versions; do not reuse generic plan checkout without order metadata.
- Add server-side Cloud order creation and verified payment-to-order association.
- Add server-side entitlements for `android_cloud`, `mac_developer`, and `mac_general_desktop`; enforce expiry, grace period, concurrency, duration and usage quotas.
- Add an Admin-only provider procurement/invoice ledger with append-only audit events and evidence references. Do not reuse customer wallet balances as provider funding or store provider credentials in the ledger.
- Add idempotent provisioning authorization that fails closed if payment, entitlement, admin approval, licensing or capacity checks are unavailable.
- Add reconciliation and refund/chargeback handling.
- Add tests for tenant isolation, authorization, replay/idempotency, payment webhook verification, failed settlement, and provisioning denial.

## Security and operations requirements

- Dedicated customer identity and isolated sessions.
- Short-lived, scoped browser session credentials; no public SSH/VNC/management port.
- Tenant-owned storage, explicit retention policy, encrypted backups and tested restore.
- Session lifecycle, idle timeout, concurrency quotas, audit events and abuse controls.
- Admin actions require authorization and audit logging.
- Capacity and provider health checks before session provisioning.

## Rollout gates

1. Licensing and provider approval.
2. Dedicated Apple Mac host/provider selection and capacity/security review.
3. Cloud product checkout, payment verification, entitlements and provider-cost ledger.
4. Backend provisioning API with fail-closed licensing guard.
5. Browser gateway prototype and isolated single-customer pilot.
6. Security, restore, load and end-to-end billing tests.
7. Limited subscription launch only after all acceptance gates pass.

## Safety boundary

The current `/cloud` UI and this document are an entry point and implementation specification only. They do not represent a Cloud-specific free quota, paid Cloud checkout, provider settlement, Apple approval, a provisioned Mac host, an active Mac runtime, or production deployment.
