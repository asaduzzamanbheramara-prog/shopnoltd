from pathlib import Path

from app.scripts.import_legacy_users import email, parse_dump, safe_meta


def test_parse_dump_and_normalize_email(tmp_path: Path):
    dump = tmp_path / "legacy.sql"
    dump.write_text(
        """INSERT INTO users (id,email,full_name,password,nid,avatar_url) VALUES
        (1,'User@Example.COM','Legacy User','dont-import','1234567890','https://img.example/avatar.jpg'),
        (2,NULL,'No Email','secret',NULL,NULL);"""
    )
    rows = parse_dump(dump)
    assert len(rows) == 2
    assert email(rows[0]) == "user@example.com"
    assert email(rows[1]) is None


def test_safe_meta_excludes_credentials_and_kyc():
    row = {
        "display_name": "Legacy",
        "password": "secret",
        "password_hash": "hash",
        "api_key": "key",
        "nid": "1234567890",
        "phone": "+8801000000000",
    }
    meta = safe_meta(row)
    assert meta == {"display_name": "Legacy", "phone": "+8801000000000"}



def test_reset_email_requires_explicit_apply_flag():
    # Guard is enforced by the CLI before run() can access Keycloak or a database.
    import ast
    from pathlib import Path

    source = Path(__file__).parents[1] / "app" / "scripts" / "import_legacy_users.py"
    tree = ast.parse(source.read_text())
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "error"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "--send-reset-emails requires --apply"
    ]
    assert len(calls) == 1


def test_reset_email_helper_uses_short_lifespan():
    import asyncio
    from app.scripts.import_legacy_users import _request_password_reset

    class Response:
        status_code = 204

    class FakeClient:
        async def put(self, url, **kwargs):
            assert url.endswith("/users/kc-user-123/execute-actions-email")
            assert kwargs["params"]["lifespan"] == 1800
            assert kwargs["json"] == ["UPDATE_PASSWORD"]
            return Response()

    assert asyncio.run(_request_password_reset(FakeClient(), "test-token", "kc-user-123")) is True

def test_creating_legacy_identity_does_not_send_email_without_opt_in(monkeypatch):
    import asyncio
    from app.scripts.import_legacy_users import _create_keycloak_user

    class Response:
        status_code = 201
        headers = {"Location": "https://keycloak.example/admin/realms/shopnoltd/users/kc-new-user"}

        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self):
            self.posts = []
            self.puts = []

        async def post(self, url, **kwargs):
            self.posts.append((url, kwargs))
            return Response()

        async def put(self, url, **kwargs):
            self.puts.append((url, kwargs))
            raise AssertionError("identity creation must not send reset email")

    client = FakeClient()
    user, created, reset_sent = asyncio.run(
        _create_keycloak_user(client, "admin-token", {"first_name": "Test"}, "new@example.com")
    )

    assert user["id"] == "kc-new-user"
    assert created is True
    assert reset_sent is False
    assert len(client.posts) == 1
    assert client.puts == []

