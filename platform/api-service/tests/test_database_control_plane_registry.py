from app.database_control_plane.contract import DatastoreKind
from app.database_control_plane.access import resolve_table_capability
from app.database_control_plane.discovery import _mongo_database_names
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
    assert {"payment-service", "billing-engine", "exchange-service", "social/blog", "ai-platform", "kobotoolbox"} <= services


def test_mongodb_capability_is_read_only_and_typed():
    item = next(item for item in catalog() if item["service"] == "kobotoolbox")
    assert item["database"] == "formhub"
    assert item["kind"] == DatastoreKind.MONGODB.value
    collection = next(table for table in item["tables"] if table["name"] == "instances")
    assert collection["readable"] is True
    assert collection["writable"] is False
    assert collection["protected_reason"]


def test_protected_capabilities_never_advertise_generic_writes():
    for database in DATABASE_CAPABILITIES:
        for table in database.tables:
            if table.protected_reason:
                assert table.writable is False
                assert table.bulk_write is False
                assert table.importable is False



def test_capability_cannot_cross_declared_schema_boundary():
    from app.database_control_plane.access import resolve_table_capability

    declared = resolve_table_capability("social", "blog_posts", "public")
    undeclared = resolve_table_capability("social", "blog_posts", "other_schema")

    assert declared["writable"] is True
    assert undeclared["writable"] is False
    assert undeclared["status"] == "discovered_read_only"



def test_postgres_kpi_and_mongodb_formhub_are_distinct_datastores():
    postgres_kpi = resolve_table_capability("kpi", "instances", "public")
    mongo_instances = resolve_table_capability(
        "formhub", "instances", kind=DatastoreKind.MONGODB
    )

    assert postgres_kpi["status"] == "discovered_read_only"
    assert postgres_kpi["readable"] is False
    assert postgres_kpi["writable"] is False
    assert postgres_kpi["exportable"] is False
    assert mongo_instances["status"] == "declared"
    assert mongo_instances["readable"] is False
    assert mongo_instances["writable"] is False


def test_registry_declares_live_postgres_stores_without_granting_generic_writes():
    declared = {
        item.database
        for item in DATABASE_CAPABILITIES
        if item.kind == DatastoreKind.POSTGRESQL
    }
    expected = {
        "audit", "chatwoot_production", "freedomain", "keycloak",
        "kobocat", "kpi", "litellm", "notifications",
        "session_manager", "training",
    }
    assert expected <= declared


def test_mongo_inventory_includes_configured_database_before_first_collection():
    class FakeDatabase:
        name = "formhub"

    class FakeMongoClient:
        def list_database_names(self):
            return ["admin", "config", "local"]

        def get_default_database(self):
            return FakeDatabase()

    assert _mongo_database_names(FakeMongoClient()) == ["formhub"]



def test_unknown_live_tables_are_metadata_only_by_default():
    capability = resolve_table_capability("keycloak", "user_entity", "public")
    assert capability["status"] == "discovered_read_only"
    assert capability["readable"] is False
    assert capability["writable"] is False
    assert capability["exportable"] is False
    assert capability["reportable"] is False


def test_registry_includes_expected_tables_for_empty_application_databases():
    expected = {
        ("auth", "sessions"),
        ("live", "streams"),
        ("meet", "rooms"),
        ("messaging", "messages"),
        ("session_manager", "profiles"),
        ("notifications", "notifications"),
        ("audit", "audit_logs"),
        ("training", "courses"),
        ("router", "tenant_routes"),
        ("domains", "registrars"),
        ("storage", "professional_profiles"),
        ("mobile", "app_releases"),
        ("analytics", "events"),
        ("reports", "reports"),
        ("worker", "tasks"),
        ("foundation", "beneficiaries"),
        ("interior", "interior_rooms"),
        ("licenses", "licenses"),
        ("events", "event_tickets"),
        ("ai", "ai_conversations"),
        ("oauth", "account_provisioning_jobs"),
        ("mail", "mail_messages"),
        ("social", "blog_posts"),
        ("payments", "rates"),
    }
    declared = {
        (database.database, table.name)
        for database in DATABASE_CAPABILITIES
        for table in database.tables
    }
    assert expected <= declared


def test_no_generic_table_write_or_backup_restore_is_advertised():
    assert all(not table.writable for db in DATABASE_CAPABILITIES for table in db.tables)
    assert all(not db.backup and not db.restore for db in DATABASE_CAPABILITIES)
