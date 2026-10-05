"""Controlled legacy Shopnoltd user reconciler.

Default is dry-run. --apply performs an idempotent reconciliation:
* legacy rows are matched to Keycloak by normalized email;
* existing Keycloak identities keep their real Keycloak UUID;
* missing Keycloak identities are created without importing legacy passwords;
* new identities receive a temporary random password and UPDATE_PASSWORD
  action, and a reset email is requested;
* legacy balances/passwords/tokens/secrets are never imported;
* unmatched records are never represented by synthetic identities.
"""
import argparse
import asyncio
import json
import re
import secrets
from pathlib import Path
from urllib.parse import urlparse

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.db import Base, SessionLocal, engine
from app.core.vault import encrypt_secret
from app.models.models import KYCIdentity, UserMirror, UserProfile

SECRET = re.compile(r"(password|passwd|passcode|secret|token|api.?key|private.?key|otp|2fa)", re.I)
KYC = re.compile(r"(nid|national.?id|passport|government.?id|driving.?licen|date.?of.?birth|birth.?date)", re.I)
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", re.I)
AVATAR = {"profile_pic", "profile_picture", "profile_photo", "avatar", "avatar_url"}
BANNER = {"banner", "banner_url", "cover", "cover_photo", "cover_image"}
SKIP = {"password", "password_hash", "passwd", "token", "api_key", "secret"}


def sql_value(s):
    s = s.strip()
    if s.upper() == "NULL":
        return None
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "'\"":
        q = s[0]
        return s[1:-1].replace(q + q, q).replace("\\'", "'").replace("\\\\", "\\")
    return s


def fields(s):
    out, buf, q, esc, depth = [], [], None, False, 0
    for ch in s:
        if q:
            buf.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == q:
                q = None
        elif ch in "'\"":
            q = ch
            buf.append(ch)
        elif ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            out.append(sql_value("".join(buf)))
            buf = []
        else:
            buf.append(ch)
    if buf:
        out.append(sql_value("".join(buf)))
    return out


def row_groups(values):
    groups, start, q, esc, depth = [], None, None, False, 0
    for i, ch in enumerate(values):
        if q:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == q:
                q = None
            continue
        if ch in "'\"":
            q = ch
        elif ch == "(":
            if depth == 0:
                start = i + 1
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                groups.append(values[start:i])
    return groups


def _users_columns(text):
    match = re.search(r"CREATE\s+TABLE\s+[\x60]users[\x60]\s*\((.*?)\)\s*;", text, re.I | re.S)
    if not match:
        raise RuntimeError("legacy dump does not contain users CREATE TABLE")
    columns = []
    for line in match.group(1).splitlines():
        m = re.match(r"\s*[\x60]([^\x60]+)[\x60]\s+", line)
        if m:
            columns.append(m.group(1).lower())
    if not columns:
        raise RuntimeError("legacy users table has no parseable columns")
    return columns


def parse_dump(path):
    text = Path(path).read_text(errors="replace")
    columns = _users_columns(text)
    rows = []

    # Most MySQL dumps emit one users row per INSERT without a column list.
    # Parse those statements line-by-line so parentheses inside quoted
    # user-agent/address values cannot confuse the row-group scanner.
    for line in text.splitlines():
        match = re.match(r"\s*INSERT\s+INTO\s+[\x60]?users[\x60]?\s+VALUES\s*(\(.*\));\s*$", line, re.I)
        if match:
            vals = fields(match.group(1)[1:-1])
            if len(vals) == len(columns):
                rows.append(dict(zip(columns, vals)))

    if rows:
        return [{str(k).lower(): (None if v is None else str(v).strip()) for k, v in r.items()} for r in rows]

    # Fallback for dumps that use an explicit column list or multiline
    # INSERT statements.
    pattern = re.compile(r"INSERT\s+INTO\s+[\x60]?users[\x60]?\s*\((.*?)\)\s*VALUES\s*(.*?);", re.I | re.S)
    for m in pattern.finditer(text):
        cols = [x.strip().strip(chr(96)).strip('"').lower() for x in m.group(1).split(",")]
        for group in row_groups(m.group(2)):
            vals = fields(group)
            if len(vals) == len(cols):
                rows.append(dict(zip(cols, vals)))
    return [{str(k).lower(): (None if v is None else str(v).strip()) for k, v in r.items()} for r in rows]


def first(row, keys):
    for k in keys:
        if row.get(k):
            return row[k]
    return None


