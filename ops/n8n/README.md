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

## n8n

The existing WhatsApp inbound/outbound workflows remain inactive until credentials are configured and their end-to-end webhook tests pass.

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

## Release gate

Do not publish/activate the workflows merely because they import successfully. Required checks are:

1. n8n workflow JSON import succeeds.
2. Credential references are resolved.
3. PostgreSQL contract queries succeed.
4. WhatsApp webhook verification succeeds.
5. WhatsApp inbound test creates/updates identity and inbox rows.
6. WhatsApp outbound test sends and logs the provider message ID.
7. At least one account-connect test succeeds for every provider enabled in production.
8. Unsupported actions return a structured non-success result instead of attempting browser automation.
9. GitHub Actions -> GHCR -> ArgoCD/k3s completes successfully.
10. Public endpoint smoke tests pass.
