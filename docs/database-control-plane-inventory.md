# Shopnoltd Database Control Plane Inventory

## Purpose

The platform database requirement is broader than the payment-service admin tables API. Every database-backed service must expose controlled administration appropriate to its data domain while preserving tenant isolation, RBAC, auditability, transactional integrity, and service-specific invariants.

## Database-backed service families identified

The repository contains independent SQLAlchemy/database layers in at least these service families:

| Service | Database layer evidence | Control-plane status |
|---|---|---|
| payment-service | `platform/payment-service/app/core/db.py` and payment models | Foundation present; generic financial writes must remain protected |
| billing-engine | `billing-engine` models/database configuration | Requires service-specific admin adapter |
| exchange-service | `platform/exchange-service` database layer | Requires service-specific admin adapter |
| domain-service | `platform/domain-service` models/database layer | Requires controlled CRUD/admin adapter |
| auth-service | `platform/auth-service/app/core/db.py` | Security-sensitive; generic writes should be prohibited |
| oauth-service | `platform/oauth-service/app/core/db.py` | Security-sensitive; generic writes should be prohibited |
| tenant-router | `platform/tenant-router/app/core/db.py` | Tenant/routing-sensitive; controlled adapter required |
| gateway | `platform/gateway/app/core/db.py` | Operational configuration; controlled adapter required |
| api-service | `platform/api-service/app/core/db.py` | Prefer service APIs; adapter only where administration is safe |
| mail-service | `platform/mail-service/app/core/db.py` | Controlled operational/content administration required |
| meet-service | `platform/meet-service/app/core/db.py` | Controlled operational/content administration required |
| event-service | `platform/event-service/app/core/db.py` | Event/audit data requires protected append/read semantics |
| audit-service | `platform/audit-service/app/core/db.py` | Audit data should be immutable/read-only to generic CRUD |
| worker-service | `platform/worker-service/app/core/db.py` | Inspect models and expose only safe operational administration |
| AI platform | `platform/ai-platform/app/core/db.py` and `ai-platform/backend/app/database.py` | Provider/model/usage administration requires controlled APIs |
| mobile-api | `platform/mobile-api/app/core/db.py` | Prefer API/service operations; controlled admin coverage required |
| social/blog domains | social/blog persistence layers | Content CRUD/publish workflow required |

This inventory is intentionally conservative: a database layer does not by itself imply that unrestricted generic CRUD is safe.

## Required capability contract

Each database-backed service must provide, as applicable:

1. schema/table/entity discovery;
2. authenticated and RBAC-protected list/search/filter/sort/pagination;
3. validated create/read/update/delete for safe entities;
4. bulk edit/delete with explicit destructive confirmation;
5. tenant scoping and platform-admin global scope only where authorized;
6. schema-aware type, nullability, enum, length, foreign-key and uniqueness validation;
7. duplicate detection before bulk imports where practical;
8. transactional CSV/JSON/XLSX import and CSV/JSON/XLSX export;
9. report/PDF generation where the entity is reportable;
10. audit history for every mutation and administrative action;
11. backup/restore workflows with privileged authorization and audit records;
12. dashboards/KPIs with drill-down to source records;
13. scheduled reports where operationally useful;
14. HD/4K responsive visualization and interactive 3D only where analytically useful;
15. no unrestricted raw SQL for ordinary administrators;
16. service-specific mutation APIs for money, identity, security, ledger, webhook, and other invariant-sensitive data.

## Financial safety boundary

The payment-service generic database surface treats wallets, transactions, webhook events, audit records, and migration metadata as read-only. Balances, frozen amounts, transaction status, approval state, identifiers, timestamps, and webhook processing state must not be changed by generic table CRUD/import. Financial state changes must flow through validated domain APIs with idempotency, authorization, transaction locking, and audit logging.

The same principle applies to other sensitive domains: identity credentials, OAuth tokens, security/audit records, routing ownership, ledger entries, and infrastructure control state must not become writable merely because a SQL table is discoverable.

## Implementation order

1. Harden the payment database control plane and add schema-aware validation/import/export.
2. Add billing-engine and exchange-service adapters because they are financially critical.
3. Add domain, tenant, auth/OAuth, gateway, event/audit, mail/meet/social/blog, AI and remaining service adapters.
4. Add centralized backup/restore orchestration.
5. Connect the web admin UI to service/database capabilities instead of assuming one database.
6. Add cross-service analytics and visualization only through authorized APIs.
7. Run unit/integration/security tests and live k3s QA before release.

## Release gate

The database requirement is **NOT COMPLETE** until every production database has either:

- a safe service-specific control API covering its required administrative operations, or
- an explicitly documented read-only/protected status with an appropriate reason.

A generic SQL/table browser alone is not considered complete platform database administration.
