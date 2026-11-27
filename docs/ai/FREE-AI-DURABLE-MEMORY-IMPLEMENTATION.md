# Free AI and Durable Memory — Implementation Contract

This document defines the release contract for issue #673. It is deliberately separate from runtime configuration: documenting a capability does not enable a provider, create a database table, or deploy a service.

## Verified current behavior

- Agent Auto mode obtains the authenticated active model catalog and chooses only entries whose `capabilities.free_tier` is explicitly true.
- Retryable upstream failures (quota, transient server errors, network/timeouts) put a model into a process-local cooldown and try another eligible free model.
- AI Platform has a database-backed provider/model registry, encrypted provider credentials, and an Ollama provider type that does not require an API key.
- Agent conversation state is currently a process-local `histories: dict[str, list]`; it is not durable across Agent restarts.
- Agent task sinks, active-task tracking, recent-goal rate limits, and model cooldowns are also process-local. Durable task recovery is not implemented.
- Current Agent UI socket authentication has a finite deadline and supports token refresh; this is not equivalent to an indefinite persistent login.

## Product contract

### Free access

1. The default Auto/Free mode may use only active, administrator-verified `free_tier=true` models that are also allowed by the Agent's restricted LiteLLM virtual key.
2. A paid model must never be selected implicitly. Manual paid-model selection requires explicit user selection and a clear cost notice.
3. The UI must identify the selected provider/model, indicate free-tier classification, and explain provider quotas/rate limits. Never describe third-party free tiers as unlimited or guaranteed.
4. If all eligible free models are unavailable, return a clear no-free-model-available response; do not silently switch to a paid model.
5. Ollama is a no-provider-key option only when a reachable, configured local/self-hosted endpoint and model are available. It is not automatically free compute: hardware and hosting costs remain.
6. Provider credentials remain server-side, encrypted at rest in the AI Platform, and absent from browser responses, conversation history, memory, task records, and logs.
7. Add per-user usage controls and abuse protection before making free access public. Do not weaken existing rate limits as a shortcut.

### Conversation history and memory

1. Persist conversation threads and ordered messages in the existing PostgreSQL database, with immutable Keycloak `sub` as the tenant owner.
2. Keep raw conversation history separate from optional distilled memories. Memory is opt-in, user-visible, editable, and retrievable only by its owner.
3. Never store credentials, access/refresh tokens, passwords, payment details, authentication challenges, or sensitive personal data in distilled memory. Apply conservative redaction before persistence and memory extraction.
4. Provide authenticated APIs/UI to list, inspect, pause/resume, export, and delete a user's memories and conversations. Deletion must cascade or reliably tombstone dependent embeddings/index entries.
5. Enforce retention and size limits; make memory opt-out effective immediately. Do not infer consent from ordinary chat use.
6. Retrieve only relevant memories for a conversation, with bounded token/context budgets and source attribution to the user-visible memory records.

### Durable tasks

1. Store task metadata and append-only checkpoints separately from conversation messages.
2. Persist plan updates, completed read-only work, and action intent/result records.
3. Never automatically replay a non-idempotent external action (posting, payment, deletion, submission, message send, etc.) after a crash. Mark uncertain actions as `needs_user_review` and require confirmation/reconciliation against the target website.
4. On restart/reconnect, show interrupted task status and resume only from a verified safe checkpoint.
5. Enforce one active task per user across Agent replicas with database/Redis coordination, not only an in-process set.

## Suggested data model

- `agent_conversations`: UUID id, owner_subject, title, created_at, updated_at, archived_at.
- `agent_messages`: UUID id, conversation_id, owner_subject, sequence, role, content, tool_name, tool_call_id, created_at; unique (conversation_id, sequence).
- `agent_memories`: UUID id, owner_subject, memory_text, category, source_conversation_id, consented_at, updated_at, deleted_at; indexed by owner and status.
- `agent_tasks`: UUID id, owner_subject, conversation_id, status, goal, selected_model, created_at, updated_at, lease_expires_at.
- `agent_task_events`: UUID id, task_id, sequence, event_type, safe_payload, action_idempotency_key, created_at; append-only and unique (task_id, sequence).

All owner-scoped reads, updates, exports, and deletes must include owner_subject in the database predicate; do not trust a client-supplied owner ID. Add migration downgrade/rollback instructions and indexes. Encrypt memory/message content at rest if required by the existing platform security model; do not invent or commit encryption keys.

## Required verification before release

- Unit tests: Auto never chooses paid models; manual paid choice is explicit; free fallback and no-free-model behavior; provider quota errors; cooldown expiry.
- Integration tests: Ollama no-key inference; catalog intersection with the Agent's virtual key; masked provider credentials.
- Isolation tests: two Keycloak subjects cannot list/read/update/export/delete each other's conversations, messages, memories, or tasks.
- Lifecycle tests: memory opt-in/opt-out, pause/resume, export, deletion, retention, redaction, and process restart persistence.
- Recovery tests: restart with a read-only task checkpoint; uncertain external mutation becomes needs_user_review and is not replayed.
- Operational tests: backup/restore, migration rollback, DB pool limits, per-user budgets, rate limiting, readiness, and logs free of secrets/content.
- Staging: real Keycloak login, configured free model and Ollama (if enabled), UI flow, and Agent restart test.

## Rollout safety

No production schema migration, database mutation, provider activation, secret update, replica increase, or deployment is authorized by this document or issue alone. First review migration/backup/rollback, run CI, validate in staging, and check capacity. Preserve the existing single-replica/capacity guardrails. A green build is not proof of a working external provider or live memory.

## Status

Planning/acceptance contract only. Runtime implementation, database migrations, UI controls, CI, staging validation, and production rollout remain separate deliverables tracked by issue #673.
