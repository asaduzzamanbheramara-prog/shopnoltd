# ShopnoltdToolbox Device + Automation Contract

This document defines the common platform boundary for ShopnoltdCollect Android and the existing Shopnoltd remote-device system.

## 1. Device identity

Every managed device has a stable platform device identity and belongs to exactly one authorized Shopnoltd tenant/user scope at a time.

Minimum lifecycle:

```text
created -> pending_enrollment -> enrolled -> active -> revoked
```

Enrollment credentials are single-use and expiring. Runtime credentials must be separate from the enrollment token and revocable.

## 2. Device types

The device registry must support, without changing the core model:

- `android_shopnoltd_collect`
- Windows agent
- Linux agent
- macOS agent
- future device/agent types

The Android application reports its capabilities rather than claiming capabilities it does not implement.

## 3. Capability model

A capability is metadata, not permission. Authorization is evaluated separately.

The platform distinguishes:

```text
capability advertised
    !=
operation authorized
    !=
operation currently available
```

ShopnoltdCollect currently advertises collection-oriented capabilities such as forms, data collection, location, camera, QR/barcode, audio, printing, offline storage, background sync and mobile-device-management.

## 4. Automation safety

Automation actions must be explicitly allowlisted. The Android client must never expose arbitrary shell execution or arbitrary server-side command execution.

Every automation execution should carry:

- tenant/user scope
- automation id
- trigger id/event id
- target device id when applicable
- action id/type
- authorization result
- idempotency key
- attempt number
- started/completed timestamps
- final status
- audit reference

## 5. Supported trigger classes

The platform model supports:

- schedule
- webhook/event
- payment result
- domain/service lifecycle
- wallet/balance condition
- device event
- collection/application event

## 6. Financial boundary

Automation never owns payment credentials, wallets or ledger balances.

All billable actions use the unified financial authority:

```text
service price
 -> authoritative base currency
 -> authoritative exchange rate
 -> settlement currency
 -> gateway/method compatibility
 -> checkout
 -> verified payment
 -> billing-engine wallet/ledger
 -> fulfillment
 -> automation event
```

Android devices must never contain gateway merchant secrets.

## 7. ShopnoltdCollect boundary

ShopnoltdCollect remains based on the existing Kobo/ODK collection engine. The Shopnoltd layer adds platform identity/device/automation metadata around that engine; it does not replace the existing ODK external API or collection workflow.

## 8. Existing remote-device integration

The existing remote-device UI, enrollment flow, gateway, persistent registry and allowlisted executor remain the foundation for desktop device management. ShopnoltdCollect is added as another first-class device type rather than creating a second device registry.

## 9. Audit and tenant isolation

Device registration, enrollment, revoke, automation creation, authorization, execution and failure events must be auditable and tenant-scoped.

No automation or device endpoint may accept an arbitrary target device solely because the caller knows its identifier.
