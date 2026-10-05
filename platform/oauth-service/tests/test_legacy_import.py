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
