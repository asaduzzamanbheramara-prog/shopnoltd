# Shopnoltd Omnichannel Provider Credentials

This document describes the **server-side integration credentials** for Shopnoltd administrators and the **account-connection steps** for ordinary users. Never put real credentials in Git, tickets, chat, screenshots, or frontend environment variables.

## Who configures what?

- **Shopnoltd administrator:** registers/maintains the provider developer app, configures callback URLs and permissions, and stores app credentials in the existing Kubernetes Secret Manager entry `social-service-secret`.
- **Shopnoltd user:** signs in to Shopnoltd, opens Dashboard → Platform Accounts, chooses Connect where available, signs in directly with the provider, grants consent, and selects their own Page/channel/account. User tokens are stored encrypted and scoped to the user's tenant/account.
- **Provider:** owns the user's password and login challenge. Shopnoltd must never ask for or store provider passwords.

A shared Shopnoltd developer app is used where the provider's terms permit it. Some products (notably WhatsApp Business and 3CX) also need business-asset onboarding or tenant-specific API configuration; credentials alone do not complete that setup.

## Server secret keys

Store only the keys needed for providers you are enabling. Existing keys in `social-service-secret` must be preserved when adding new keys.

| Provider | Secret key names | User connection method / caveat |
|---|---|---|
| Facebook | `FACEBOOK_CLIENT_ID`, `FACEBOOK_CLIENT_SECRET` | OAuth; keep the separate Shopno Business Connection Meta app. |
| Instagram | `INSTAGRAM_CLIENT_ID`, `INSTAGRAM_CLIENT_SECRET` (optional if reusing Facebook app) | Meta OAuth; eligible professional account/Page linkage and permissions required. |
| Google / Gmail / YouTube | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | OAuth; enable Gmail API and YouTube Data API and request only required scopes. |
| Microsoft / Outlook | `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET` | Microsoft Entra app + delegated Graph permissions and admin consent if required. |
| LinkedIn | `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET` | OAuth; product/API access and member/org permissions depend on action. |
| X | `X_CLIENT_ID`, `X_CLIENT_SECRET` | OAuth 2.0; X API access/tier and write permissions required for posting. |
| TikTok | `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET` | Web Login Kit; app review and Content Posting approval are separate from basic identity access. |
| Telegram | `TELEGRAM_BOT_TOKEN` | Bot API, not user OAuth. Admin creates the bot; user must add the bot to the relevant chat/channel with the required permissions. |
| WhatsApp | `WHATSAPP_CLIENT_ID`, `WHATSAPP_CLIENT_SECRET` | Meta app credentials are not enough by themselves; WhatsApp Business onboarding, phone-number/business asset, webhook and approved messaging setup are required. |
| 3CX | `THREECX_CLIENT_ID`, `THREECX_CLIENT_SECRET`, `THREECX_BASE_URL` | Provider/API-specific setup; base URL and tenant permissions must be confirmed with the 3CX administrator. |

OAuth redirect URI to register with providers:
`https://shopnoltd.dpdns.org/connections/oauth/callback`

Use provider-approved production app settings and least-privilege scopes. Do not enable a provider's write scope until the corresponding action is implemented and tested.

## Safely merge new keys into the existing Kubernetes Secret

Create a private env file on the authorized administrator workstation (not in the repository), for example `shopnoltd-provider-secrets.env`. Put one `KEY=value` per line. Do not wrap values in shell commands, and do not commit this file.

The following pattern merges only the keys in that file into the existing Secret; it does **not** replace the Secret's other keys:

```bash
chmod 600 shopnoltd-provider-secrets.env
PATCH="$(kubectl create secret generic social-service-secret \
  -n shopno-platform \
  --from-env-file=shopnoltd-provider-secrets.env \
  --dry-run=client -o json | jq -c '{data: .data}')"
kubectl patch secret social-service-secret \
  -n shopno-platform --type=merge -p "$PATCH"
unset PATCH
```

Verify key names only—never print decoded values:

```bash
kubectl get secret social-service-secret -n shopno-platform \
  -o json | jq -r '.data | keys[]' | sort
```

The social-service reads Secret values at process start. A rollout restart is needed before new values appear in running Pods. Do this only through the approved release/change process; do not restart or deploy production just to test an unreviewed PR.

## User workflow

1. User signs in to Shopnoltd.
2. Opens Dashboard → Platform Accounts.
3. Clicks Connect for a provider marked ready.
4. Completes provider-hosted login and consent (Shopnoltd never sees their password).
5. Selects the Page/channel/account if the provider returns multiple choices.
6. Shopnoltd automatically binds the connection to the authenticated Shopnoltd user ID and tenant ID, encrypts the provider tokens, and records granted scopes and expiry.
7. The connection list, detail, update, disconnect and action-execution paths enforce that same owner ID; another user cannot see, edit, disconnect or execute against it.
8. Token refresh, expiry tracking and reconnect status are handled by the service where the provider supports them. Users do not need to copy tokens or configure IDs manually.
9. User disconnects from the same page to delete the stored connection and encrypted credentials.

Users should not enter shared app client secrets. For Telegram, WhatsApp Business and 3CX, an administrator may need to onboard the bot/business asset/tenant first; then the user can use the asset they are authorized to manage.

## Readiness meanings

- **Needs credentials:** required server-side app keys are absent.
- **Ready to authorize:** OAuth app credentials are present; provider permissions and user consent still apply.
- **Bot configured:** Telegram bot token exists; the bot still must be added to a chat/channel.
- **Business onboarding required:** WhatsApp app credentials exist, but business/phone-number/webhook onboarding remains.
- **API details present — validation needed:** 3CX client details and base URL are present, but the adapter and tenant permissions still need verification.
- **Planned:** no working adapter/OAuth flow yet. Do not show a Connect button or claim the feature works.

## Additional platforms

Discord, Slack, Pinterest, Snapchat, Reddit, Twitch, Shopify, WooCommerce, Zoom and Google Business Profile can be added through the provider registry. They are **not automatically working** just because they are listed: each needs a provider adapter, OAuth/webhook implementation, user/tenant isolation, supported-action definitions, tests, and any required provider review. Add them as Planned until those checks pass.

## Safety and release gates

- Keep `OMNICHANNEL_EXECUTOR_ENABLED=false` until sandbox end-to-end tests, permissions, approval controls and token refresh/revoke tests pass.
- Never log access tokens, refresh tokens, client secrets, authorization codes or OAuth state.
- Never use one user's connection for another user or tenant.
- Every social_connections row must carry owner_user_id; migration 026-omnichannel-user-ownership.sql backfills owners from existing OAuth token records. Legacy rows with no provable owner remain hidden until explicitly reconciled.
- The database keeps provider-account ownership exclusive within a tenant by default. Shared workspace access must be a separate explicit grant model, never an OAuth token overwrite.
- Keep app credentials server-side and encrypt per-user OAuth tokens at rest.
- Do not enable unimplemented actions merely because they appear in a capability table.
