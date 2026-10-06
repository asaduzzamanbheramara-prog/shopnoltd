"""Safe capability resolution for live database objects."""
from __future__ import annotations

from app.database_control_plane.registry import DATABASE_CAPABILITIES


def resolve_table_capability(database: str, table: str, schema: str | None = None) -> dict:
    """Resolve a live table to an explicit capability without granting unknown writes.

    A capability is only applicable inside one of the registry-declared schemas.
    This prevents a same-named table in an undeclared schema from inheriting
    generic write privileges.
    """
    matches = [c for c in DATABASE_CAPABILITIES if c.database == database and (schema is None or schema in c.schemas)]
    for database_capability in matches:
        for capability in database_capability.tables:
            if capability.name == table:
                return {
                    "status": "declared",
                    "readable": capability.readable,
                    "writable": capability.writable,
                    "bulk_write": capability.bulk_write,
                    "importable": capability.importable,
                    "exportable": capability.exportable,
                    "reportable": capability.reportable,
                    "destructive": capability.destructive,
                    "protected_reason": capability.protected_reason,
                    "tenant_scoped": capability.tenant_scoped,
                    "ddl": capability.ddl.value,
                }
    return {
        "status": "discovered_read_only",
        "readable": True,
        "writable": False,
        "bulk_write": False,
        "importable": False,
        "exportable": True,
        "reportable": True,
        "destructive": False,
        "protected_reason": "Live table is not explicitly allowlisted for generic writes",
        "tenant_scoped": False,
        "ddl": "inspect",
    }
