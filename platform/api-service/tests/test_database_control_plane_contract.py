import pytest

from app.database_control_plane.contract import (
    DatabaseCapability,
    DatabaseTableCapability,
    DdlCapabilities,
)


def test_protected_table_cannot_advertise_generic_writes():
    with pytest.raises(ValueError):
        DatabaseTableCapability(
            name="transactions",
            writable=True,
            protected_reason="financial state must use payment service APIs",
        )


def test_writable_table_must_be_readable():
    with pytest.raises(ValueError):
        DatabaseTableCapability(name="settings", readable=False, writable=True)


def test_restore_requires_backup():
    with pytest.raises(ValueError):
        DatabaseCapability(service="billing", database="billing", restore=True)


def test_capability_exposes_writable_and_protected_tables():
    capability = DatabaseCapability(
        service="social",
        database="blog",
        tables=(
            DatabaseTableCapability(name="posts", writable=True, bulk_write=True, importable=True),
            DatabaseTableCapability(
                name="audit_log",
                protected_reason="append-only audit records",
                ddl=DdlCapabilities.INSPECT,
            ),
        ),
    )

    assert capability.writable_tables == ("posts",)
    assert capability.protected_tables == ("audit_log",)
