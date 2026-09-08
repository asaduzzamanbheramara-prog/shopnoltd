# Shopnoltd Database Control Plane Policy

## Purpose

The database control plane provides platform administration, analysis, import/export, reporting, and controlled record management without exposing arbitrary SQL.

## Generic-write boundary

Generic table mutation is restricted to `platform_admin` and is not a money-moving API.

The following classes must remain read-only through generic CRUD/import:

- wallets and wallet balances/frozen amounts
- financial transactions
- webhook event/idempotency records
- audit/security records
- migration/version metadata
- authentication credentials, tokens, and secrets

Mutations for these domains must go through their service-specific APIs so that authorization, idempotency, ledger invariants, currency validation, gateway capability checks, and audit logging cannot be bypassed.

## Protected system fields

Generic mutation must not permit direct changes to identity, tenancy, lifecycle timestamps, financial balances, approval identity, webhook processing metadata, or other service-managed fields. Examples include:

`id`, `tenant_id`, `created_at`, `updated_at`, `completed_at`, `balance`, `frozen`, `approved_by`, `payload_hash`, `received_at`, `processed_at`.

## Required control-plane capabilities

Each supported database/service adapter should provide, as appropriate:

1. create/add
2. view/search/filter/sort/pagination
3. edit/modify/save
4. controlled delete with confirmation and permissions
5. bulk operations
6. validation and duplicate/unique detection
7. tenant isolation and RBAC
8. complete audit history
9. CSV/JSON/XLSX import/export where appropriate
10. PDF/report generation where appropriate
11. schema/table/database analysis
12. backup/restore safeguards
13. scheduled reports
14. KPI dashboards with drill-down to source records
15. HD/4K responsive visualizations and analytically useful 3D views

## Import/export safety

Imports must be validated against the destination schema and database constraints, execute transactionally, and roll back on failure. Financial records must not be created or altered through generic imports.

Exports must report when a bounded export is truncated and must respect authorization and tenant scope.

## Release gate

Database functionality is not considered complete until every production database has an explicitly classified adapter or service-specific management API and its supported operations have automated tests. A generic table browser alone does not satisfy this gate.
