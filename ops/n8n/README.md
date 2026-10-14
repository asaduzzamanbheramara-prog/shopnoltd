# Shopnoltd Omnichannel CRM / n8n

This directory is the source-of-truth contract for the n8n omnichannel layer.

## Scope

Supported account families are:

- WhatsApp Business
- Facebook / Messenger
- Instagram Professional
- LinkedIn
- X
- Telegram
- TikTok
- YouTube
- Gmail
- Microsoft Outlook
- 3CX

The platform is intentionally adapter-based. A platform action is only executed when the provider's current API and granted permissions support it. Unsupported actions are returned as unsupported/provider_dependent; the system does not use browser automation to bypass provider restrictions.

## Database

omnichannel-crm.sql creates the shared contract:

- social_connections
- client_platform_identity
- client_conversations
- client_messages
- client_inbox
- platform_actions
- platform_posts
- platform_sync_errors
- platform_capabilities
- automation_rules
- automation_runs

The DDL has already been applied to the production Shopnoltd PostgreSQL database during this implementation. Keep the SQL idempotent and include it in the normal GitOps migration/release process before the next clean rebuild.

## Identity model

A customer is represented by client_id; a platform profile is represented by client_platform_identity.

Example:

    client_id = C123
      WhatsApp -> 88017...
      Instagram -> @customer
      Facebook -> page/user id
      Telegram -> user id
      Email -> customer@example.com

Never treat a platform account as the CRM customer itself.

## Account model

social_connections stores account metadata and references to secret material. Raw OAuth/access/refresh tokens must not be committed to Git or stored in workflow JSON. Use the Shopnoltd secret/credential layer and store only references in this table.

Multiple accounts per platform are supported.

## Action model

platform_actions is the common action queue. Typical actions include:

- search/contact resolution
- send_message
- send_email
- call
- create_post
- schedule_post
- comment
- reply
- like
- reaction
- share
- follow
- unfollow
- friend_request
- live

Availability is recorded in platform_capabilities because provider capabilities and permissions vary.

## Current integration readiness

The account-registry and blog-draft workflows are activated by GitOps but fail closed unless the shared webhook secret is configured. The account registry may use the registration-only internal automation token; the action queue must never use that token. The action queue remains inactive until a separate least-privilege action token and provider-backed end-to-end tests pass. A gated executor foundation is being introduced first; its initial adapter is deliberately limited to Telegram `send_message`. Other providers/actions fail closed as unsupported until their own adapter and tests are implemented. The runtime worker defaults to disabled (`ACTION_WORKER_ENABLED=false`). Provider credentials and OAuth grants must be configured, and each enabled provider must pass a live account-connect and end-to-end test.

**Blog draft intake is wired to n8n** at `POST /webhook/shopnoltd/blog/draft`. It requires `x-shopnoltd-webhook-secret`, accepts title/content metadata, and always creates a draft using the separate `SHOPNOLTD_N8N_BLOG_DRAFT_TOKEN`. That token is allowed to create drafts only; it cannot publish, edit, delete, manage accounts, or queue actions. Human review is required before publication.

The action/account webhook endpoints must also have caller authentication configured in the n8n credential store before production activation. Workflow JSON must not contain credentials or tokens. The action queue deliberately has no API Authorization header until its approved normal-user/service-account credential is wired; unauthenticated calls should be rejected by the API. Never restore `SHOPNOLTD_INTERNAL_AUTOMATION_TOKEN` on the action endpoint. A successful workflow import alone is not a readiness check.

## n8n

The account-registry and blog-draft workflows are imported active with a fail-closed shared-header check. The action queue remains imported inactive until the action executor and its provider-backed end-to-end tests pass.

Recommended workflow groups:

1. Platform account connect/sync
2. Inbound event normalization
3. Client identity resolution
4. Unified inbox/conversation persistence
5. Outbound action router
6. Social publishing/scheduling
7. AI response/approval
8. 3CX call events
9. Error/retry/audit

## Security

Do not commit:

- WhatsApp/Meta access tokens
- OAuth client secrets
- refresh tokens
- n8n API keys
- Postgres passwords
- webhook verification secrets
- 3CX credentials

The PostgreSQL password exposed during the implementation should be rotated before production use.

## Runtime secret contract

The n8n pod receives webhook/action/blog values from the existing `shopno-apps/n8n-secret` through `envFrom`. Configure these keys there:

- `SHOPNOLTD_N8N_WEBHOOK_SECRET`: shared header value required as `x-shopnoltd-webhook-secret` on account-registration and blog-draft webhooks.
- `SHOPNOLTD_N8N_BLOG_DRAFT_TOKEN`: must match `token` in `shopno-platform/shopnoltd-n8n-blog-draft-secret`.
- `SHOPNOLTD_N8N_ACTION_TOKEN`: must match `token` in `shopno-platform/shopnoltd-n8n-action-secret`; action workflow remains inactive until the executor is implemented and tested.

The two `shopno-platform` Secret objects are optional references in deployments so an absent token cannot prevent unrelated website services from starting. Missing credentials cause the automation endpoints to reject requests rather than fall back to the broad internal automation token. Never place any secret values in workflow JSON or Git.

## Release gate

Do not publish/activate the workflows merely because they import successfully. Required checks are:

1. n8n workflow JSON import succeeds and webhook auth rejects missing/wrong secrets.
2. Scoped action and blog-draft credentials are configured in Kubernetes secrets.
3. PostgreSQL contract queries succeed.
4. Provider webhook verification and inbound/outbound tests pass for enabled providers.
5. At least one account-connect test succeeds for every provider enabled in production.
6. Provider-backed action execution is implemented, idempotent, and records provider IDs. The current initial adapter supports Telegram `send_message` only; other actions must remain unsupported until implemented and tested. The worker is disabled by default.
7. Unsupported actions return a structured non-success result instead of attempting browser automation.
8. GitHub Actions -> GHCR -> ArgoCD/k3s completes successfully.
9. Public endpoint smoke tests pass.