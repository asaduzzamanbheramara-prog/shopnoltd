# ShopnoltdCollect release signing

ShopnoltdCollect uses the Android application ID `org.shopnoltd.collect`.

## Local signing

Keep the release keystore outside the repository. The Gradle build reads these local properties when present:

- `RELEASE_STORE_FILE`
- `RELEASE_STORE_PASSWORD`
- `RELEASE_KEY_ALIAS`
- `RELEASE_KEY_PASSWORD`

`secrets.properties` is ignored by Git and must never be committed.

## GitHub Actions signing

Configure repository Actions secrets in the ShopnoltdCollect repository:

- `RELEASE_STORE_BASE64`
- `RELEASE_STORE_PASSWORD`
- `RELEASE_KEY_ALIAS`
- `RELEASE_KEY_PASSWORD`

The workflow creates the keystore only in the ephemeral runner workspace, builds the signed release APK, verifies it with `apksigner`, and publishes the checksum as an artifact. Secret values must never be printed in logs.

## QA versus release

`selfSignedRelease` is the installable QA path and does not use the production release key. `release` uses the configured release signing key. Do not treat a QA APK as the production distribution artifact.

## Key continuity

Keep the current release key for now so future updates can be signed with the same identity. Rotate/rekey later only with an explicit Android release migration plan, because changing signing identity can prevent normal updates over an existing installation.
