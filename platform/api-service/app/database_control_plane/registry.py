"""Central database-control-plane capability registry.

The registry is intentionally declarative. It does not grant database access;
owning services remain responsible for authentication, tenant scoping,
validation, audit logging and execution of every operation.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.database_control_plane.contract import (
    DatabaseCapability,
    DatabaseTableCapability,
    DatastoreKind,
    DdlCapabilities,
)


def _table(name: str, *, writable: bool = False, bulk: bool = False, importable: bool = False,
           destructive: bool = False, protected: str | None = None,
           tenant_scoped: bool = False, ddl: DdlCapabilities = DdlCapabilities.NONE) -> DatabaseTableCapability:
    return DatabaseTableCapability(
        name=name,
        readable=True,
        writable=writable,
        bulk_write=bulk,
        importable=importable,
        exportable=True,
        reportable=True,
        destructive=destructive,
        protected_reason=protected,
        tenant_scoped=tenant_scoped,
        ddl=ddl,
    )


DATABASE_CAPABILITIES: tuple[DatabaseCapability, ...] = (
    DatabaseCapability(
        service="ad-service",
        database="ads",
        schemas=("public",),
        tables=(
            _table("advertisers", protected="advertiser ownership/approval is service-owned"),
            _table("publishers", protected="publisher ownership/approval and revenue share are service-owned"),
            _table("publisher_sites", protected="site verification is service-owned"),
            _table("ad_zones", protected="inventory authorization is service-owned"),
            _table("campaigns", protected="campaign budgets and financial state are service-owned"),
            _table("creatives", protected="creative moderation and destination validation are service-owned"),
            _table("ad_deliveries", protected="delivery ledger is append-only/service-owned"),
            _table("ad_events", protected="event ledger is append-only/service-owned"),
            _table("fraud_events", protected="fraud/security history is append-only"),
            _table("publisher_payouts", protected="payout state is financial/service-owned"),
        ),
        backup=True,
        restore=True,
        tenant_scope="service",
        protected_reason="advertising inventory, delivery and financial events require validated ad-service APIs",
    ),
    DatabaseCapability(
        service="payment-service",
        database="shopnoltd",
        schemas=("public",),
        tables=(
            _table("wallets", protected="wallet balances/frozen funds are changed only by validated wallet APIs", tenant_scoped=True),
            _table("transactions", protected="money-moving transactions are changed only by validated payment APIs", tenant_scoped=True),
            _table("webhook_events", protected="webhook idempotency/security state is service-owned"),
            _table("admin_audit_log", protected="audit history is append-only"),
            _table("direct_payment_accounts", protected="payment-account credentials and routing are service-owned", tenant_scoped=True),
            _table("payment_accounts", protected="payment-account private values and routing are service-owned", tenant_scoped=True),
            _table("direct_payment_intents", protected="payment intents are transactional state", tenant_scoped=True),
            _table("direct_payment_submissions", protected="payment evidence is verification-owned", tenant_scoped=True),
            _table("alembic_version", protected="migration metadata is deployment-owned"),
        ),
        backup=True,
        restore=True,
        tenant_scope="service",
        protected_reason="financial state must remain behind validated service APIs",
    ),
    DatabaseCapability(
        service="billing-engine",
        database="billing",
        tables=(
            _table("users", writable=True, bulk=True, importable=True, tenant_scoped=True),
            _table("subscriptions", writable=True, bulk=True, importable=True, destructive=True, tenant_scoped=True),
            _table("wallets", protected="wallet balances are ledger-owned"),
            _table("transactions", protected="financial transactions are ledger-owned"),
            _table("wallet_ledger_entries", protected="ledger history is append-only"),
            _table("audit_log", protected="audit history is append-only"),
        ),
        backup=True,
        restore=True,
        tenant_scope="service",
    ),
    DatabaseCapability(
        service="exchange-service",
        database="payments",
        tables=(
            _table("rates", protected="rates are owned by the rate updater"),
            _table("conversions", protected="conversion history is audit/financial state"),
        ),
        backup=True,
        restore=True,
        tenant_scope="service",
    ),
    DatabaseCapability(
        service="social/blog",
        database="social",
        tables=(
            _table("blog_posts", writable=True, bulk=True, importable=True, destructive=True, tenant_scoped=True),
            _table("blog_admin_audit", protected="blog administration audit history is append-only", tenant_scoped=True),
        ),
        backup=True,
        restore=True,
        tenant_scope="service",
    ),
    DatabaseCapability(
        service="kobotoolbox",
        database="kpi",
        kind=DatastoreKind.MONGODB,
        tables=(
            _table("instances", protected="Kobo submission records are application-owned and must remain behind Kobo validation/audit flows"),
        ),
        tenant_scope="service",
        protected_reason="Kobo MongoDB data is application-owned; generic writes are disabled",
    ),
    DatabaseCapability(
        service="oauth-service",
        database="oauth",
        tables=(
            _table("users", protected="identity mirror is service-owned"),
            _table("user_profiles", protected="profiles are service-owned; use profile APIs"),
            _table("kyc_identities", protected="government identity data is restricted to KYC/payment/compliance APIs"),
            _table("imported_workbooks", protected="import manifests are importer-owned"),
            _table("imported_excel_rows", protected="source records are importer-owned"),
            _table("secret_vault_entries", protected="encrypted secrets are vault-owned; generic reads/writes are disabled"),
        ),
        backup=True,
        restore=True,
        tenant_scope="service",
        protected_reason="identity, profile and encrypted imported-account data remain service-owned",
    ),
    DatabaseCapability(
        service="ai-platform",
        database="shopnoltd",
        tables=(
            _table("ai_providers", writable=True, bulk=True, importable=True, tenant_scoped=True),
            _table("ai_models", writable=True, bulk=True, importable=True, tenant_scoped=True),
            _table("ai_connections", writable=True, bulk=True, importable=False, destructive=True, tenant_scoped=True),
        ),
        backup=True,
        restore=True,
        tenant_scope="service",
    ),
    # Service databases with read-only live-table discovery. Explicit writable
    # capabilities remain listed above; unknown live tables never gain generic
    # write/import/delete permissions.
    DatabaseCapability(service="auth-service", database="auth", schemas=("public",), backup=True, restore=True),
    DatabaseCapability(service="mobile-api", database="mobile", schemas=("public",), backup=True, restore=True),
    DatabaseCapability(service="meet-service", database="meet", schemas=("public",), backup=True, restore=True),
    DatabaseCapability(service="mail-service", database="mail", schemas=("public",), backup=True, restore=True),
    DatabaseCapability(service="live-service", database="live", schemas=("public",), backup=True, restore=True),
    DatabaseCapability(service="tenant-router", database="router", schemas=("public",), backup=True, restore=True),
    DatabaseCapability(service="event-service", database="events", schemas=("public",), backup=True, restore=True),
    DatabaseCapability(service="report-service", database="reports", schemas=("public",), backup=True, restore=True),
    DatabaseCapability(service="worker-service", database="worker", schemas=("public",), backup=True, restore=True),
    DatabaseCapability(service="domain-service", database="domains", schemas=("public",), backup=True, restore=True),
    DatabaseCapability(service="storage-service", database="storage", schemas=("public",), backup=True, restore=True),
    DatabaseCapability(service="license-service", database="licenses", schemas=("public",), backup=True, restore=True),
    DatabaseCapability(service="interior-service", database="interior", schemas=("public",), backup=True, restore=True),
    DatabaseCapability(service="analytics-service", database="analytics", schemas=("public",), backup=True, restore=True),
    DatabaseCapability(service="foundation-service", database="foundation", schemas=("public",), backup=True, restore=True),

)


def catalog() -> list[dict[str, Any]]:
    """Return a JSON-safe capability catalog for authorized admin clients."""
    return [
        {
            "service": capability.service,
            "database": capability.database,
            "kind": capability.kind.value,
            "schemas": list(capability.schemas),
            "backup": capability.backup,
            "restore": capability.restore,
            "database_ddl": capability.database_ddl.value,
            "tenant_scope": capability.tenant_scope,
            "protected_reason": capability.protected_reason,
            "tables": [asdict(table) | {"ddl": table.ddl.value} for table in capability.tables],
        }
        for capability in DATABASE_CAPABILITIES
    ]
