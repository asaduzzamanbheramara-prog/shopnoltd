"""Controlled one-time legacy Shopnoltd users importer.
Default is dry-run; --apply writes. Legacy wallet/balance values are never imported.
Government IDs are encrypted in the protected KYC table. Avatar/banner fields are preserved.
"""
import argparse, asyncio, json, re, uuid
from pathlib import Path
from sqlalchemy import select
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
    if s.upper() == "NULL": return None
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "'\\"":
        q = s[0]
        return s[1:-1].replace(q + q, q).replace("\\\\'", "'").replace("\\\\\\\\", "\\\\")
    return s

def fields(s):
    out, buf, q, esc, depth = [], [], None, False, 0
    for ch in s:
        if q:
            buf.append(ch)
            if esc: esc = False
            elif ch == "\\\\": esc = True
            elif ch == q: q = None
        elif ch in "'\\"":
            q = ch; buf.append(ch)
        elif ch == "(":
            depth += 1; buf.append(ch)
        elif ch == ")":
            depth -= 1; buf.append(ch)
        elif ch == "," and depth == 0:
            out.append(sql_value("".join(buf))); buf = []
        else: buf.append(ch)
    if buf: out.append(sql_value("".join(buf)))
    return out

def row_groups(values):
    groups, start, q, esc, depth = [], None, None, False, 0
    for i, ch in enumerate(values):
        if q:
            if esc: esc = False
            elif ch == "\\\\": esc = True
            elif ch == q: q = None
            continue
        if ch in "'\\"": q = ch
        elif ch == "(":
            if depth == 0: start = i + 1
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0: groups.append(values[start:i])
    return groups

def parse_dump(path):
    text = Path(path).read_text(errors="replace")
    rows = []
    pattern = re.compile(r"INSERT\s+INTO\s+users\s*\((.*?)\)\s*VALUES\s*(.*?);", re.I | re.S)
    for m in pattern.finditer(text):
        cols = [x.strip().strip('"') for x in m.group(1).split(",")]
        cols = [x.lower() for x in cols]
        for group in row_groups(m.group(2)):
            vals = fields(group)
            if len(vals) == len(cols): rows.append(dict(zip(cols, vals)))
    return [{str(k).lower(): (None if v is None else str(v).strip()) for k,v in r.items()} for r in rows]

def first(row, keys):
    for k in keys:
        if row.get(k): return row[k]
    return None

def email(row):
    value = (row.get("email") or row.get("email_address") or "").strip().lower()
    return value if EMAIL.fullmatch(value) else None

def safe_meta(row):
    return {k:v for k,v in row.items() if v not in (None,"") and k not in SKIP and not SECRET.search(k) and not KYC.search(k)}

async def run(path, apply):
    rows = parse_dump(path)
    report = {"source_rows":len(rows),"eligible":0,"created":0,"matched":0,"profiles":0,"kyc":0,"avatars":0,"banners":0,"skipped_no_email":0,"balances_imported":0,"mode":"apply" if apply else "dry-run"}
    if not apply:
        for r in rows:
            e = email(r)
            if not e: report["skipped_no_email"] += 1; continue
            report["eligible"] += 1
            if first(r, AVATAR): report["avatars"] += 1
            if first(r, BANNER): report["banners"] += 1
            if any(KYC.search(k) and r.get(k) for k in r): report["kyc"] += 1
        print(json.dumps(report, indent=2)); return

    async with engine.begin() as c: await c.run_sync(Base.metadata.create_all)
    async with SessionLocal() as s:
        for r in rows:
            e = email(r)
            if not e: report["skipped_no_email"] += 1; continue
            report["eligible"] += 1
            u = (await s.execute(select(UserMirror).where(UserMirror.email == e))).scalar_one_or_none()
            legacy_id = r.get("id") or r.get("user_id")
            if not u:
                u = UserMirror(keycloak_id=f"legacy:{legacy_id}" if legacy_id else f"legacy:{uuid.uuid4()}", identity_source="legacy_sql", source_sheet="users", source_row=int(legacy_id) if str(legacy_id or "").isdigit() else None, email=e, name=first(r, {"full_name","fullname","name"}) or e.split("@")[0], roles=[], active=str(r.get("account_status","active")).lower() not in {"disabled","deleted","inactive"})
                s.add(u); await s.flush(); report["created"] += 1
            else:
                report["matched"] += 1
                if u.identity_source != "keycloak": u.identity_source = "legacy_sql"

            p = (await s.execute(select(UserProfile).where(UserProfile.user_id == u.id))).scalar_one_or_none()
            if not p: p = UserProfile(user_id=u.id, source="legacy_sql"); s.add(p)
            p.first_name = p.first_name or first(r, {"first_name","firstname","given_name"})
            p.last_name = p.last_name or first(r, {"last_name","lastname","family_name"})
            p.display_name = p.display_name or first(r, {"full_name","fullname","display_name","name"}) or u.name
            p.gender = p.gender or r.get("gender")
            p.phone = p.phone or first(r, {"phone","mobile","fullphone","phone_number"})
            av = first(r, AVATAR); bn = first(r, BANNER)
            if not p.avatar_url and av: p.avatar_url = av; report["avatars"] += 1
            if not p.banner_url and bn: p.banner_url = bn; report["banners"] += 1
            meta = p.profile_metadata or {}; meta.update(safe_meta(r)); meta["legacy_user_id"] = legacy_id; meta["legacy_balance_ignored"] = True; p.profile_metadata = meta; report["profiles"] += 1

            ids = {k:v for k,v in r.items() if v and KYC.search(k)}
            if ids:
                k = (await s.execute(select(KYCIdentity).where(KYCIdentity.user_id == u.id))).scalar_one_or_none()
                if not k: k = KYCIdentity(user_id=u.id, verification_status="pending"); s.add(k)
                k.legal_name = k.legal_name or first(r, {"full_name","fullname","name"})
                k.date_of_birth = k.date_of_birth or first(r, {"birth_date","date_of_birth","dob"})
                k.nationality = k.nationality or first(r, {"nationality","country_name"})
                gov = first(r, {"nid","nid_number","national_id","passport","passport_number","government_id","government_id_number"})
                if gov and not k.encrypted_government_id:
                    k.government_id_type = "nid" if any(x in r for x in ("nid","nid_number","national_id")) else "government_id"
                    k.government_id_last4 = gov[-4:]; k.encrypted_government_id = encrypt_secret(gov)
                k.metadata = {a:b for a,b in ids.items() if a not in {"nid","nid_number","national_id","passport","passport_number","government_id","government_id_number"}}
                report["kyc"] += 1
        await s.commit()
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    asyncio.run(run(a.dump, a.apply))
