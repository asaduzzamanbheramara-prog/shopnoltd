# Social Automation Center - implementation and rollout contract

## Implemented application workflow

- Protected web route: /social-automation.
- API prefix: /api/v1/omnichannel/automation.
- Account connections are per-user OAuth grants; raw passwords are never accepted.
- A user can create two local wall-clock schedule slots per connected account. Defaults are 09:00 and 21:00 in Asia/Dhaka; users may select timezone and weekdays.
- Each due schedule creates one pending_approval draft. The scheduler never calls a provider API.
- Users can edit, approve, reject, pause, resume, and delete their schedules/drafts through the approval inbox.
- Approval is bound to the exact saved content SHA-256, authenticated user, owned connection, active token, and required provider scope.
- Before supported publishing actions, access tokens are checked and refreshed server-side when they expire within five minutes. Token refresh is serialized with database row locks; rotated refresh tokens and provider-supplied refresh expiry are encrypted/persisted. Disconnect cancels queued actions and pauses schedules.
- The scheduler uses UTC instants and timezone-aware wall-clock calculations; nonexistent DST times move to the first valid minute, and ambiguous past folds are skipped.
- The worker uses row locks with SKIP LOCKED and draft idempotency keys so multiple service replicas do not create duplicate drafts.

## Provider identity notes

- X and LinkedIn member posting are the only social create_post adapters currently present. X and LinkedIn refresh support depends on the provider actually issuing a refresh token; LinkedIn programmatic refresh is limited to approved partner apps.
- YouTube OAuth resolves the actual channel ID and requires exactly one channel on the Google account.
- Instagram uses Meta/Facebook Login and requires exactly one linked Instagram Professional account on the selected Facebook login. Multiple linked professional accounts require an account-selection workflow and fail closed.
- TikTok web OAuth uses client_key, comma-separated scopes, and no PKCE challenge; it resolves the data.user identity object. Its rotated refresh token is persisted after every refresh.
- Facebook OAuth identifies the Facebook user profile. Facebook Page publishing is not implemented.
- Instagram, Facebook, YouTube, and TikTok may be connected for account metadata and draft preparation, but they cannot be approved for external publishing until a tested official API adapter is added.
- Likes, comments, shares, follows, live actions, feed scraping, browser-login automation, CAPTCHA/2FA bypass, and engagement farming are not implemented.

## Runtime configuration

Supply credentials only through the runtime secret manager. Never commit them.

- PROVIDER_OAUTH_ENCRYPTION_KEY: valid Fernet key; startup checks format before enabling the executor.
- PROVIDER_OAUTH_STATE_SECRET: secret used to encrypt/validate short-lived OAuth state.
- Provider OAuth client IDs/secrets for Google, Microsoft, LinkedIn, X, Facebook/Instagram, and TikTok.
- OMNICHANNEL_EXECUTOR_ENABLED: defaults to false; keep false until provider sandbox tests, production credentials, backup readiness, and a separate deployment approval are complete.

The Instagram Facebook Login flow uses the Facebook app credentials (FACEBOOK_CLIENT_ID and FACEBOOK_CLIENT_SECRET), not a separate Instagram app credential pair. YouTube channel identification uses the least-privilege youtube.readonly scope. TikTok uses TIKTOK_CLIENT_KEY as its OAuth client_key.

## Database and rollout

Migration: k8s/services/postgres/migration/021-social-automation.sql.

The migration adds per-user connection ownership, two-per-day schedule slots, approval drafts, idempotency, and due/user indexes. It is registered in the PostgreSQL migration Kustomization and runs in the existing migration hook before the service deployment.

The social-service lifespan starts the draft scheduler only after the migration schema check passes. It starts the provider executor only when the schema is ready, the executor flag is explicitly true, and the Fernet encryption key is valid.

## Verification and remaining release gates

- Python syntax compilation and git diff --check are required before commit.
- The frontend production build and PostgreSQL/social-service Kustomize builds must pass.
- Run the social-service pytest suite in the project Python 3.12 container/CI environment; the current WSL host does not have the service Python dependencies or pytest installed. Static helper checks, Python compileall, frontend build, and Kustomize builds are run separately.
- Validate migration 021 against a disposable PostgreSQL database before release.
- Complete OAuth connect/disconnect and provider sandbox end-to-end tests for each provider before enabling its adapter.
- Verify backup/restore readiness, review the final diff, commit and push only after explicit approval.
- No production migration, deployment, provider credential change, executor enablement, account login, external post, like, comment, share, follow, or live action has been performed by this code-only work.
