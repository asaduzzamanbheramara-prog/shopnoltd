"""One-time XLSX importer for the Shopnoltd profile/account vault.
Reads XLSX directly with stdlib XML so no spreadsheet package is required.
Secret-looking fields are encrypted immediately and never stored in raw JSON.
"""
import asyncio, hashlib, json, os, re, sys, zipfile, xml.etree.ElementTree as ET
from pathlib import Path
from sqlalchemy import select
from app.core.db import Base, engine, SessionLocal
from app.core.vault import encrypt_secret
from app.models.models import ImportedWorkbook, ImportedExcelRow, SecretVaultEntry, UserMirror, UserProfile

NS='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
REL='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
SECRET_WORDS=re.compile(r'(password|passcode|secret|token|api[ _-]?key|private[ _-]?key|authenticator|2fa|otp|recovery.*(code|password|secret)|client[ _-]?secret)', re.I)
EMAIL_RE=re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')

def col_index(ref):
    m=re.match(r'([A-Z]+)', ref or '')
    if not m: return 0
    n=0
    for ch in m.group(1): n=n*26+ord(ch)-64
    return n

def workbook_rows(path):
    with zipfile.ZipFile(path) as z:
        shared=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            root=ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in root.findall(NS+'si'):
                shared.append(''.join(t.text or '' for t in si.iter(NS+'t')))
        wb=ET.fromstring(z.read('xl/workbook.xml'))
        relroot=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        relmap={r.attrib['Id']:r.attrib['Target'] for r in relroot}
        for sh in wb.find(NS+'sheets'):
            name=sh.attrib['name']; target=relmap[sh.attrib[REL+'id']]
            if not target.startswith('xl/'): target='xl/'+target.lstrip('/')
            root=ET.fromstring(z.read(target))
            rows=[]
            for rr in root.findall('.//'+NS+'sheetData/'+NS+'row'):
                cells={}
                for c in rr.findall(NS+'c'):
                    ref=c.attrib.get('r',''); idx=col_index(ref)
                    typ=c.attrib.get('t'); v=c.find(NS+'v'); isel=c.find(NS+'is')
                    val=''
                    if typ=='s' and v is not None: val=shared[int(v.text)]
                    elif typ=='inlineStr' and isel is not None: val=''.join(t.text or '' for t in isel.iter(NS+'t'))
                    elif v is not None: val=v.text or ''
                    if val!='': cells[idx]=val
                if cells: rows.append((int(rr.attrib.get('r','0')),cells))
            yield name, rows

def email_candidates(values):
    found=[]
    for v in values:
        s=str(v).strip()
        for part in re.split(r'[\s,;|]+',s):
            if EMAIL_RE.fullmatch(part): found.append(part.lower())
    return list(dict.fromkeys(found))

def secret_label(label):
    return bool(SECRET_WORDS.search(str(label or '')))

def split_labeled(value):
    m=re.match(r'^\s*([^:]{2,80}):\s*(.+)$', str(value), re.S)
    return (m.group(1).strip(),m.group(2).strip()) if m else (None,None)

