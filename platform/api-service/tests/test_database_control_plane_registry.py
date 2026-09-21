from app.database_control_plane.registry import DATABASE_CAPABILITIES, catalog


def test_catalog_has_no_unprotected_financial_generic_writes():
    for database in DATABASE_CAPABILITIES:
        for table in database.tables:
            if database.service in {"payment-service", "exchange-service"}:
                assert not table.writable
                assert table.protected_reason


def test_catalog_only_advertises_writable_tables_with_safe_contract():
    data = catalog()
    for database in data:
        for table in database["tables"]:
            if table["writable"]:
                assert table["readable"]
                assert table["protected_reason"] is None
                assert table["ddl"] in {"none", "inspect", "safe", "destructive"}


def test_catalog_is_complete_for_declared_control_plane_domains():
    services = {item["service"] for item in catalog()}
    assert {"payment-service", "billing-engine", "exchange-service", "social/blog", "ai-platform"} <= services
