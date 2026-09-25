"""Central database-control-plane capability registry.

The registry is intentionally declarative. It does not grant database access;
owning services remain responsible for authentication, tenant scoping,
validation, audit logging and execution of every operation.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.database_control_plane.contract import DatabaseCapability, DatabaseTableCapability, DdlCapabilities


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




# Production stores discovered during the September 2026 live inventory.
# These are inventory records, not grants. A store remains unavailable for
# generic browser CRUD until its owning adapter publishes validated operations.
PRODUCTION_DATABASE_INVENTORY: tuple[dict[str, str], ...] = (
    {"service": "chatwoot", "database": "chatwoot", "mode": "application", "status": "adapter-required"},
    {"service": "chatwoot", "database": "chatwoot_production", "mode": "application", "status": "adapter-required"},
    {"service": "guacamole", "database": "guacamole", "mode": "application", "status": "adapter-required"},
    {"service": "keycloak", "database": "keycloak", "mode": "identity-protected", "status": "protected"},
    {"service": "kobotoolbox", "database": "kobocat", "mode": "application", "status": "adapter-required"},
    {"service": "kpi", "database": "kpi", "mode": "analytics", "status": "adapter-required"},
    {"service": "litellm", "database": "litellm", "mode": "AI-infrastructure", "status": "adapter-required"},
    {"service": "owncast", "database": "live", "mode": "application", "status": "adapter-required"},
    {"service": "mail", "database": "mail", "mode": "application", "status": "adapter-required"},
    {"service": "jitsi", "database": "meet", "mode": "application", "status": "adapter-required"},
    {"service": "messaging", "database": "messaging", "mode": "application", "status": "adapter-required"},
    {"service": "metabase", "database": "metabase", "mode": "application", "status": "adapter-required"},
    {"service": "n8n", "database": "n8n", "mode": "automation", "status": "adapter-required"},
    {"service": "postgresql", "database": "postgres", "mode": "system", "status": "protected"},
    {"service": "payment-service", "database": "payments", "mode": "financial", "status": "service-controlled"},
    {"service": "session-manager", "database": "session_manager", "mode": "security", "status": "protected"},
    {"service": "shopnoltd", "database": "shopnoltd", "mode": "platform", "status": "adapter-required"},
    {"service": "social", "database": "social", "mode": "content", "status": "adapter-required"},
)

DATABASE_CAPABILITIES: tuple[DatabaseCapability, ...] = (
    DatabaseCapability(
        service="payment-service",
        database="payment",
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
        database="exchange",
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
        service="ai-platform",
        database="ai",
        tables=(
            _table("ai_providers", writable=True, bulk=True, importable=True, tenant_scoped=True),
            _table("ai_models", writable=True, bulk=True, importable=True, tenant_scoped=True),
            _table("ai_connections", writable=True, bulk=True, importable=False, destructive=True, tenant_scoped=True),
            _table("provider_credentials", protected="provider secrets must never be generic-readable/exportable"),
        ),
        backup=True,
        restore=True,
        tenant_scope="service",
    ),
)


def catalog() -> list[dict[str, Any]]:
    """Return a JSON-safe capability catalog for authorized admin clients."""
    return [
        {
            "service": capability.service,
            "database": capability.database,
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
