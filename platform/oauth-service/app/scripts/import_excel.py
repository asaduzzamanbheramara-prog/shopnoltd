"""Safe XLSX importer for Shopnoltd users, profiles, and source records.

Every imported email is reconciled to the canonical Keycloak identity store. Existing
Keycloak users are linked; new imported identities are created in Keycloak with a
required password-update action. Application mirror/profile rows are then created
or updated without duplicating users.
"""
import asyncio, hashlib, json, re, sys, uuid, zipfile, xml.etree.ElementTree as ET
from pathlib import Path
import httpx
from sqlalchemy import select
from app.core.config import settings
from app.core.db import Base, engine, SessionLocal
from app.core.vault import encrypt_secret
from app.models.models import ImportedWorkbook, ImportedExcelRow, SecretVaultEntry, UserMirror, UserProfile

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
SECRET_WORDS = re.compile(r"(password|passcode|secret|token|api[ _-]?key|private[ _-]?key|authenticator|2fa|otp|recovery.*(code|password|secret)|client[ _-]?secret)", re.I)
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

FIELD_ALIASES = {
    "first_name": ("first name", "firstname", "given name", "givenname"),
    "last_name": ("last name", "lastname", "surname", "family name", "familyname"),
    "display_name": ("display name", "full name", "name"),
    "phone": ("phone", "mobile", "mobile number", "phone number", "telephone"),
    "recovery_email": ("recovery email", "alternate email", "secondary email"),
    "avatar_url": ("avatar", "avatar url", "profile image", "profile photo", "photo url", "image url"),
    "bio": ("bio", "biography", "about", "description"),
    "gender": ("gender", "sex"),
    "birth_month": ("birth month", "dob month"),
    "birth_day": ("birth day", "dob day"),
    "birth_year": ("birth year", "dob year"),
}

def col_index(ref):
    m = re.match(r"([A-Z]+)", ref or "")
    if not m: return 0
    n = 0
    for ch in m.group(1): n = n * 26 + ord(ch) - 64
    return n

def workbook_rows(path):
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall(NS + "si"):
                shared.append("".join(t.text or "" for t in si.iter(NS + "t")))
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        relroot = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        relmap = {r.attrib["Id"]: r.attrib["Target"] for r in relroot}
        for sh in wb.find(NS + "sheets"):
            name = sh.attrib["name"]; target = relmap[sh.attrib[REL + "id"]]
            if not target.startswith("xl/"): target = "xl/" + target.lstrip("/")
            root = ET.fromstring(z.read(target)); rows = []
            for rr in root.findall(".//" + NS + "sheetData/" + NS + "row"):
                cells = {}
                for c in rr.findall(NS + "c"):
                    ref = c.attrib.get("r", ""); idx = col_index(ref)
                    typ = c.attrib.get("t"); v = c.find(NS + "v"); isel = c.find(NS + "is"); val = ""
                    if typ == "s" and v is not None: val = shared[int(v.text)]
                    elif typ == "inlineStr" and isel is not None: val = "".join(t.text or "" for t in isel.iter(NS + "t"))
                    elif v is not None: val = v.text or ""
                    if val != "": cells[idx] = val
                if cells: rows.append((int(rr.attrib.get("r", "0")), cells))
            yield name, rows

def email_candidates(values):
    found = []
    for value in values:
        for part in re.split(r"[\s,;|]+", str(value).strip()):
            if EMAIL_RE.fullmatch(part): found.append(part.lower())
    return list(dict.fromkeys(found))

def secret_label(label): return bool(SECRET_WORDS.search(str(label or "")))

def split_labeled(value):
    m = re.match(r"^\s*([^:]{2,80}):\s*(.+)$", str(value), re.S)
    return (m.group(1).strip(), m.group(2).strip()) if m else (None, None)

def normalize_label(label): return re.sub(r"[^a-z0-9]+", " ", str(label or "").lower()).strip()

