"""Read-only live datastore discovery for the admin control plane.

Discovery observes PostgreSQL and MongoDB metadata only. It never executes
user SQL or generic mutation commands and never grants capabilities.
"""

from __future__ import annotations

import asyncio
import base64
import os
from typing import Any

import asyncpg
import httpx
from pymongo import MongoClient
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.database_control_plane.registry import DATABASE_CAPABILITIES

_SYSTEM_DATABASES = {"postgres", "template0", "template1"}
_EXCLUDED_SCHEMAS = {"pg_catalog", "information_schema"}
_KUBE_TOKEN = "/var/run/secrets/kubernetes.io/serviceaccount/token"
_KUBE_CA = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
_MONGO_SOURCES = (
    {"service": "kobotoolbox", "namespace": "shopno-apps", "secret": "kobotoolbox-mongo-auth", "key": "MONGO_DB_URL"},
)


def _postgres_dsn(database: str) -> str:
    url = make_url(settings.database_url).set(database=database)
    return url.render_as_string(hide_password=False).replace("+asyncpg", "")


def _declared_by_database() -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for item in DATABASE_CAPABILITIES:
        result.setdefault(item.database, []).append(item.service)
    return result


async def _connect(database: str) -> asyncpg.Connection:
    return await asyncio.wait_for(asyncpg.connect(dsn=_postgres_dsn(database)), timeout=3.0)


async def _inspect_database(database: str) -> dict[str, Any]:
    conn = await _connect(database)
    try:
        schemas = [r["schema_name"] for r in await conn.fetch(
            """select schema_name from information_schema.schemata
               where schema_name <> all($1::text[]) order by schema_name""",
            list(_EXCLUDED_SCHEMAS),
        )]
        tables = await conn.fetch(
            """select c.table_schema, c.table_name
               from information_schema.tables c
               where c.table_type = 'BASE TABLE'
                 and c.table_schema <> all($1::text[])
               order by c.table_schema, c.table_name""",
            list(_EXCLUDED_SCHEMAS),
        )
        table_items: list[dict[str, Any]] = []
        for row in tables:
            schema, name = row["table_schema"], row["table_name"]
            columns = await conn.fetch(
                """select column_name, data_type, is_nullable, ordinal_position
                   from information_schema.columns
                   where table_schema=$1 and table_name=$2
                   order by ordinal_position""", schema, name)
            constraints = await conn.fetch(
                """select tc.constraint_name, tc.constraint_type,
                          array_agg(kcu.column_name order by kcu.ordinal_position) as columns
                   from information_schema.table_constraints tc
                   left join information_schema.key_column_usage kcu
                     on kcu.constraint_name=tc.constraint_name
                    and kcu.table_schema=tc.table_schema
                    and kcu.table_name=tc.table_name
                   where tc.table_schema=$1 and tc.table_name=$2
                   group by tc.constraint_name, tc.constraint_type
                   order by tc.constraint_name""", schema, name)
            indexes = await conn.fetch(
                """select indexname, indexdef from pg_indexes
                   where schemaname=$1 and tablename=$2 order by indexname""", schema, name)
            table_items.append({
                "schema": schema,
                "name": name,
                "columns": [dict(r) for r in columns],
                "constraints": [dict(r) for r in constraints],
                "indexes": [dict(r) for r in indexes],
            })
        return {"database": database, "reachable": True, "schemas": schemas, "tables": table_items}
    finally:
        await conn.close()
async def discover_postgres() -> dict[str, Any]:
    """Return live PostgreSQL inventory reconciled with declared capabilities."""
    conn = await _connect(make_url(settings.database_url).database or "postgres")
    try:
        rows = await conn.fetch(
            """select datname, pg_size_pretty(pg_database_size(datname)) as size,
                      pg_database_size(datname) as size_bytes
               from pg_database
               where datallowconn and not datistemplate
               order by datname"""
        )
    finally:
        await conn.close()

    declared = _declared_by_database()
    semaphore = asyncio.Semaphore(3)

    async def inspect(row: Any) -> dict[str, Any]:
        name = row["datname"]
        item: dict[str, Any] = {
            "database": name,
            "size": row["size"],
            "size_bytes": row["size_bytes"],
            "declared_services": declared.get(name, []),
            "declaration_status": "declared" if name in declared else "live_undeclared",
        }
        if name in _SYSTEM_DATABASES:
            item["classification"] = "system"
            item["reachable"] = True
            return item
        async with semaphore:
            try:
                item.update(await asyncio.wait_for(_inspect_database(name), timeout=12.0))
                item["classification"] = "application"
            except Exception as exc:
                item.update({"reachable": False, "error_type": type(exc).__name__})
        return item

    databases = list(await asyncio.gather(*(inspect(row) for row in rows)))

    declared_only = [
        {"database": name, "services": services, "declaration_status": "declared_not_live"}
        for name, services in sorted(declared.items())
        if not any(d["database"] == name for d in databases)
    ]
    return {"databases": databases, "declared_not_live": declared_only}