def email(row):
    value = (row.get("email") or row.get("email_address") or "").strip().lower()
    return value if EMAIL.fullmatch(value) else None


def safe_meta(row):
    return {
        k: v
        for k, v in row.items()
        if v not in (None, "")
        and k not in SKIP
        and not SECRET.search(k)
        and not KYC.search(k)
    }


def _admin_configured():
    return (
        bool(settings.keycloak_url)
        and bool(settings.keycloak_admin_user)
        and bool(settings.keycloak_admin_password)
        and settings.keycloak_admin_password != "CHANGE_ME"
    )


async def _kc_admin_token(client):
    if not _admin_configured():
        raise RuntimeError("Keycloak admin credentials are required for --apply")
    r = await client.post(
        f"{settings.keycloak_url.rstrip('/')}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": settings.keycloak_admin_user,
            "password": settings.keycloak_admin_password,
        },
    )
    r.raise_for_status()
    return r.json()["access_token"]


async def _find_keycloak_user(client, token, email_value):
    url = f"{settings.keycloak_url.rstrip('/')}/admin/realms/{settings.keycloak_realm}/users"
    r = await client.get(
        url,
        params={"email": email_value, "exact": "true", "max": 20},
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    matches = [u for u in r.json() if (u.get("email") or "").strip().lower() == email_value]
    if len(matches) > 1:
        raise RuntimeError(f"multiple Keycloak identities match {email_value}")
    return matches[0] if matches else None


async def _create_keycloak_user(client, token, row, email_value):
    url = f"{settings.keycloak_url.rstrip('/')}/admin/realms/{settings.keycloak_realm}/users"
    first_name = first(row, {"first_name", "firstname", "given_name"}) or ""
    last_name = first(row, {"last_name", "lastname", "family_name"}) or ""

    temporary_password = secrets.token_urlsafe(32)
    payload = {
        "username": email_value,
        "email": email_value,
        "firstName": first_name,
        "lastName": last_name,
        "enabled": True,
        "emailVerified": False,
        "requiredActions": ["UPDATE_PASSWORD"],
        "credentials": [{"type": "password", "value": temporary_password, "temporary": True}],
    }
    r = await client.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload)
    if r.status_code == 409:
        existing = await _find_keycloak_user(client, token, email_value)
        if existing:
            return existing, False, False
    r.raise_for_status()

    location = r.headers.get("Location", "")
    user_id = urlparse(location).path.rstrip("/").split("/")[-1] if location else ""
    if not user_id:
        existing = await _find_keycloak_user(client, token, email_value)
        if not existing:
            raise RuntimeError(f"Keycloak created {email_value} but returned no identity")
        user_id = existing["id"]

    reset_sent = False
    reset = await client.put(
        f"{url}/{user_id}/execute-actions-email",
        params={"lifespan": 86400, "client_id": "shopnoltd-web", "redirect_uri": "https://shopnoltd.dpdns.org/"},
        headers={"Authorization": f"Bearer {token}"},
        json=["UPDATE_PASSWORD"],
    )
    if reset.status_code in (204, 200):
        reset_sent = True
    return {"id": user_id, "email": email_value, "enabled": True}, True, reset_sent