def profile_value(labels, cells, field):
    aliases = {normalize_label(x) for x in FIELD_ALIASES[field]}
    for idx, label in labels.items():
        if normalize_label(label) in aliases:
            value = str(cells.get(idx, "")).strip()
            if value: return value
    return None

def profile_payload(labels, cells, email):
    first = profile_value(labels, cells, "first_name")
    last = profile_value(labels, cells, "last_name")
    display = profile_value(labels, cells, "display_name") or " ".join(x for x in (first, last) if x) or email.split("@")[0]
    return {
        "first_name": first, "last_name": last, "display_name": display,
        "phone": profile_value(labels, cells, "phone"),
        "recovery_email": profile_value(labels, cells, "recovery_email"),
        "avatar_url": profile_value(labels, cells, "avatar_url"),
        "bio": profile_value(labels, cells, "bio"),
        "gender": profile_value(labels, cells, "gender"),
        "birth_month": profile_value(labels, cells, "birth_month"),
        "birth_day": profile_value(labels, cells, "birth_day"),
        "birth_year": profile_value(labels, cells, "birth_year"),
    }

async def kc_token():
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{settings.keycloak_url}/realms/master/protocol/openid-connect/token",
            data={"grant_type": "password", "client_id": "admin-cli",
                  "username": settings.keycloak_admin_user, "password": settings.keycloak_admin_password},
        )
    r.raise_for_status()
    return r.json()["access_token"]

async def ensure_keycloak_user(email, name, tok, client):
    base = f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}"
    headers = {"Authorization": f"Bearer {tok}"}
    r = await client.get(f"{base}/users", params={"email": email, "exact": "true"}, headers=headers)
    r.raise_for_status()
    matches = r.json()
    if matches: return matches[0]["id"], False
    r = await client.post(
        f"{base}/users",
        json={"username": email, "email": email, "firstName": name, "enabled": True,
              "emailVerified": False, "requiredActions": ["UPDATE_PASSWORD"]},
        headers=headers,
    )
    if r.status_code == 409:
        r = await client.get(f"{base}/users", params={"email": email, "exact": "true"}, headers=headers)
        r.raise_for_status(); matches = r.json()
        if not matches: raise RuntimeError(f"Keycloak conflict but no user found for {email}")
        return matches[0]["id"], False
    r.raise_for_status()
    r = await client.get(f"{base}/users", params={"email": email, "exact": "true"}, headers=headers)
    r.raise_for_status(); matches = r.json()
    if not matches: raise RuntimeError(f"Keycloak creation succeeded but lookup failed for {email}")
    return matches[0]["id"], True

