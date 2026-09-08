# Shopnoltd AI Platform — Provider and Model Management

The Shopnoltd AI platform provides a database-backed multi-provider model
registry. Provider credentials are encrypted at rest and are never returned
raw by the API. Runtime inference resolves an active model and its provider,
constructs the appropriate adapter, and can fall back to another active model
when the selected model fails.

## Supported provider types

- `openai`
- `anthropic`
- `google` (Gemini)
- `ollama`
- `azure_openai`
- `custom` (OpenAI-compatible endpoint)

Ollama does not require an API key. Credential-backed providers require an
API key before their connectivity test or inference can succeed.

## Credential lifecycle

Provider API keys are accepted only through the authenticated admin provider
API, encrypted with `AI_KEY_ENCRYPTION_KEY`, stored as encrypted database
values, and returned only as masked values. The encryption key is supplied to
the workload through the Kubernetes `ai-platform-encryption` Secret and must
never be committed to Git.

The deployment also imports the normal `ai-platform-secret` for service
configuration. The encryption key is deliberately a separate Secret so it can
be rotated independently of provider records.

## Provider API

The authenticated admin endpoints are:

- `GET /api/ai/providers` — list providers with masked credentials
- `POST /api/ai/providers` — create a provider
- `GET /api/ai/providers/{provider_id}` — inspect provider metadata
- `PATCH /api/ai/providers/{provider_id}` — update provider metadata/credential
- `POST /api/ai/providers/{provider_id}/activate` — enable a provider
- `POST /api/ai/providers/{provider_id}/deactivate` — disable a provider
- `POST /api/ai/providers/{provider_id}/test` — verify provider connectivity/auth
- `DELETE /api/ai/providers/{provider_id}` — remove a provider and its models

The connectivity test is designed to be safe for operators: missing
credentials and provider failures are reported without returning upstream
response bodies, authorization headers, or stored credentials.

## Model API

Models are registered under providers and can be activated/deactivated and
prioritized. Inference selects the requested active model when one is supplied;
otherwise it selects the active default/highest-priority model. If the first
active model fails, the router attempts another active model rather than
silently returning a demo/stub response.

## Runtime configuration

Kubernetes provides:

- `ai-platform-config` ConfigMap for non-secret runtime configuration
- `ai-platform-secret` Secret for service secrets/configuration
- `ai-platform-encryption` Secret containing `AI_KEY_ENCRYPTION_KEY`
- the AI platform Deployment with persistent data storage and readiness checks

The encryption Secret is intentionally not represented as plaintext YAML in
this repository. Provision it through the cluster's secret-management process
before enabling credential-backed providers.

## Operational setup

Generate a Fernet key using the `cryptography` package and provision it as
`AI_KEY_ENCRYPTION_KEY` in the cluster Secret. Do not paste the generated key
into Git, tickets, logs, CI output, or chat.

After deployment, the release validation should cover:

1. provider creation with a test credential;
2. masked credential response (never the raw key);
3. provider connectivity test;
4. model creation and activation;
5. real inference through the platform API;
6. invalid/missing credential handling;
7. fallback to another active provider/model;
8. encryption-key mismatch handling;
9. secret redaction in application errors/logs.

## Important release distinction

A successful Kubernetes build or deployment proves that the AI service can
start; it does **not** prove that an external provider credential is valid.
Each external provider must be tested with its real cluster configuration.
Ollama must likewise be tested against the configured runtime endpoint.

Keep provider credentials in Kubernetes/secret-management infrastructure and
keep the Git repository limited to code, non-secret configuration, manifests,
and documentation.
