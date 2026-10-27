# Shopnoltd authentication automation: all users and future signups

## Purpose

Use the scheduled Keycloak readiness workflow and browser tests together. Do not keep a list of real users' passwords in this repository, a CSV committed to Git, an Actions artifact, or chat.

## What can be checked for every account

The workflow `.github/workflows/all-user-keycloak-readiness.yml` inventories every user in the configured Keycloak realm, including new users on the next scheduled/manual run. It reports whether each account is enabled, has a password credential, has an OTP credential, and has required actions. Its per-account report uses pseudonymous references rather than usernames or email addresses.

A Keycloak password credential is a verifier/hash, not a recoverable plaintext password. An account with no password credential must complete an approved password-setup/reset flow; automation must not assign a shared password.

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

Repository Actions secrets for the read-only inventory:
- `KEYCLOAK_AUDIT_CLIENT_ID`
- `KEYCLOAK_AUDIT_CLIENT_SECRET`

Use a dedicated Keycloak confidential client with service-account authentication and only the required read-only realm-management permissions. Do not use an administrator's personal password.

Optional repository Actions variables:
- `KEYCLOAK_BASE_URL=https://auth.shopnoltd.dpdns.org`
- `KEYCLOAK_REALM=shopnoltd`

The current all-user workflow is an inventory/readiness audit, not a claim that every real account has completed a successful login. The existing authenticated browser workflow tests dedicated admin/owner/user accounts only.
