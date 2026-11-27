# Shopnoltd Cloud Workspace: Mac licensing gate

## Product decision

Shopnoltd Cloud Workspace is the common customer entry point for cloud device environments.

- Android Cloud remains the existing browser-based Android emulator service.
- Mac Cloud is a planned subscription service with two intended use cases:
  - Developer Workspace: Xcode, Swift development, builds and automated testing.
  - General Mac Desktop: ordinary macOS desktop applications and browsing.
- Both use cases must run on eligible Apple-branded Mac hardware. A Linux container or a macOS-themed desktop is not a macOS substitute.

## Current implementation

- Customer entry point: `/cloud`.
- Existing Android workspace: `/android-cloud`.
- Mac Cloud is deliberately unavailable in the UI until licensing and infrastructure checks pass.
- The current Android controller configuration sets `ANDROID_CLOUD_MAX_SESSIONS=1`.
- Android emulator data currently uses a session-local Kubernetes `emptyDir`; it must not be advertised as persistent user storage.
- No Mac host provisioning, Mac session API, Mac billing entitlement, or Mac runtime is enabled by this change.

## Licensing gate

Before offering Mac Cloud to customers:

1. Obtain written confirmation from Apple Developer Relations or an appropriate commercial licensing provider for the exact intended service.
2. Treat developer services and general-purpose desktop access as separate licensing questions.
3. If relying on the macOS developer-service exception, verify every applicable condition, including eligible development services, a minimum 24-consecutive-hour lease, exclusive customer use/control, customer agreement to the applicable license, and required advance notice to Apple.
4. Do not assume that the developer-service exception authorizes a general-purpose shared Mac desktop subscription.
5. Confirm the provider's right to host, virtualize, remotely display and lease the selected macOS version and hardware.
6. Retain written approval and the applicable license terms as launch evidence.

## Subscription and entitlement requirements

The existing Shopnoltd billing system must be integrated through explicit server-side entitlements before provisioning:

- Separate entitlement identifiers for `android_cloud`, `mac_developer`, and `mac_general_desktop`.
- Plan status, renewal/expiry, grace period, concurrency, session duration and resource quotas checked by the backend.
- A browser UI or client-side flag must never grant access by itself.
- Provisioning must fail closed if the entitlement service is unavailable or licensing approval is absent.
- Do not charge customers for Mac Cloud while the relevant Mac entitlement is unavailable.

## Customer payment and provider settlement model

Shopnoltd uses a customer-pays-Shopnoltd, admin-pays-provider model. Cloud access is free to browse and discover; actual metered or subscription use is paid by the customer before capacity is committed.

1. Show the customer the platform, plan, billing period or usage unit, price, limits, and refund/cancellation terms before checkout.
2. Customer pays Shopnoltd through the existing approved payment channels. The payment must be verified server-side; a browser success screen is not proof of payment.
3. Record the customer payment against a cloud order/usage ledger with a unique reference and idempotency key.
4. Only an authorized Admin can approve provider procurement/renewal and mark the provider invoice as paid. Store provider, invoice reference, currency, amount, payment date, evidence reference, and approving admin in an auditable provider-cost ledger. Never store card credentials or expose provider secrets.
5. Reserve capacity only when the customer payment is verified, the provider capacity is available, and the provider-cost budget/coverage is approved. Do not start a paid host or incur provider charges automatically.
6. Reconcile customer receipts, refunds, provider invoices, taxes/fees, and Shopnoltd margin. Keep customer money and provider costs traceable per service and billing period.
7. If payment, admin approval, provider funding, licensing, or capacity is missing, fail closed and do not launch a billable session.

The intended admin workflow is manual approval/payment to the provider initially; automated provider settlement is out of scope unless separately approved and securely implemented. Never represent an unpaid provider invoice as paid or use a customer's payment for another purpose without an explicit disclosed policy.

## Security and operations requirements

- Dedicated customer identity and isolated Mac workspace.
- Short-lived, scoped browser session credentials; no public SSH/VNC/management port.
- Tenant-owned storage, explicit retention policy, encrypted backups and tested restore.
- Session lifecycle, idle timeout, concurrency quotas, audit events and abuse controls.
- Admin actions require authorization and audit logging.
- Capacity and provider health checks before session provisioning.

## Rollout gates

1. Licensing and provider approval.
2. Dedicated Apple Mac host/provider selection and capacity/security review.
3. Backend entitlement and provisioning API with fail-closed licensing guard.
4. Browser gateway prototype and isolated single-customer pilot.
5. Security, restore, load and end-to-end billing tests.
6. Limited subscription launch only after all acceptance gates pass.

## Safety boundary

This document and the `/cloud` UI are planning/control-surface work only. They do not represent Apple approval, a provisioned Mac host, an active Mac runtime, a purchasable Mac plan, or production deployment.
