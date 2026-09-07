# ShopnoltdCollect signing CI

ShopnoltdCollect is maintained as the `shopnoltd-collect-android` submodule. Its Android application ID is `org.shopnoltd.collect`.

The Android CI supports two distribution paths:

- `selfSignedRelease`: installable QA artifact for functional testing.
- `release`: production-signed artifact when encrypted GitHub Actions signing secrets are configured.

The release keystore must remain outside source control. Configure encrypted Actions secrets in the Android repository; never commit `secrets.properties`, passwords, or the keystore. Keep the current release key for update continuity until a deliberate signing migration is performed.
