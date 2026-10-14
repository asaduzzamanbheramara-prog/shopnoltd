# Automatic user subdomain and full mailbox provisioning

## Requirement

Every newly created Shopnoltd account must receive, without visiting a separate settings page:

1. One unique personal subdomain under the configured Shopnoltd parent zone.
2. One full email mailbox with a working login and inbox.
3. A visible provisioning status and safe retry behavior if either downstream service is temporarily unavailable.

This document records the source audit and implementation safety gates. It does not claim that provisioning is implemented or that live infrastructure is ready.

## Source audit findings

- `platform/freedomain-service/app/api/domains.py` contains `provision_for_user`, which can idempotently provision a free subdomain, and `GET /me` calls it lazily. The OAuth outbox now records subdomain work, but no worker currently invokes the FreeDomain service for those jobs.
- `platform/freedomain-service/app/backfill_existing_users.py` exists for existing Keycloak users, but it is an operational backfill and must not be run as part of an unreviewed code change.
- `platform/oauth-service/app/api/users.py` now enqueues unique `subdomain` and `mailbox` outbox jobs for user mirrors and administrator-created accounts. The database model constrains resource/status values and non-negative attempt counts. No worker/reconciler consumes the jobs yet, so enqueueing does not mean the resources exist.
- `platform/mail-service/app/api/mailboxes.py` now generates a cryptographically random provider password, never returns it, checks Mailcow's application-level JSON result, rolls back the local session on provider errors, and only marks the local mailbox active after provider success. Focused mocked tests cover these paths. The endpoint still requires administrator authorization and is not a complete self-service activation flow.
- `platform/mail-service/app/core/config.py` defaults to a Mailcow API URL and placeholder API key. The Kubernetes mail-service ConfigMap currently configures Brevo SMTP relay only.
- The checked-in mail-server manifest uses `mailu/postfix:2.0`, while Roundcube expects an IMAP server on 993 and SMTP submission on 587. The source manifest does not demonstrate a complete, correctly wired IMAP mailbox backend. The mail-server manifest is also in a separate legacy path/namespace from `k8s/services/mail`.
- The current `k8s/services/mail/kustomization.yaml` includes the mail API and Roundcube resources, but no Mailu/Postfix/Dovecot mail-server workload or service. `roundcube-deployment.yaml` points to `mail-server.shopno-mail.svc.cluster.local:993` for IMAP and port 587 for SMTP, while `configmap.yaml` only declares Brevo SMTP relay settings for the mail API. Therefore the checked-in current mail stack does not prove that the Roundcube IMAP/SMTP endpoints exist or that messages can be received and persisted. This is a repository-manifest finding, not a claim about live cluster state.

## Required architecture

1. **Canonical identity:** use the internal canonical user ID for ownership and persist the Keycloak subject separately. Do not assume JWT `sub`, internal user ID, and email local-part are interchangeable.
2. **Idempotent provisioning record/outbox:** create durable provisioning jobs keyed by canonical user ID and resource type (subdomain/mailbox). Unique constraints prevent duplicates. Retry transient errors with bounded backoff and expose `pending/active/failed` status.
3. **Subdomain:** derive a normalized label from the verified account username, enforce reserved-name rules and uniqueness, and provision through the existing FreeDomain service. Do not mark active until the DNS/wildcard-routing policy has been verified.
4. **Mailbox provider:** choose and configure a supported full mail stack (or verified Mailcow deployment) with SMTP submission, IMAP, mailbox storage, TLS, quota enforcement, and per-user mailbox administration. Do not treat an SMTP relay as a mailbox server.
5. **Credentials:** never use a shared/default password. Generate a one-time activation/reset flow or random credential delivered through a verified channel; store only provider-required secrets and never log passwords or tokens.
6. **Provider consistency:** use idempotency/provider lookup and reconciliation so a retry after a timeout does not create duplicate mailboxes. Do not swallow provider errors or report a mailbox as active before provider confirmation.
7. **Authorization:** user-facing endpoints may only read the authenticated user's own subdomain/mailbox; administrative provisioning credentials stay server-side.
8. **Existing users:** provide a dry-run report and controlled backfill with per-user outcomes; do not automatically run a backfill from application startup.
9. **Observability:** log correlation IDs, canonical user ID, resource type, attempt count, and sanitized provider status; never log message contents, passwords, or access tokens.

## Acceptance tests

- New account produces exactly one subdomain and exactly one mailbox.
- Repeated login, duplicate events, concurrent requests, and retries do not create duplicates.
- Username collisions/reserved labels produce a unique safe label.
- DNS or mail-provider outage leaves the account intact and provisioning visibly pending/failed with retry capability.
- Provider rejection/timeout is not reported as success.
- Mailbox password/activation credentials are never hard-coded, returned in ordinary API responses, or written to logs.
- A user cannot inspect or manage another user's mailbox or domain.
- Existing users can be backfilled in dry-run mode first; conflicts are reported and not overwritten.
- Integration test proves actual IMAP login and inbox persistence against the selected mail provider, plus outbound SMTP and inbound delivery where the hosting/network provider supports them.

## Release blockers

- Confirm the actual live mail stack, namespace/service endpoints, TLS, storage, DNS MX/SPF/DKIM/DMARC, and inbound port 25 reachability.
- Confirm the mail provider API and provision a proper secret using the cluster's secret-management process; do not commit API keys.
- Implement and test a worker/reconciler with bounded retry/backoff, safe job claiming, provider idempotency, and sanitized status/error reporting before considering the requirement complete.
- Design a verified mailbox activation/password-reset path; the random provider password is intentionally not returned to the caller.
- Verify the configured Mailcow response contract and configure real provider credentials through secret management. The checked-in API key remains a placeholder.
- Add end-to-end account-to-domain/mailbox tests, including actual IMAP persistence and SMTP/inbound delivery, before claiming full provisioning.
- No migrations, backfills, merge, or deployment are authorized by this change.


## Current branch implementation status (Oct 14, 2026)

- Implemented and unit-tested: idempotent outbox enqueue for normal mirrored users and administrator-created accounts; unique resource constraint; constrained outbox state values; secure provider password generation; Mailcow JSON success validation; rollback/sanitized failures; focused CI regression tests.
- Not implemented: outbox worker, retry/reconciliation loop, user-visible provisioning status/retry endpoint, verified credential activation flow, real provider configuration, verified full mailbox server, DNS/mail delivery integration tests.
- All of the above tests are mock/unit-level. Keep this PR Draft and do not run backfills or deploy as part of these changes.
