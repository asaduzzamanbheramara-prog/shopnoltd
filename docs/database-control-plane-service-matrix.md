# Shopnoltd Cross-Service Database Control-Plane Matrix

This matrix defines the required management boundary for each platform database. It is an inventory and release contract, not permission to mutate arbitrary tables.

| Service / data domain | Management mode | Generic writes | Required management capabilities | Sensitive boundary |
|---|---|---:|---|---|
| payment-service | service API + guarded admin adapter | No | view/search/filter, analysis, exports/reports, audit, backup/restore | wallets, transactions, webhooks read-only; money moves only through validated APIs |
| billing-engine | service API + guarded admin adapter | No for ledger | view/search, analysis, reports, audit, backup/restore | wallet/ledger and billing events remain service-owned |
| exchange-service | service API + admin adapter | No for rate history | view/search, analysis, reports, audit, backup/restore | provider/rate history is updater-owned |
| auth-service | service-specific admin API | No | users/roles lifecycle, search, audit, reports, backup/restore | credentials, tokens, password material never generic CRUD |
| Keycloak | Keycloak administration API | No | realm/client/user/role management, audit/export, backup/restore | secrets, credentials and identity internals are protected |
| domain-service | service API | Controlled | domain records search/edit where explicitly safe, reports, audit, backup | registration, renewal, billing and registrar operations remain transactional |
| freedomain-service | service API | Controlled | tenant/domain search, lifecycle operations, reports, audit, backup | DNS and registrar changes remain validated workflows |
| ai-platform | service API + admin adapter | Controlled | provider/model CRUD, activation, analysis, reports, audit, backup | API keys/secrets never generic CRUD/export |
| social/blog | service API + admin adapter | Yes for content | post CRUD, draft/publish, search, import/export, reports, audit, backup | account/security records protected |
| api-service | service API | No for system state | API resource management, search, reports, audit, backup | auth/session/security state protected |
| audit-service | append-only service | No | search/filter, analysis, export/report, retention controls, backup/restore | historical audit events cannot be edited/deleted generically |
| event-service | service API | No for event history | search/filter, replay through validated workflow, analysis, reports, backup | event/idempotency history protected |
| analytics-service | service API | Controlled | datasets/queries/configuration, dashboards, analysis, reports, export, backup | source-system records remain owned by source service |
| foundation-service | service API | Controlled | tenant/platform configuration CRUD where explicitly safe, reports, audit, backup | identity/security/system secrets protected |
| admin-infrastructure | operator API | No generic DB writes | infrastructure inventory, health, reports, audit, backup orchestration | Kubernetes/control-plane mutations require dedicated privileged workflows |
| KoboToolbox / KoBoCat / Enketo | application-native APIs | Application-defined | forms/projects/submissions management, search, export, analysis, reports, backup | application auth and database internals are not generic CRUD |
| mail data | application-native admin API | Application-defined | mailbox/domain configuration, search, reports, backup | passwords, tokens and message security metadata protected |
| meeting/Jitsi data | application-native APIs | Application-defined | rooms/configuration, usage analysis, reports, backup | authentication/secrets protected |
| object/document storage metadata | service API | Controlled | object metadata search, lifecycle, export/report, backup | object contents and credentials follow storage ACLs |

## Capability contract

Every adapter must explicitly advertise supported operations. Unsupported operations must return a deterministic `403`/`409` rather than silently succeeding or pretending that a feature is native.

Minimum supported read/analysis surface:

- schema and entity inventory
- paginated list/search/filter/sort
- record detail
- validation and duplicate detection
- row counts, null/unique statistics and basic distribution analysis
- CSV/JSON/XLSX export where data policy permits
- bounded PDF reporting where useful
- audit history
- tenant and role enforcement

Where mutation is permitted:

- create/add
- edit/modify/save
- controlled delete with confirmation
- bulk operations
- transactional import with rollback

## Backup and restore contract

- Backup must be named, traceable and auditable.
- Backup storage and database credentials are deployment-managed.
- Restore requires `platform_admin`, explicit confirmation, a reason, and a pre-restore backup.
- Restore must be executed by a privileged operator/job, not by arbitrary HTTP shell execution.
- Checksums, size, timestamps, source database identity and operation status must be retained as metadata.
- Financial/security/audit databases require service-specific restore procedures and post-restore integrity checks.

## Visualization contract

Control-plane UIs should provide responsive HD/4K dashboards with drill-down to authorized records. 3D visualizations are enabled only for multidimensional/temporal/geospatial data where they improve analysis; ordinary tables and financial ledgers remain 2D for accuracy and usability.

## Release gate

A database is complete only when its adapter is classified, its permitted operations are explicit, its sensitive entities are protected, and automated tests cover authorization, tenant isolation, validation, mutation (where allowed), import/export, reporting, audit, and backup/restore safeguards.