async def main(path):
    path = Path(path).resolve()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    tok = await kc_token()

    async with SessionLocal() as s, httpx.AsyncClient(timeout=30) as client:
        existing = (await s.execute(select(ImportedWorkbook).where(ImportedWorkbook.sha256 == digest))).scalar_one_or_none()
        if existing:
            print(json.dumps({"status": "already_imported", "workbook_id": existing.id, "rows": existing.row_count})); return

        wb = ImportedWorkbook(filename=path.name, source_path=str(path), sha256=digest, status="running")
        s.add(wb); await s.flush()
        sheets = total = secret_count = linked = created_kc = created_profiles = 0

        for sheet, rows in workbook_rows(path):
            sheets += 1
            if not rows: continue
            header = rows[0][1]
            looks_like_header = any(secret_label(v) for v in header.values()) or any(
                re.search(r"(email|account|username|first name|last name|display name|phone|mobile|gender|status|password|passcode|recovery|avatar|photo|bio)", str(v), re.I)
                for v in header.values()
            )
            labels = {i: str(v).strip() for i, v in header.items()} if looks_like_header else {}
            source_rows = rows[1:] if looks_like_header else rows

            for rownum, cells in source_rows:
                raw = {}
                source_ciphertext = encrypt_secret(json.dumps(cells, ensure_ascii=False, sort_keys=True))
                emails = email_candidates(cells.values())
                linked_user = None
                profile_data = profile_payload(labels, cells, emails[0]) if emails else {}

                if emails:
                    email = emails[0]
                    name = profile_data.get("display_name") or email.split("@")[0]
                    kc_id, was_created = await ensure_keycloak_user(email, name, tok, client)
                    created_kc += int(was_created)
                    linked_user = (await s.execute(select(UserMirror).where(UserMirror.email == email))).scalar_one_or_none()

                    if linked_user and linked_user.keycloak_id.startswith("import:"):
                        linked_user.keycloak_id = kc_id
                    elif not linked_user:
                        linked_user = UserMirror(
                            keycloak_id=kc_id, identity_source="keycloak", source_workbook_id=wb.id,
                            source_sheet=sheet, source_row=rownum, email=email, name=name, roles=[], active=True,
                        )
                        s.add(linked_user); await s.flush()
                    else:
                        linked_user.keycloak_id = kc_id
                        linked_user.identity_source = "keycloak"
                        linked_user.name = name or linked_user.name
                        linked_user.active = True

                    linked_user.source_workbook_id = wb.id
                    linked_user.source_sheet = sheet
                    linked_user.source_row = rownum

                    profile = (await s.execute(select(UserProfile).where(UserProfile.user_id == linked_user.id))).scalar_one_or_none()
                    if not profile:
                        profile = UserProfile(user_id=linked_user.id, source="excel_import",
                            profile_metadata={"workbook_id": wb.id, "sheet": sheet, "source_row": rownum})
                        s.add(profile); created_profiles += 1

                    for field, value in profile_data.items():
                        if value in (None, ""): continue
                        if field in ("birth_day", "birth_year"):
                            try: value = int(value)
                            except ValueError: continue
                        setattr(profile, field, value)
                    profile.source = "excel_import"
                    profile.profile_metadata = {**(profile.profile_metadata or {}), "workbook_id": wb.id, "sheet": sheet, "source_row": rownum}
                    linked += 1

                row_id = str(uuid.uuid4())
                normalized = "account" if any(x in sheet.lower() for x in ("gmail", "instagram", "yahoo", "account")) else "source_record"
                normalized_key = emails[0] if emails else None
                for idx, val in cells.items():
                    label = labels.get(idx, f"column_{idx}"); labeled, payload = split_labeled(val)
                    is_secret = secret_label(label) or secret_label(labeled)
                    if is_secret:
                        raw[label] = "[ENCRYPTED]"
                        s.add(SecretVaultEntry(
                            id=str(uuid.uuid4()), owner_type="excel_row", owner_id=row_id, provider=sheet[:64],
                            secret_type=(labeled or label)[:64], encrypted_value=encrypt_secret(payload if payload is not None else str(val)),
                            source_workbook_id=wb.id, source_sheet=sheet, source_row=rownum,
                        ))
                        secret_count += 1
                    else:
                        raw[label] = str(val)

                s.add(ImportedExcelRow(
                    id=row_id, workbook_id=wb.id, sheet_name=sheet, source_row=rownum, values=raw,
                    encrypted_source=source_ciphertext, normalized_type=normalized, normalized_key=normalized_key,
                    linked_user_id=linked_user.id if linked_user else None,
                ))
                total += 1
                if total % 100 == 0: await s.flush()

        wb.sheet_count = sheets; wb.row_count = total; wb.status = "completed"
        await s.commit()
        print(json.dumps({"status": "completed", "workbook_id": wb.id, "sheets": sheets, "rows": total,
                          "encrypted_secrets": secret_count, "linked_users": linked,
                          "keycloak_users_created": created_kc, "profiles_created": created_profiles}))

if __name__ == "__main__":
    if len(sys.argv) != 2: raise SystemExit("usage: import_excel.py <xlsx>")
    asyncio.run(main(sys.argv[1]))