async def run(path, apply):
    rows = parse_dump(path)
    report = {
        "source_rows": len(rows),
        "eligible": 0,
        "created": 0,
        "matched": 0,
        "profiles": 0,
        "kyc": 0,
        "avatars": 0,
        "banners": 0,
        "skipped_no_email": 0,
        "balances_imported": 0,
        "keycloak_created": 0,
        "keycloak_matched": 0,
        "passwords_imported": 0,
        "reset_emails_sent": 0,
        "reset_email_failures": 0,
        "mode": "apply" if apply else "dry-run",
    }

    if not apply:
        for r in rows:
            e = email(r)
            if not e:
                report["skipped_no_email"] += 1
                continue
            report["eligible"] += 1
            if first(r, AVATAR):
                report["avatars"] += 1
            if first(r, BANNER):
                report["banners"] += 1
            if any(KYC.search(k) and r.get(k) for k in r):
                report["kyc"] += 1
        print(json.dumps(report, indent=2))
        return report

    if not _admin_configured():
        raise RuntimeError("Refusing --apply: Keycloak admin credentials are not configured")

    async with httpx.AsyncClient(timeout=30) as client:
        token = await _kc_admin_token(client)
        async with engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)

        async with SessionLocal() as s:
            for r in rows:
                e = email(r)
                if not e:
                    report["skipped_no_email"] += 1
                    continue
                report["eligible"] += 1

                kc = await _find_keycloak_user(client, token, e)
                created_kc = False
                reset_sent = False
                if not kc:
                    kc, created_kc, reset_sent = await _create_keycloak_user(client, token, r, e)
                    if created_kc:
                        report["keycloak_created"] += 1
                    if reset_sent:
                        report["reset_emails_sent"] += 1
                    else:
                        report["reset_email_failures"] += 1
                else:
                    report["keycloak_matched"] += 1

                keycloak_id = kc["id"]
                u = (await s.execute(select(UserMirror).where(UserMirror.email == e))).scalar_one_or_none()
                by_kc = (await s.execute(select(UserMirror).where(UserMirror.keycloak_id == keycloak_id))).scalar_one_or_none()

                if u and u.keycloak_id != keycloak_id:
                    raise RuntimeError(f"identity conflict for {e}: email maps to {u.keycloak_id}, Keycloak maps to {keycloak_id}")
                if by_kc and by_kc.email != e:
                    raise RuntimeError(f"identity conflict for {e}: Keycloak identity already belongs to {by_kc.email}")

                if not u:
                    u = UserMirror(
                        keycloak_id=keycloak_id,
                        identity_source="legacy_sql",
                        source_sheet="users",
                        source_row=int(r.get("id")) if str(r.get("id") or "").isdigit() else None,
                        email=e,
                        name=first(r, {"full_name", "fullname", "name"}) or e.split("@")[0],
                        roles=[],
                        active=bool(kc.get("enabled", True)),
                    )
                    s.add(u)
                    await s.flush()
                    report["created"] += 1
                else:
                    report["matched"] += 1
                    if u.identity_source != "legacy_sql":
                        u.identity_source = "legacy_sql"
                    u.keycloak_id = keycloak_id
                    u.active = bool(kc.get("enabled", True))

                p = (await s.execute(select(UserProfile).where(UserProfile.user_id == u.id))).scalar_one_or_none()
                if not p:
                    p = UserProfile(user_id=u.id, source="legacy_sql")
                    s.add(p)
                p.first_name = p.first_name or first(r, {"first_name", "firstname", "given_name"})
                p.last_name = p.last_name or first(r, {"last_name", "lastname", "family_name"})
                p.display_name = p.display_name or first(r, {"full_name", "fullname", "display_name", "name"}) or u.name
                p.gender = p.gender or r.get("gender")
                p.phone = p.phone or first(r, {"phone", "mobile", "fullphone", "phone_number"})
                av = first(r, AVATAR)
                bn = first(r, BANNER)
                if not p.avatar_url and av:
                    p.avatar_url = av
                    report["avatars"] += 1
                if not p.banner_url and bn:
                    p.banner_url = bn
                if bn:
                    report["banners"] += 1
                meta = p.profile_metadata or {}
                meta.update(safe_meta(r))
                meta["legacy_user_id"] = r.get("id") or r.get("user_id")
                meta["legacy_balance_ignored"] = True
                meta["legacy_password_ignored"] = True
                p.profile_metadata = meta
                report["profiles"] += 1

                ids = {k: v for k, v in r.items() if v and KYC.search(k)}
                if ids:
                    k = (await s.execute(select(KYCIdentity).where(KYCIdentity.user_id == u.id))).scalar_one_or_none()
                    if not k:
                        k = KYCIdentity(user_id=u.id, verification_status="pending")
                        s.add(k)
                    k.legal_name = k.legal_name or first(r, {"full_name", "fullname", "name"})
                    k.date_of_birth = k.date_of_birth or first(r, {"birth_date", "date_of_birth", "dob"})
                    k.nationality = k.nationality or first(r, {"nationality", "country_name"})
                    gov = first(r, {"nid", "nid_number", "national_id", "passport", "passport_number", "government_id", "government_id_number"})
                    if gov and not k.encrypted_government_id:
                        k.government_id_type = "nid" if any(x in r for x in ("nid", "nid_number", "national_id")) else "government_id"
                        k.government_id_last4 = gov[-4:]
                        k.encrypted_government_id = encrypt_secret(gov)
                    k.kyc_metadata = {a: b for a, b in ids.items() if a not in {"nid", "nid_number", "national_id", "passport", "passport_number", "government_id", "government_id_number"}}
                    report["kyc"] += 1

            await s.commit()

    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    asyncio.run(run(a.dump, a.apply))
