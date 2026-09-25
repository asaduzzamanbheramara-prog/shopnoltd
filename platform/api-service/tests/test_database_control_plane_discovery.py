import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/postgres")

from app.database_control_plane.discovery import _declared_by_database, _postgres_dsn


def test_declared_database_map_preserves_service_ownership():
    data = _declared_by_database()
    assert "shopnoltd" in data
    assert "payment-service" in data["shopnoltd"]
    assert "ai-platform" in data["shopnoltd"]


def test_postgres_dsn_replaces_only_database_name():
    dsn = _postgres_dsn("example_database")
    assert "example_database" in dsn
    assert "+asyncpg" not in dsn
