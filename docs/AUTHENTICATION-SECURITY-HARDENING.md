# Authentication security hardening

## Scope

Shopnoltd uses Keycloak as its primary OIDC identity provider. Browser login uses the
Authorization Code flow with PKCE (S256), transaction-bound `state`, and a registered
callback. Backend services validate Keycloak access tokens using the realm JWKS.

This hardening change standardizes the main service verifiers and closes several
authorization inconsistencies. It does not claim that every legacy or separately
deployed authentication surface has been migrated.

## Changes in this branch

- Main FastAPI service verifiers validate the configured Keycloak issuer as well as
  the service audience.
- Keycloak JWT verification is pinned to RS256 instead of trusting an algorithm value
  selected from a token header or JWKS entry.
- Platform-admin checks use realm-level role claims; a client-specific role cannot
  grant platform-wide administration.
- The OAuth service's tenant and customer authorization helpers use realm roles for
  platform/tenant privilege decisions.
- The ad service no longer treats a client role as a platform administrator role.
- The domain service compares its internal shared key using constant-time comparison.
- The auth-service refresh endpoint accepts the refresh token in a POST JSON body
  rather than a URL query parameter.
- The auth-service logout endpoint can revoke a supplied refresh token at Keycloak
  and marks matching local session records inactive.
- A focused auth-service unit test and a dedicated GitHub Actions workflow exercise
  the verifier and realm-role contract.

## Credential and token handling

- User passwords are authenticated by Keycloak; do not persist plaintext passwords.
- The Keycloak Admin API client secret is server-side configuration and must be
  supplied through Kubernetes Secrets or an equivalent secret manager.
- Access tokens are bearer credentials and must be sent only over TLS in the
  Authorization header.
- Refresh tokens must never be placed in URL query strings, logs, analytics, or
  support messages.
- Keycloak signing keys are public JWKS material; the signing private key remains
  exclusively with the identity provider.
- Service-to-service shared keys remain distinct from end-user access tokens and
  must be stored as runtime secrets.

## Remaining work before claiming a complete security migration

1. **Browser token storage:** the web portal currently stores access, refresh, and ID
   tokens in `localStorage`. JavaScript executing in the origin can read these values.
   A full fix requires migrating browser API traffic to a Backend-for-Frontend (BFF)
   session using Secure, HttpOnly, SameSite cookies, CSRF protection, and server-side
   token storage. Do not switch to `sessionStorage` and call that a security fix.
2. **Legacy AI backend:** `ai-platform/backend` contains a separate password-hash and
   locally signed JWT implementation. Confirm whether it is deployed or referenced;
   migrate it to Keycloak or retire it before describing identity as fully centralized.
3. **Password grant:** `platform/auth-service/app/api/auth.py` retains a legacy
   Resource Owner Password Credentials (password grant) endpoint. Prefer the OIDC
   browser Authorization Code + PKCE flow and disable Direct Access Grants in
   Keycloak once no supported clients depend on this endpoint.
4. **End-to-end logout:** browser logout currently uses the Keycloak OIDC end-session
   redirect with an ID-token hint. The auth-service API can revoke a refresh token when
   supplied; clients must call it before clearing that token if they need the local
   session record and refresh-token revocation together.
5. **Runtime verification:** verify the deployed Keycloak client audience mappers,
   issuer URL, social identity-provider credentials, token lifetimes, refresh-token
   rotation/reuse policy, and Kubernetes Secret mounts. Source code alone cannot prove
   production configuration or successful real-user login.
6. **Verifier inventory:** review separately deployed VPN, remote-device, Android Cloud,
   agent, and legacy AI components whenever their deployment manifests or routes
   change. They have independent runtime settings and must retain the same issuer,
   audience, algorithm, and role rules.

## Operational rollout

Deploy the Keycloak issuer/audience changes only after confirming that the Keycloak
realm emits the expected issuer and each service's configured audience. If an existing
service token lacks its required audience, correct the Keycloak audience mapper rather
than weakening validation. Run the authentication workflow and existing service
smoke tests before promoting images or syncing production.
