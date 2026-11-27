# Shopnoltd Cloud Workspace: cross-platform, licensing and billing gates

## Product scope

One browser portal will offer separate, isolated environments:

- **Windows Cloud:** Windows desktop/developer workspace on properly licensed Windows hosting.
- **Linux Cloud:** full Linux desktop/developer workspace using supported distributions such as Ubuntu or Debian.
- **Mac Cloud:** Xcode/Swift developer workspace and separately reviewed general macOS desktop. Both require eligible Apple-branded Mac hardware and applicable licensing.
- **Android Cloud:** browser-based Android emulator/device workspace. Supported phone/tablet profiles and Android versions must be validated before offering.
- **Browser Code Workspace:** existing authenticated Shopnoltd code-server/app workspace; not a full desktop OS.

A single portal does not mean one shared VM. Each customer session must be isolated and provisioned on an OS-appropriate host.

## Relationship to the Universal Software & OS Center

Shopnoltd is also intended to be a universal online software discovery, installation-guidance and device-recovery destination—not only a cloud desktop provider. Keep this as a distinct but connected product area:

- **Online software and OS catalogue:** discover supported operating systems, applications, drivers and recovery utilities; filter by device, OS/version, architecture and package format; prefer official publisher sources and show licence and verification status.
- **Online installation guidance:** provide platform-specific, permission-aware instructions and supported package-manager/helper workflows. A browser catalogue or download link alone does not install software on a customer's device.
- **Pendrive / offline recovery:** guide users to obtain verified images and create bootable media on a supported working computer. Actual USB writing requires a separately signed, least-privilege local helper with explicit target-drive selection and destructive-write confirmation; a normal web page cannot safely write arbitrary physical disks.
- **Device-specific recovery:** use manufacturer-supported methods for phones, tablets, Macs, PCs, TVs, routers and embedded devices. Do not claim that a generic PC bootable USB installs or repairs every device.
- **Cloud Workspace connection:** offer browser-based Windows/Linux/Mac/Android environments as a separate way to use supported systems online. A cloud session is not the same as installing an OS onto a user's physical device.

The existing foundation and constraints are documented in `docs/universal-software-os-center/README.md`, `device-installation-support-matrix.md` and `bootable-usb-recovery.md`. Catalogue, planner and documentation work must not be described as a completed USB writer, verified universal installer, or successful physical-device recovery.

## Universal OS & Software Center connection

The Cloud portal is one part of the broader Shopnoltd device platform. Its `/cloud` page links directly to the existing `/software-os-center.html` catalogue/service-request experience and `/offline-recovery-guide.html` guide. Keep these journeys distinct:

- **Cloud Workspace:** remote browser sessions on provider hosts, subject to OS licensing, account, capacity and entitlement gates.
- **Software & OS Center:** official-source discovery, compatibility information, service requests and vendor-specific installation/recovery guidance for supported device classes.
- **Pendrive workflow:** verified OS/recovery image plus compatible media-writing tool on a separate working computer. The current web UI does not write physical disks; a future writer must be a signed local helper with explicit target-drive selection and destructive confirmation.
- **Online software setup:** a catalogue link or browser guide is not remote installation. Actual local installation needs a supported OS/package manager or separately reviewed signed helper with least privilege and user consent.
- **Device support:** Windows/Linux PCs and compatible Macs may use bootable installers; iPhone/iPad and most Android phones, TVs, routers and embedded devices require model-specific vendor recovery rather than a generic PC boot USB.

Do not advertise a universal one-click installer, automatic physical-device repair, or USB writing until the relevant helper, exact-device compatibility tests, image verification and recovery safeguards are shipped.

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


## Verified integration boundary (repository audit)

The current payment implementation must not be mistaken for a Cloud order/entitlement system:

- payment-service has wallet, direct-payment, provider-webhook and transaction flows. Direct-number TxID submissions are evidence; the manual verification endpoint is an Admin-reviewed wallet-credit flow, not an OS Cloud product grant.
- Existing provider webhooks process payment-service transactions. They are not yet bound to a server-priced Cloud SKU/order, a Cloud entitlement transition, or a provisioning request.
- The repository's separate secure-entitlement contract is explicitly design-only. Do not treat its illustrative GET /api/v1/me/entitlements response as a deployed API.
- No Cloud-specific product catalogue, paid order table, entitlement table, provider procurement/invoice ledger, or fail-closed provisioning authorization endpoint is connected to the Cloud UI.
- Android Cloud currently authenticates the account and enforces its configured session capacity/TTL. It does not consult a paid Cloud entitlement. Keep its existing access policy separate; do not silently reclassify it as a paid service.

### Required Cloud order state machine

 draft → awaiting_customer_payment → payment_verified → awaiting_provider_approval → provider_funded → provisionable → provisioning → active

Terminal/exception states must include payment_failed, payment_mismatch, provider_rejected, licensing_blocked, capacity_unavailable, provisioning_failed, cancelled, refunded, and revoked. Only a server-side transition to provisionable may authorize a provider adapter to create a session. Browser redirects and client-supplied statuses never advance this state machine.

### Minimum server-owned records

- Cloud SKU/price version: OS, image/version, plan, currency, amount, billing period, resource limits, retention and licensing class.
- Customer order: authenticated subject, tenant, immutable SKU/price snapshot, unique order/idempotency keys, verified payment transaction/provider event and lifecycle timestamps.
- Entitlement: subject, tenant, SKU, validity interval, status, concurrency/duration/usage quotas, source order and revocation reason.
- Provider procurement/settlement: provider, OS/licensing scope, invoice/reference, amount/currency, period, evidence reference, Admin approver and append-only audit events. Never store provider credentials or secrets in this ledger.
- Provisioning operation: order/entitlement reference, selected provider/host, idempotency key, capacity/licensing check result, session reference and cleanup status.

All reads/writes must enforce tenant ownership and role checks. Webhook processing, entitlement grants, provider approval and provisioning must be idempotent and auditable. If payment, entitlement, licensing, provider approval, capacity or the authorization service is unavailable, paid provisioning must fail closed.
