import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/postgres")

import pytest
from fastapi import HTTPException

from app.api.database_control import _guarded_sql_table_references


def test_extracts_unquoted_and_quoted_table_references():
    assert _guarded_sql_table_references("SELECT * FROM public.users") == {("public", "users")}
    assert _guarded_sql_table_references('SELECT * FROM "public"."users"') == {("public", "users")}
    assert _guarded_sql_table_references('UPDATE "public"."safe_rows" SET value = 1') == {("public", "safe_rows")}


def test_extracts_joined_tables():
    assert _guarded_sql_table_references(
        "SELECT u.id FROM public.users u JOIN public.profiles p ON p.user_id = u.id"
    ) == {("public", "users"), ("public", "profiles")}


def test_does_not_treat_table_words_inside_string_literals_as_references():
    assert _guarded_sql_table_references("SELECT 'FROM public.users' AS example") == set()


def test_rejects_only_parenthesized_table_syntax():
    with pytest.raises(HTTPException) as exc:
        _guarded_sql_table_references("SELECT * FROM ONLY (public.users)")
    assert exc.value.status_code == 403


def test_rejects_unqualified_postgres_system_relations():
    with pytest.raises(HTTPException) as exc:
        _guarded_sql_table_references("SELECT * FROM pg_class")
    assert exc.value.status_code == 403