async def main(path):
    path=Path(path).resolve(); digest=hashlib.sha256(path.read_bytes()).hexdigest()
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as s:
        existing=(await s.execute(select(ImportedWorkbook).where(ImportedWorkbook.sha256==digest))).scalar_one_or_none()
        if existing:
            print(json.dumps({'status':'already_imported','workbook_id':existing.id,'rows':existing.row_count}))
            return
        wb=ImportedWorkbook(filename=path.name,source_path=str(path),sha256=digest,status='running')
        s.add(wb); await s.flush()
        sheets=0; total=0; secret_count=0; linked=0
        for sheet, rows in workbook_rows(path):
            sheets += 1
            if not rows: continue
            # Preserve every row. The first populated row is treated as a header only for field labels.
            header=rows[0][1]
            header_text=' '.join(str(v) for v in header.values())
            looks_like_header=any(secret_label(v) for v in header.values()) or any(re.search(r'(email|account|username|first name|last name|gender|status|password|passcode|recovery)', str(v), re.I) for v in header.values())
            labels={i:str(v).strip() for i,v in header.items()} if looks_like_header else {}
            source_rows=rows[1:] if looks_like_header else rows
            for rownum,cells in source_rows:
                raw={}
                source_ciphertext=encrypt_secret(json.dumps(cells, ensure_ascii=False, sort_keys=True))
                emails=email_candidates(cells.values())
                linked_user=None
                if emails:
                    # One application identity per distinct email. Existing Keycloak users are linked;
                    # new XLS identities become imported users with a non-login synthetic identity key.
                    linked_user=(await s.execute(select(UserMirror).where(UserMirror.email==emails[0]))).scalar_one_or_none()
                    if not linked_user:
                        linked_user=UserMirror(
                            keycloak_id=f"import:{__import__('uuid').uuid4()}",
                            identity_source="excel_import",
                            source_workbook_id=wb.id,
                            source_sheet=sheet,
                            source_row=rownum,
                            email=emails[0],
                            name=emails[0].split("@")[0],
                            roles=[],
                            active=True,
                        )
                        s.add(linked_user)
                        await s.flush()
                        s.add(UserProfile(
                            user_id=linked_user.id,
                            display_name=linked_user.name,
                            recovery_email=emails[0],
                            source="excel_import",
                            profile_metadata={"workbook_id": wb.id, "sheet": sheet, "source_row": rownum},
                        ))
                row_id=str(__import__('uuid').uuid4())
                normalized='account' if any(x in sheet.lower() for x in ('gmail','instagram','yahoo','account')) else 'source_record'
                normalized_key=emails[0] if emails else None
                for idx,val in cells.items():
                    label=labels.get(idx, f'column_{idx}')
                    labeled, payload=split_labeled(val)
                    is_secret=secret_label(label) or secret_label(labeled)
                    if is_secret and payload:
                        raw[label]='[ENCRYPTED]'
                        s.add(SecretVaultEntry(id=str(__import__('uuid').uuid4()),owner_type='excel_row',owner_id=row_id,provider=sheet[:64],secret_type=(labeled or label)[:64],encrypted_value=encrypt_secret(payload),source_workbook_id=wb.id,source_sheet=sheet,source_row=rownum))
                        secret_count += 1
                    elif is_secret:
                        raw[label]='[ENCRYPTED]'
                        s.add(SecretVaultEntry(id=str(__import__('uuid').uuid4()),owner_type='excel_row',owner_id=row_id,provider=sheet[:64],secret_type=label[:64],encrypted_value=encrypt_secret(str(val)),source_workbook_id=wb.id,source_sheet=sheet,source_row=rownum))
                        secret_count += 1
                    else:
                        raw[label]=str(val)
                s.add(ImportedExcelRow(id=row_id,workbook_id=wb.id,sheet_name=sheet,source_row=rownum,values=raw,encrypted_source=source_ciphertext,normalized_type=normalized,normalized_key=normalized_key,linked_user_id=linked_user.id if linked_user else None))
                if linked_user:
                    linked += 1
                    profile=(await s.execute(select(UserProfile).where(UserProfile.user_id==linked_user.id))).scalar_one_or_none()
                    if profile and not profile.recovery_email and emails:
                        profile.recovery_email=emails[0]
                total += 1
                if total % 250 == 0: await s.flush()
        wb.sheet_count=sheets; wb.row_count=total; wb.status='completed'
        await s.commit()
        print(json.dumps({'status':'completed','workbook_id':wb.id,'sheets':sheets,'rows':total,'encrypted_secrets':secret_count,'linked_users':linked}))

if __name__=='__main__':
    if len(sys.argv)!=2: raise SystemExit('usage: import_excel.py <xlsx>')
    asyncio.run(main(sys.argv[1]))