async def _kubernetes_secret(namespace: str, secret: str, key: str) -> str:
    token = open(_KUBE_TOKEN, encoding="utf-8").read().strip()
    host = os.environ["KUBERNETES_SERVICE_HOST"]
    port = os.environ.get("KUBERNETES_SERVICE_PORT", "443")
    url = f"https://{host}:{port}/api/v1/namespaces/{namespace}/secrets/{secret}"
    async with httpx.AsyncClient(verify=_KUBE_CA, timeout=4.0) as client:
        response = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        response.raise_for_status()
    encoded = response.json()["data"][key]
    return base64.b64decode(encoded).decode()


def _mongo_server_metadata(uri: str) -> list[dict[str, Any]]:
    client = MongoClient(uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000)
    try:
        database_names = [
            name for name in client.list_database_names()
            if name not in {"admin", "config", "local"}
        ]
        databases: list[dict[str, Any]] = []
        for database in sorted(database_names):
            db = client[database]
            collections: list[dict[str, Any]] = []
            for name in sorted(db.list_collection_names()):
                collection = db[name]
                fields = list(collection.aggregate([
                    {"$project": {"pairs": {"$objectToArray": "$$ROOT"}}},
                    {"$unwind": "$pairs"},
                    {"$group": {"_id": "$pairs.k", "types": {"$addToSet": {"$type": "$pairs.v"}}}},
                    {"$sort": {"_id": 1}},
                ]))
                indexes = [
                    {
                        "name": item["name"],
                        "key": list(item["key"].items()),
                        "unique": bool(item.get("unique", False)),
                    }
                    for item in collection.list_indexes()
                ]
                collections.append({
                    "name": name,
                    "estimated_documents": collection.estimated_document_count(),
                    "fields": [
                        {"name": item["_id"], "types": sorted(item["types"])}
                        for item in fields
                    ],
                    "indexes": indexes,
                })
            databases.append({"database": database, "reachable": True, "collections": collections})
        return databases
    finally:
        client.close()


async def discover_mongodb() -> dict[str, Any]:
    declared = _declared_by_database()
    databases: list[dict[str, Any]] = []
    for source in _MONGO_SOURCES:
        try:
            uri = await _kubernetes_secret(source["namespace"], source["secret"], source["key"])
            live_databases = await asyncio.to_thread(_mongo_server_metadata, uri)
            for item in live_databases:
                item["service"] = source["service"]
                item["secret"] = f"{source['namespace']}/{source['secret']}"
                item["declared_services"] = declared.get(item["database"], [])
                item["declaration_status"] = (
                    "declared" if item["database"] in declared else "live_undeclared"
                )
                item["classification"] = "application"
            databases.extend(live_databases)
        except Exception as exc:
            databases.append({
                "service": source["service"],
                "secret": f"{source['namespace']}/{source['secret']}",
                "declaration_status": "source_unavailable",
                "reachable": False,
                "error_type": type(exc).__name__,
            })
    return {"databases": databases}


async def reconcile_postgres() -> dict[str, Any]:
    """Small, bounded reconciliation suitable for an authenticated admin call."""
    result = await discover_postgres()
    live = result["databases"]
    mongo = await discover_mongodb()
    return {
        "version": 2,
        "source": "live-postgresql-and-mongodb",
        "read_only": True,
        "sql_endpoint": False,
        "mongo_write_endpoint": False,
        "summary": {
            "live_databases": len(live),
            "reachable_databases": sum(1 for d in live if d.get("reachable")),
            "live_undeclared": sum(1 for d in live if d.get("declaration_status") == "live_undeclared"),
            "declared_not_live": len(result["declared_not_live"]),
            "mongo_sources": len(mongo["databases"]),
            "mongo_reachable": sum(1 for d in mongo["databases"] if d.get("reachable")),
        },
        "postgres": result,
        "mongodb": mongo,
    }
