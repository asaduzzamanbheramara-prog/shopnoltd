# Shopnoltd Cloud Workspace: cross-platform, licensing and billing gates

## Product scope

One browser portal will offer separate, isolated environments:

- **Windows Cloud:** Windows desktop/developer workspace on properly licensed Windows hosting.
- **Linux Cloud:** full Linux desktop/developer workspace using supported distributions such as Ubuntu or Debian.
- **Mac Cloud:** Xcode/Swift developer workspace and separately reviewed general macOS desktop. Both require eligible Apple-branded Mac hardware and applicable licensing.
- **Android Cloud:** browser-based Android emulator/device workspace. Supported phone/tablet profiles and Android versions must be validated before offering.
- **Browser Code Workspace:** existing authenticated Shopnoltd code-server/app workspace; not a full desktop OS.

A single portal does not mean one shared VM. Each customer session must be isolated and provisioned on an OS-appropriate host.

## Current implementation and truthful availability

- Portal: `/cloud`.
- Existing Code Workspace: `/app?panel=code`; uses current app environment and access controls.
- Existing Android workspace: `/android-cloud`; controller default is `ANDROID_CLOUD_MAX_SESSIONS=1`.
- Android emulator data currently uses session-local Kubernetes `emptyDir`; it is temporary, not persistent user storage.
- Windows Cloud, full Linux desktop Cloud and Mac Cloud are planned, not provisioned. Native installers in Downloads are not cloud desktop sessions.
- A Cloud-specific free quota, Cloud checkout, server-side entitlements, usage metering and provider invoice/settlement ledger are not implemented by this UI change.
- Generic Shopnoltd checkout/wallet functionality is not proof of an OS Cloud order or entitlement.
- Mac has no host provisioning, session API, billing entitlement or runtime enabled.

## Free and paid service policy

1. Cloud Workspace discovery/browsing is free.
2. Existing Code Workspace and Android Cloud remain governed by current account, session, capacity and access controls. Do not promise a new free quota or unlimited sessions until enforceable backend quotas exist.
3. Do not add desktop VMs, Kasm/Guacamole, Android emulator replicas or other compute workloads to the current cluster without measured capacity review. Free software does not make compute, storage, bandwidth or operations free.
4. Published paid plans must disclose OS/image, price, currency, billing period/usage unit, CPU/RAM/storage, session duration/concurrency, retention, cancellation and refund terms.
5. Customer pays Shopnoltd first. Payment must be verified server-side and linked to a unique OS Cloud order and idempotency key.
6. Authorized Admin separately approves provider procurement/renewal and records provider invoice reference, currency, amount, payment date, evidence reference and approving admin.
7. Provisioning is blocked unless customer payment, server-side entitlement, Admin provider-funding approval, provider capacity and OS licensing all pass.
8. Refunds, chargebacks, provider costs, taxes/fees and Shopnoltd margin must be reconcilable per order and billing period.

## OS-specific provider and licensing requirements

### Windows
- Confirm provider Windows Server/client virtualization and remote-access rights for the exact service model.
- Verify per-user/per-device licensing and any required RDS/SPLA or equivalent terms before multi-user sessions.
- Use supported, patched images and tenant-isolated sessions. Do not expose RDP directly to the public internet.

### Linux
- Select maintained distributions and document image lifecycle/security patching.
- Measure CPU, RAM, storage IOPS, bandwidth and concurrency before launch.
- Use per-customer isolation, short-lived gateway credentials, quotas and session cleanup.

### macOS
- Obtain written confirmation from Apple Developer Relations or an appropriate commercial licensing provider for the exact service.
- Treat developer services and general-purpose desktop access as separate licensing questions.
- If relying on a developer-service exception, verify every applicable condition, including eligible development services, minimum 24-consecutive-hour lease, exclusive customer use/control, customer agreement to the applicable license and required advance notice.
- Do not assume this exception authorizes a general-purpose shared Mac desktop subscription.
- Confirm provider rights to host, virtualize, remotely display and lease the selected macOS version/hardware.

### Android
- Choose emulator/device providers with commercial service and redistribution terms suitable for Shopnoltd.
- Validate Android version, ABI/ARM compatibility, Google Play services and app testing requirements separately; an emulator does not imply Google Play certification.
- Offer phone/tablet profiles only after testing. Persistent storage requires a quota-limited volume and tested restore.
- Enforce session quotas, expiry, cleanup, abuse controls and tenant isolation.

## Required backend work before paid launch

- Define OS product/SKU records and immutable price versions; do not reuse generic checkout without OS Cloud order metadata.
- Add server-side order creation and verified payment-to-order association.
- Add entitlements for `windows_cloud`, `linux_cloud`, `mac_developer`, `mac_general_desktop`, and `android_cloud`; enforce expiry, grace period, concurrency, duration and usage quotas.
- Add Admin-only provider procurement/invoice ledger with append-only audit events and evidence references. Do not reuse customer wallet balances as provider funding or store provider credentials in the ledger.
- Add idempotent provisioning authorization that fails closed if payment, entitlement, Admin approval, licensing or capacity checks are unavailable.
- Add reconciliation/refund handling and tests for tenant isolation, authorization, webhook verification, replay/idempotency, failed settlement and provisioning denial.

## Security and operations

- Dedicated customer identity and isolated sessions.
- Short-lived scoped browser credentials; no public SSH/RDP/VNC/management port.
- Tenant-owned storage, explicit retention, encrypted backups and tested restore.
- Session lifecycle, idle timeout, concurrency quotas, audit events and abuse controls.
- Admin actions require authorization and audit logging.
- Check provider health and capacity before provisioning.

## Rollout gates

1. OS-specific licensing/provider approval and capacity review.
2. Host/image selection for Windows, Linux, Mac and Android.
3. Cloud checkout, payment verification, entitlements and provider-cost ledger.
4. Fail-closed provisioning API.
5. Isolated single-customer pilot for each OS.
6. Security, restore, load and end-to-end billing tests.
7. Limited launch only after all acceptance gates pass.

## Safety boundary

The `/cloud` UI and this document are an entry point and implementation specification only. They do not represent free quotas, paid OS Cloud checkout, provider settlement, licensing approval, provisioned Windows/Linux/Mac hosts, additional Android versions, active sessions or production deployment.
