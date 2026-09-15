# Full Database Control Plane — Implementation Plan

This branch implements the full Admin database-management requirement as a capability-driven, service-specific control plane.

## Phase gates

1. Inventory every production database and adapter capability.
2. Implement service adapters for safe CRUD and lifecycle operations.
3. Keep financial, identity, security, audit, tenant-routing and infrastructure invariants behind validated service APIs.
4. Add DDL capabilities only where the adapter can validate names/types/constraints and create an audited recovery point.
5. Add centralized backup/restore orchestration before enabling destructive production operations.
6. Replace the current hard-coded Admin UI service modes with capability-driven controls.
7. Add cross-service analysis/reporting/drill-down.
8. Run RBAC, tenant-isolation, transaction, import/export, backup/restore and live k3s tests.

## Non-negotiable safety rules

- No unrestricted browser SQL.
- No generic writes to payment ledgers, wallets, transactions, webhook state, credentials, OAuth tokens, audit/security state, migration metadata or tenant-routing ownership.
- Destructive database/table operations require platform-admin authorization, explicit confirmation, audit logging and a verified recovery path.
- Every adapter must declare its protected entities and reason.
- The release gate remains failed until every production database has either a tested adapter or an explicit protected/read-only capability declaration.
