# Shopnoltd full-platform acceptance and regression plan

## Purpose

Validate and repair the existing Shopnoltd platform incrementally, preserving existing features and data. This is a release/test contract, not a claim that every listed feature is already implemented or live. Use the existing GitOps and secret-management processes; do not bypass them with direct production edits.

## Identity and account policy

- Every account has one immutable internal canonical user ID and one Keycloak subject mapping. A user-facing profile ID/slug may be editable only if it is distinct from the immutable database primary key and collisions are rejected.
- Usernames are normalized and unique. Email addresses are normalized and unique case-insensitively across the canonical identity store and Keycloak.
- The permitted email domain must be a centrally configured policy, verified at registration and update time. Do not silently assume an address domain or change existing users' email addresses. If the product requires one exact email domain, configure that domain explicitly and define how existing external-email accounts are migrated.
- Email/domain changes must be verified, transactional across identity and user mirror records where possible, and reconciled safely after partial failures.
- Public registration must never allow a user to self-assign administrator privileges. New accounts receive the least-privilege default role; admin assignment requires a separately authorized workflow.
- Duplicate usernames, email addresses, profile slugs, referral codes, and canonical identity mappings must fail with a clear conflict response and a database-level uniqueness guarantee where applicable.

## Registration and login test matrix

Run end-to-end tests against a dedicated staging environment with synthetic accounts and disposable test data. Never test by changing production users' passwords or by exposing passwords/tokens in logs.

| Actor / path | Required test | Pass condition |
|---|---|---|
| Existing customer | Login through website browser redirect, PKCE callback, session and dashboard | Correct account lands on dashboard; logout invalidates local session |
| Existing tenant owner | Login and tenant-scoped pages/APIs | Owner can access only their own tenant |
| Existing admin | Login to the intended admin portal and database control plane | Admin-only functions work; no direct-access password-grant dependency |
| Newly registered customer | Register, verify email if required, login, create profile | Unique canonical ID and profile; least-privilege role |
| New tenant owner | Approved owner onboarding flow | Tenant association created once; tenant isolation enforced |
| Duplicate registration | Repeat username/email with case and whitespace variants | Conflict; no duplicate identity or orphan profile |
| Unknown/invalid referral | Register with missing, invalid or deleted referral code | Safely attributed to configured admin/system referral, or explicitly rejected according to product policy; never to an arbitrary user |
| Valid referral | Register using an active user's referral URL/code | Correct immutable referrer attribution; self-referral and cycles rejected |
| Profile ID update | Change editable public profile ID/slug | New slug is unique; internal primary key and ownership references remain stable |
| Disabled/unverified account | Attempt login | Correct policy response; no unauthorized access |
| Expired/invalid token | Call protected APIs | 401; no data leakage |
| Role escalation attempt | Submit admin role/tenant ID in public registration/profile payload | Server ignores or rejects privilege fields |

The production smoke workflow is evidence only for the cases it actually executes. A passing static test is not a substitute for browser-based tests with synthetic accounts.

## Data integrity and database-management acceptance

- Run the existing read-only reconciliation endpoint/report first; record duplicate email, duplicate Keycloak ID, orphan profile and tenant-reference counts without exposing personal records.
- Verify unique constraints/indexes and case-insensitive normalized uniqueness before proposing any migration. Report existing collisions; do not auto-delete, overwrite, or merge identities.
- Verify migrations are repeatable and forward-compatible; run on disposable test database before staging.
- Test admin database catalog/inventory, permitted metadata reads, authorized CRUD on an explicitly safe test table, audit history, pagination, and error handling.
- Prove normal users cannot read or mutate admin/system tables or another tenant's data. No unrestricted raw SQL for normal users.
- Test rollback on failed writes, concurrent duplicate creation, idempotent retries, backups and restore in non-production. Never claim backup/restore works without a restore drill.
- Verify all database-backed services individually: health/connectivity, migrations, read/write paths, authorization, uniqueness, timeouts, and sanitized failures. Inventory alone is not proof of CRUD correctness.

