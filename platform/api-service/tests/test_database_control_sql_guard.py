import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/postgres")

import pytest
from fastapi import HTTPException

from app.api.database_control import _extract_sql_tables


def test_extracts_unquoted_and_quoted_table_references():
    assert _extract_sql_tables("SELECT * FROM public.users") == {("public", "users")}
    assert _extract_sql_tables('SELECT * FROM "public"."users"') == {("public", "users")}
    assert _extract_sql_tables('UPDATE "public"."safe_rows" SET value = 1') == {("public", "safe_rows")}


def test_extracts_joined_tables():
    assert _extract_sql_tables(
        "SELECT u.id FROM public.users u JOIN public.profiles p ON p.user_id = u.id"
    ) == {("public", "users"), ("public", "profiles")}


def test_does_not_treat_table_words_inside_string_literals_as_references():
    assert _extract_sql_tables("SELECT 'FROM public.users' AS example") == set()


def test_rejects_only_parenthesized_table_syntax():
    with pytest.raises(HTTPException) as exc:
        _extract_sql_tables("SELECT * FROM ONLY (public.users)")
    assert exc.value.status_code == 403
