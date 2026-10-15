"""PostgreSQL integration coverage for outbox checks on pre-existing tables."""
from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.provisioning_migrations import ensure_account_provisioning_constraints


def test_existing_outbox_receives_idempotent_constraints():
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL migration integration test")

    async def exercise_migration():
        engine = create_async_engine(database_url)
        try:
            async with engine.begin() as connection:
                await connection.execute(text("DROP TABLE IF EXISTS account_provisioning_jobs"))
                await connection.execute(text("""
                    CREATE TABLE account_provisioning_jobs (
                        id VARCHAR(64) PRIMARY KEY,
                        user_id VARCHAR(64) NOT NULL,
                        keycloak_id VARCHAR(64) NOT NULL,
                        resource_type VARCHAR(32) NOT NULL,
                        status VARCHAR(16) NOT NULL,
                        attempts INTEGER NOT NULL
                    )
                """))
                # NOT VALID intentionally preserves legacy rows but rejects new invalid writes.
                await connection.execute(text("""
                    INSERT INTO account_provisioning_jobs
                    (id, user_id, keycloak_id, resource_type, status, attempts)
                    VALUES ('legacy', 'u0', 'kc0', 'old-resource', 'old-status', -1)
                """))
                await ensure_account_provisioning_constraints(connection)
                await ensure_account_provisioning_constraints(connection)
                names = (
                    await connection.execute(text("""
                        SELECT conname FROM pg_constraint
                        WHERE conrelid = 'account_provisioning_jobs'::regclass
                    """))
                ).scalars().all()
                assert {
                    "ck_account_provisioning_resource_type",
                    "ck_account_provisioning_status",
                    "ck_account_provisioning_attempts_nonnegative",
                }.issubset(set(names))

                with pytest.raises(IntegrityError):
                    async with connection.begin_nested():
                        await connection.execute(text("""
                            INSERT INTO account_provisioning_jobs
                            (id, user_id, keycloak_id, resource_type, status, attempts)
                            VALUES ('bad', 'u1', 'kc1', 'not-allowed', 'pending', 0)
                        """))

                with pytest.raises(IntegrityError):
                    async with connection.begin_nested():
                        await connection.execute(text("""
                            INSERT INTO account_provisioning_jobs
                            (id, user_id, keycloak_id, resource_type, status, attempts)
                            VALUES ('bad2', 'u2', 'kc2', 'mailbox', 'not-allowed', 0)
                        """))

                with pytest.raises(IntegrityError):
                    async with connection.begin_nested():
                        await connection.execute(text("""
                            INSERT INTO account_provisioning_jobs
                            (id, user_id, keycloak_id, resource_type, status, attempts)
                            VALUES ('bad3', 'u3', 'kc3', 'subdomain', 'pending', -1)
                        """))

                await connection.execute(text("""
                    INSERT INTO account_provisioning_jobs
                    (id, user_id, keycloak_id, resource_type, status, attempts)
                    VALUES ('good', 'u4', 'kc4', 'mailbox', 'pending', 0)
                """))
        finally:
            await engine.dispose()

    asyncio.run(exercise_migration())
