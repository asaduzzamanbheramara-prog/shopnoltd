# Unified Shopnoltd customer-facing services

Shopnoltd uses `https://shopnoltd.dpdns.org` as the primary customer-facing platform.

Specialized subdomains may remain as technical/service endpoints for isolation, scaling, WebRTC, remote-device engines, APIs, and independent deployments. They must not be treated as unrelated products when a service is intended to be part of Shopnoltd.

## Android Cloud

The Android Cloud browser workspace is exposed through:

- `https://shopnoltd.dpdns.org/android-cloud`

The dedicated Android Cloud hostname may remain available for direct service diagnostics, but the primary customer navigation and browser workflow use the main Shopnoltd domain.

## Remote Devices

`https://devices.shopnoltd.dpdns.org` remains the specialized remote-device connection service for authorized Windows, Linux, macOS, Android, iOS and browser device profiles. It is distinct from Android Cloud and must not be renamed or repurposed as Android Cloud.

The main Shopnoltd service catalog identifies Remote Devices separately from Android Cloud.

## Rule

A separate hostname is an implementation boundary, not a separate Shopnoltd customer identity. Shared authentication, billing, wallet, exchange, entitlements and navigation should remain anchored to the main Shopnoltd platform wherever the service supports them.