## Referrals, profiles and provisioning

- Referral URLs and QR codes resolve to an active referrer; admin fallback behavior for absent/invalid referrers is deterministic, auditable, and covered by tests.
- Referral rewards must be idempotent, reconcile to ledger/payment records, and reject self-referrals, duplicate rewards and invalid transitions.
- Keep internal user ID immutable. Allow editing only the public profile ID/slug and editable profile fields, with authorization and uniqueness checks.
- New and existing users should have idempotent domain/mailbox provisioning status. Never mark a resource active before provider confirmation. Current repository audit documents that mailbox activation/full mail-stack and live provider validation remain incomplete; test and report them as blockers rather than assuming they work.

## Services, automation and payments

- Test each service catalog entry's health, auth requirements, role/tenant boundaries, and actual backing service; a reachable route alone is not feature success.
- Automation workflows need authorization, scoped tokens, audit records, idempotency, bounded retries, and a visible failure state. Test that normal users cannot invoke admin automation.
- Payment tests must use provider sandbox credentials and test cards/webhooks only. Verify checkout, signature verification, idempotency, duplicate webhook delivery, failed/abandoned payments, refund/reconciliation paths and entitlement changes. Never represent demo-mode transactions as live payments.
- Do not enable or claim a gateway is live unless credentials are provisioned through secret management and a real sandbox/live health test succeeds.

## Software, operating systems, devices and bootable USB

- Catalogue OS/application/driver installers by vendor source, version, architecture, licence, supported device/OS, checksum/signature source and known limitations.
- Cover supported Windows, Linux, macOS and device-specific Android/iOS or embedded-device workflows only where documented by the vendor. There is no single universal installer for every OS/device.
- USB/pendrive creation must use a separately reviewed local helper, not unrestricted browser disk access. Show exact device and capacity, verify image integrity, warn about data loss, require a second explicit confirmation before writing, and verify the result where possible.
- Test non-destructive catalogue/download instructions separately from actual image writing and boot tests. Never say a USB writer, OS installer or device repair works merely because a catalogue page exists.
- Test supported device/OS combinations in disposable VMs and representative physical hardware before advertising compatibility. Never silently format drives or install software.

## Automation and CI

- Run static authentication-contract checks on pull requests.
- Run unit/integration tests for each affected service and migration.
- Run browser tests for existing and newly registered synthetic actors using the real Authorization Code + PKCE path.
- Run the authenticated production smoke workflow only with its intended GitHub Actions secrets and approved test accounts. Review job logs for pass/fail and ensure they contain no credentials or tokens.
- After merge, wait for GitOps sync, verify the exact revision, rollout readiness, health endpoints and smoke tests. Do not claim deployment success based on a merged PR alone.

## Current known boundaries

- Website browser login is implemented with Authorization Code + PKCE; a password-grant token request is not a website login test.
- Keycloak client sync previously enabled Direct Access Grants for existing clients inconsistently with new-client creation. PR #454 changes that reconciliation policy and adds static contract checks; it is open and unmerged at the time of this document.
- Existing referral UI, profile/user APIs, payment services, database control-plane docs and software/OS catalogue scaffolding exist, but their presence does not establish that every path is end-to-end functional.
- The repository's own mailbox-provisioning audit identifies unverified/incomplete mailbox activation and live mail-provider setup.
- The USB recovery documentation explicitly describes the current catalogue/checksum tools as read-only and a future local USB writer as planned.
- No production passwords were changed as part of this acceptance plan. Do not rotate users' passwords to diagnose browser-flow or configuration failures.

## Release gate

Do not call the platform fully verified until each supported actor class and newly registered synthetic account passes the browser login/role tests, database checks pass, referral/profile invariants pass, payment and automation paths are tested in their supported modes, and every advertised OS/device installation workflow has evidence for its declared compatibility. Publish a per-feature PASS / FAIL / BLOCKED report with the tested revision and environment.
