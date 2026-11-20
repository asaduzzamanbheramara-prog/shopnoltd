# Shopnoltd authentication automation: all users and future signups

## Purpose

Use the scheduled Keycloak readiness workflow and browser tests together. Do not keep a list of real users' passwords in this repository, a CSV committed to Git, an Actions artifact, or chat.

## What can be checked for every account

The workflow `.github/workflows/all-user-keycloak-readiness.yml` inventories every user in the configured Keycloak realm, including new users on the next scheduled/manual run. It reports whether each account is enabled, has a password credential, has an OTP credential, and has required actions. Its per-account report uses pseudonymous references rather than usernames or email addresses.

A Keycloak password credential is a verifier/hash, not a recoverable plaintext password. An account with no password credential must complete an approved password-setup/reset flow; automation must not assign a shared password.

## Current production readiness finding (2026-11-20)

The successful all-user audit inspected 584 Keycloak accounts without changing any account. It found 581 enabled accounts with the `UPDATE_PASSWORD` required action, one enabled account without a password credential, and two enabled accounts with a password credential and no required action. The CSV contains only pseudonymous user references. Do not remove `UPDATE_PASSWORD` in bulk: imported legacy password hashes are not reused, and each affected account must complete its own password setup/reset.

The Keycloak realm's password-recovery email path is configured by the targeted Keycloak client-sync job. That job mirrors the existing `shopno-mail/mail-service-config` SMTP host/port and `shopno-mail/mail-service-smtp` credentials into namespace-local Keycloak config/secret objects, then reconciles the realm's SMTP settings and `resetPasswordAllowed=true`. The Keycloak egress policy permits the Brevo relay IP on SMTP submission port 587. The sync verifies the persisted non-secret SMTP settings and never logs credentials. It does not send reset emails to customers; users must initiate their own reset or required-action flow.

## Real login tests

A real password login can only be verified with the current password (and MFA factor if required) or by having the account owner complete a user-mediated test. Do not attempt to bypass MFA, enumerate passwords, or use the Keycloak Admin API to impersonate users.

Use dedicated synthetic test accounts for repeatable end-to-end browser tests. Store their credentials and TOTP seed as separate GitHub Actions secrets. Never put secret values in source files. Keep the existing three-role smoke test separate from the all-account readiness inventory.

## Future user signup/login

For future users, run a separate signup-to-login browser test against a dedicated synthetic test identity:
1. Create the test identity through the public signup flow with a generated, one-run password held only in the test process.
2. Verify signup returns the expected success response and that the new account appears in Keycloak.
3. Use the same in-memory password to test the public login flow and the authenticated landing page.
4. Clean up only the synthetic test identity created by that run, after confirming it belongs to the test namespace/account marker. Never clean up a real customer account.
5. Report pass/fail without printing the password, tokens, TOTP codes, or personal user details.

This test should be added only after the UI signup/login contract and safe synthetic-account cleanup behavior are verified. It must not use a real customer's credentials.

## Required configuration

The trusted self-hosted Linux runner reads the existing Keycloak bootstrap credential from the Kubernetes Secret `shopno-identity/keycloak-secret` only to provision/repair one dedicated confidential audit client. The workflow creates or reconciles `shopnoltd-keycloak-readiness-audit`, disables browser/direct-grant flows, enables its service account, and assigns only these read-only `realm-management` client roles: `view-users`, `query-users`, and `view-realm`. The generated client ID/secret is stored in the Kubernetes Secret `shopno-identity/shopnoltd-keycloak-audit-client`; it is never printed or uploaded. All per-account reads then use that restricted service-account token. No GitHub Actions client-secret values are required. The bootstrap credential is never placed in source files, artifacts, or logs.

The audit also checks the live realm's `resetPasswordAllowed` flag and whether its SMTP configuration contains a host and sender. This is configuration presence only, not a test email or proof of delivery. The realm import currently does not define an SMTP server. The separate `shopno-mail` SMTP relay secret is not automatically proof that Keycloak is configured to use that relay. Configure Keycloak's realm SMTP settings only after confirming the actual internal SMTP service endpoint, TLS mode, sender address, and credentials; never copy SMTP passwords into Git.

Optional repository Actions variable: `KEYCLOAK_REALM=shopnoltd`.

The scheduled audit runs on the trusted self-hosted Linux runner and reaches Keycloak through a temporary localhost port-forward to the in-cluster Service. This avoids depending on Cloudflare allowing GitHub-hosted runner traffic to the OIDC token endpoint.

The current all-user workflow is an inventory/readiness audit, not a claim that every real account has completed a successful login. The existing authenticated browser workflow tests dedicated admin/owner/user accounts only.
