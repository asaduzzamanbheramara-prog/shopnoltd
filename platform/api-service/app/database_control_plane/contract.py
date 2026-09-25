"""Shared capability contract for the platform-wide admin database control plane.

This module contains no database access. Service adapters publish these
capabilities and enforce the corresponding policy server-side.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class DatastoreKind(str, Enum):
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"


class DdlCapabilities(str, Enum):
    NONE = "none"
    INSPECT = "inspect"
    SAFE = "safe"
    DESTRUCTIVE = "destructive"


@dataclass(frozen=True)
class DatabaseTableCapability:
    name: str
    readable: bool = True
    writable: bool = False
    bulk_write: bool = False
    importable: bool = False
    exportable: bool = True
    reportable: bool = True
    destructive: bool = False
    protected_reason: str | None = None
    tenant_scoped: bool = False
    ddl: DdlCapabilities = DdlCapabilities.NONE

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("table name must not be empty")
        if self.writable and not self.readable:
            raise ValueError("a writable table must also be readable")
        if self.destructive and not self.writable:
            raise ValueError("destructive capability requires writable capability")
        if self.protected_reason and self.writable:
            raise ValueError("protected tables cannot advertise generic writable capability")


@dataclass(frozen=True)
class DatabaseCapability:
    service: str
    database: str
    kind: DatastoreKind = DatastoreKind.POSTGRESQL
    tables: tuple[DatabaseTableCapability, ...] = field(default_factory=tuple)
    schemas: tuple[str, ...] = field(default_factory=tuple)
    backup: bool = False
    restore: bool = False
    database_ddl: DdlCapabilities = DdlCapabilities.NONE
    tenant_scope: str = "service"
    protected_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.service.strip() or not self.database.strip():
            raise ValueError("service and database are required")
        if self.restore and not self.backup:
            raise ValueError("restore capability requires backup capability")
        names = [table.name for table in self.tables]
        if len(names) != len(set(names)):
            raise ValueError("duplicate table capability")

    @property
    def writable_tables(self) -> tuple[str, ...]:
        return tuple(table.name for table in self.tables if table.writable)

    @property
    def protected_tables(self) -> tuple[str, ...]:
        return tuple(table.name for table in self.tables if table.protected_reason)
