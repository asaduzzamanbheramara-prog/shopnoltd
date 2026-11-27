# Sign in with Apple for Shopnoltd

## Status

This branch adds optional frontend and Keycloak synchronization support for an
Apple identity provider. The Apple button is deliberately disabled by default.
This is **not production-ready and does not enable Apple login by itself**.

Shopnoltd uses Keycloak realm `shopnoltd` for all portal authentication. The
Apple identity provider must be installed and configured in Keycloak before
the frontend feature flag is enabled.

## Provider implementation

The official Keycloak distribution does not include Apple as a built-in
identity provider. The current integration design uses the community
Keycloak Apple Identity Provider extension:

- Project: https://github.com/klausbetz/apple-identity-provider-keycloak
- Extension directory: https://www.keycloak.org/extensions
- Review the extension's release notes, source, license, and compatibility
  with Shopnoltd's pinned Keycloak 26.7.1 before adding its JAR to the image.

Do not install an unpinned or unverified JAR directly into production. Pin a
specific compatible release and verify its checksum before building the
Keycloak image. The extension must be present at Keycloak startup before any
Apple provider is reconciled.

## Apple Developer configuration required

A working web integration requires an Apple Developer account with Sign in
with Apple configured, including:

- Services ID (used as `APPLE_CLIENT_ID`)
- Team ID (used as `APPLE_TEAM_ID`)
- Key ID (used as `APPLE_KEY_ID`)
- Sign in with Apple private key (.p8; stored as `APPLE_CLIENT_SECRET` for
  the extension's configuration interface)

The exact extension release must be checked to confirm its configuration
field names and key format. Never commit the real private key, put it in a
ConfigMap, paste it into chat, or include it in a pull request.

## Apple callback

Register this exact callback URL for the Services ID in the Apple Developer
portal:

`https://auth.shopnoltd.dpdns.org/realms/shopnoltd/broker/apple/endpoint`

The Services ID must also be configured for the Shopnoltd website domain and
the callback URL above.

## Kubernetes runtime secret

After the extension has been installed and the Apple Developer configuration
has been completed, populate the existing Secret
`shopno-identity/keycloak-social-providers` with these keys using the
approved interactive secret-provisioning process:

- `APPLE_CLIENT_ID`
- `APPLE_CLIENT_SECRET` (private .p8 key material in the format required by
  the pinned extension)
- `APPLE_TEAM_ID`
- `APPLE_KEY_ID`

The repository example contains empty placeholders only. Do not apply the
example file as a production Secret.

The Keycloak sync job ignores Apple until all four values are present. It
creates the `apple` and `apple-signup` aliases, with the normal login alias
using Shopnoltd's existing email-verification-first broker flow.

## Frontend feature flag

The Login and Register pages understand the `apple` provider hint. The
button remains hidden unless the web portal is built with:

`VITE_SOCIAL_LOGIN_APPLE=true`

Keep this flag false until all of the following are verified:

1. The pinned Apple extension is installed in the Keycloak image.
2. The four Apple values are provisioned in the runtime Secret.
3. Keycloak sync reports successful creation/update of both Apple aliases.
4. Apple redirects to the callback URL and returns successfully.
5. Login and signup browser tests pass, including email/account-linking safety.
6. A production deployment and real-device/browser end-to-end test succeed.

## Safety and rollout

- Do not change production Secrets or Keycloak runtime configuration as part
  of a source-only change.
- Do not enable the frontend button before the provider is installed and
  credentials are present.
- Do not assume that a normal Apple Account alone grants access to the Apple
  Developer capabilities needed for web Sign in with Apple.
- Do not automatically link identities solely because an email string
  matches. Verify Apple's signed identity token and retain the existing
  Shopnoltd account-linking and email-verification safeguards.
