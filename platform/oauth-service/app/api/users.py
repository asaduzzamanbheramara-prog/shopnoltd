import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import verify_token, verify_token_admin
from app.models.models import UserMirror, UserProfile
from app.schemas.schemas import UserAdminPatch, UserIn, UserOut

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)


ADMIN_URL = f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}"


async def kc_token():
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{settings.keycloak_url}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": settings.keycloak_admin_user,
                "password": settings.keycloak_admin_password,
            },
        )
    r.raise_for_status()
    return r.json()["access_token"]


def _user_name(payload: dict) -> str:
    name = (payload.get("name") or "").strip()
    if name:
        return name
    given = (payload.get("given_name") or "").strip()
    family = (payload.get("family_name") or "").strip()
    return " ".join(part for part in (given, family) if part)


def _user_out(u: UserMirror) -> UserOut:
    return UserOut(
        id=u.id,
        sub=u.keycloak_id,
        email=u.email,
        name=u.name or "",
        tenant_id=u.tenant_id,
        roles=u.roles or [],
        active=bool(u.active),
        identity_source=u.identity_source or "keycloak",
    )


async def ensure_user_mirror(payload: dict, s: AsyncSession) -> UserMirror:
    keycloak_id = payload.get("sub")
    email = (payload.get("email") or "").strip()

    if not keycloak_id:
        raise HTTPException(401, "authenticated token is missing subject")
    if not email:
        raise HTTPException(400, "authenticated token is missing email")

    existing = (
        await s.execute(select(UserMirror).where(UserMirror.keycloak_id == keycloak_id))
    ).scalar_one_or_none()
    if existing:
        profile = (
            await s.execute(select(UserProfile).where(UserProfile.user_id == existing.id))
        ).scalar_one_or_none()
        if not profile:
            profile = UserProfile(
                user_id=existing.id,
                display_name=existing.name or email.split("@")[0],
                first_name=(payload.get("given_name") or "").strip() or None,
                last_name=(payload.get("family_name") or "").strip() or None,
                source="registration",
            )
            s.add(profile)
            await s.commit()
        return existing

    email_owner = (
        await s.execute(select(UserMirror).where(UserMirror.email == email))
    ).scalar_one_or_none()
    if email_owner and email_owner.keycloak_id != keycloak_id:
        raise HTTPException(409, "email is already linked to another account")

    u = UserMirror(
        keycloak_id=keycloak_id,
        email=email,
        name=_user_name(payload),
        tenant_id=payload.get("tenant_id"),
        roles=payload.get("roles") or [],
        active=True,
        identity_source="keycloak",
    )
    s.add(u)

    try:
        await s.flush()
    except IntegrityError:
        await s.rollback()
        existing = (
            await s.execute(select(UserMirror).where(UserMirror.keycloak_id == keycloak_id))
        ).scalar_one_or_none()
        if existing:
            return existing
        email_owner = (
            await s.execute(select(UserMirror).where(UserMirror.email == email))
        ).scalar_one_or_none()
        if email_owner and email_owner.keycloak_id != keycloak_id:
            raise HTTPException(409, "email is already linked to another account")
        raise HTTPException(409, "unable to provision account safely")

    profile = (
        await s.execute(select(UserProfile).where(UserProfile.user_id == u.id))
    ).scalar_one_or_none()
    if not profile:
        profile = UserProfile(
            user_id=u.id,
            display_name=u.name or email.split("@")[0],
            first_name=(payload.get("given_name") or "").strip() or None,
            last_name=(payload.get("family_name") or "").strip() or None,
            source="registration",
        )
        s.add(profile)
    await s.commit()
    await s.refresh(u)
    return u


@router.post("", response_model=UserOut, status_code=201)
async def create(body: UserIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    tok = await kc_token()
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{ADMIN_URL}/users",
            headers={"Authorization": f"Bearer {tok}"},
            json={
                "email": body.email,
                "username": body.email,
                "firstName": body.name,
                "enabled": True,
                "emailVerified": False,
                "credentials": [{"type": "password", "value": body.password, "temporary": False}]
                if body.password
                else [],
            },
        )
    if r.status_code == 409:
        raise HTTPException(409, "user already exists")
    r.raise_for_status()
    async with httpx.AsyncClient() as c:
        r2 = await c.get(
            f"{ADMIN_URL}/users?email={body.email}", headers={"Authorization": f"Bearer {tok}"}
        )
    kc_id = r2.json()[0]["id"]
    u = UserMirror(
        keycloak_id=kc_id,
        email=body.email,
        name=body.name,
        tenant_id=body.tenant_id,
        identity_source="keycloak",
    )
    s.add(u)
    await s.flush()
    s.add(UserProfile(user_id=u.id, display_name=body.name or body.email.split("@")[0], source="admin_created"))
    await s.commit()
    await s.refresh(u)
    return _user_out(u)


@router.get("", response_model=list[UserOut])
async def list_(
    user=Depends(admin),
    s: AsyncSession = Depends(db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    q: str = Query("", max_length=200),
):
    stmt = select(UserMirror).order_by(UserMirror.created_at, UserMirror.id)
    search = q.strip()
    if search:
        pattern = f"%{search.lower()}%"
        stmt = stmt.where(
            func.lower(UserMirror.email).like(pattern)
            | func.lower(UserMirror.name).like(pattern)
            | func.lower(UserMirror.id).like(pattern)
            | func.lower(UserMirror.identity_source).like(pattern)
        )
    res = await s.execute(stmt.offset(offset).limit(limit))
    return [_user_out(u) for u in res.scalars().all()]


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(user_id: str, body: UserAdminPatch, user=Depends(admin), s: AsyncSession = Depends(db)):
    u = (await s.execute(select(UserMirror).where(UserMirror.id == user_id))).scalar_one_or_none()
    if not u:
        raise HTTPException(404, "user not found")

    changes = body.model_dump(exclude_unset=True)
    if "email" in changes:
        email = (changes["email"] or "").strip().lower()
        if not email:
            raise HTTPException(400, "email cannot be empty")
        owner = (await s.execute(select(UserMirror).where(UserMirror.email == email, UserMirror.id != u.id))).scalar_one_or_none()
        if owner:
            raise HTTPException(409, "email is already linked to another account")
        if u.keycloak_id.startswith("import:"):
            raise HTTPException(409, "legacy synthetic identity cannot change email through the admin API")
        tok = await kc_token()
        async with httpx.AsyncClient() as c:
            r = await c.put(
                f"{ADMIN_URL}/users/{u.keycloak_id}",
                headers={"Authorization": f"Bearer {tok}"},
                json={"email": email, "username": email},
            )
            r.raise_for_status()
        u.email = email

    if "name" in changes:
        u.name = (changes["name"] or "").strip()
        if not u.keycloak_id.startswith("import:"):
            tok = await kc_token()
            async with httpx.AsyncClient() as c:
                r = await c.put(
                    f"{ADMIN_URL}/users/{u.keycloak_id}",
                    headers={"Authorization": f"Bearer {tok}"},
                    json={"firstName": u.name},
                )
                r.raise_for_status()

    if "tenant_id" in changes:
        u.tenant_id = changes["tenant_id"]
    if "active" in changes and changes["active"] is not None:
        active = bool(changes["active"])
        if not u.keycloak_id.startswith("import:"):
            tok = await kc_token()
            async with httpx.AsyncClient() as c:
                r = await c.put(
                    f"{ADMIN_URL}/users/{u.keycloak_id}",
                    headers={"Authorization": f"Bearer {tok}"},
                    json={"enabled": active},
                )
                r.raise_for_status()
        u.active = active

    await s.commit()
    await s.refresh(u)
    return _user_out(u)


@router.post("/{user_id}/password-reset", response_model=dict)
async def password_reset(user_id: str, user=Depends(admin), s: AsyncSession = Depends(db)):
    u = (await s.execute(select(UserMirror).where(UserMirror.id == user_id))).scalar_one_or_none()
    if not u:
        raise HTTPException(404, "user not found")
    if u.keycloak_id.startswith("import:"):
        raise HTTPException(409, "legacy synthetic identity has no Keycloak recovery endpoint")
    tok = await kc_token()
    async with httpx.AsyncClient() as c:
        r = await c.put(
            f"{ADMIN_URL}/users/{u.keycloak_id}/execute-actions-email",
            params={"lifespan": "1800", "client_id": "shopnoltd-web"},
            headers={"Authorization": f"Bearer {tok}"},
            json=["UPDATE_PASSWORD"],
        )
        r.raise_for_status()
    return {"status": "sent", "user_id": u.id, "email": u.email}


@router.delete("/{user_id}", response_model=dict)
async def deactivate_user(user_id: str, user=Depends(admin), s: AsyncSession = Depends(db)):
    u = (await s.execute(select(UserMirror).where(UserMirror.id == user_id))).scalar_one_or_none()
    if not u:
        raise HTTPException(404, "user not found")
    if not u.keycloak_id.startswith("import:"):
        tok = await kc_token()
        async with httpx.AsyncClient() as c:
            r = await c.put(
                f"{ADMIN_URL}/users/{u.keycloak_id}",
                headers={"Authorization": f"Bearer {tok}"},
                json={"enabled": False},
            )
            r.raise_for_status()
    u.active = False
    await s.commit()
    return {"status": "deactivated", "user_id": u.id}


@router.get("/reconciliation", response_model=dict)
async def reconciliation_report(user=Depends(admin), s: AsyncSession = Depends(db)):
    """Read-only report for current vs previous-website identity provenance."""
    total = int((await s.execute(select(func.count()).select_from(UserMirror))).scalar_one())
    legacy = int(
        (
            await s.execute(
                select(func.count()).select_from(UserMirror).where(UserMirror.identity_source == "legacy_sql")
            )
        ).scalar_one()
    )
    current = total - legacy
    active = int(
        (await s.execute(select(func.count()).select_from(UserMirror).where(UserMirror.active.is_(True)))).scalar_one()
    )
    profiles = int((await s.execute(select(func.count()).select_from(UserProfile))).scalar_one())
    linked_profiles = int(
        (
            await s.execute(
                select(func.count()).select_from(UserProfile).join(UserMirror, UserProfile.user_id == UserMirror.id)
            )
        ).scalar_one()
    )
    orphan_profiles = profiles - linked_profiles
    legacy_profiles = int(
        (
            await s.execute(
                select(func.count())
                .select_from(UserProfile)
                .join(UserMirror, UserProfile.user_id == UserMirror.id)
                .where(UserMirror.identity_source == "legacy_sql")
            )
        ).scalar_one()
    )
    current_profiles = linked_profiles - legacy_profiles
    duplicate_emails = int(
        (
            await s.execute(
                select(func.count())
                .select_from(
                    select(UserMirror.email).group_by(UserMirror.email).having(func.count() > 1).subquery()
                )
            )
        ).scalar_one()
    )
    duplicate_keycloak_ids = int(
        (
            await s.execute(
                select(func.count())
                .select_from(
                    select(UserMirror.keycloak_id).group_by(UserMirror.keycloak_id).having(func.count() > 1).subquery()
                )
            )
        ).scalar_one()
    )
    return {
        "status": "ok",
        "source_policy": {
            "current_canonical": "users records not marked legacy_sql",
            "previous_website": "users records marked legacy_sql",
            "reimport_policy": "idempotent_by_unique_email_and_keycloak_id",
            "destructive_actions": "none",
        },
        "users": {
            "total_canonical_records": total,
            "current": current,
            "previous_website_legacy": legacy,
            "active": active,
        },
        "profiles": {
            "total_rows": profiles,
            "linked_to_users": linked_profiles,
            "current_canonical": current_profiles,
            "previous_website_legacy": legacy_profiles,
            "orphan_rows": orphan_profiles,
        },
        "integrity": {
            "duplicate_emails": duplicate_emails,
            "duplicate_keycloak_ids": duplicate_keycloak_ids,
            "safe_for_reconciliation": duplicate_emails == 0 and duplicate_keycloak_ids == 0,
        },
    }


@router.post("/sync-keycloak", response_model=dict)
async def sync_keycloak(user=Depends(admin), s: AsyncSession = Depends(db)):
    """Reconcile enabled Keycloak identities without recreating legacy users."""
    tok = await kc_token()
    synced = 0
    created_users = 0
    created_profiles = 0
    skipped_conflicts = 0
    first = 0

    async with httpx.AsyncClient(timeout=30) as c:
        while True:
            r = await c.get(
                f"{ADMIN_URL}/users",
                params={"first": first, "max": 200, "briefRepresentation": "false"},
                headers={"Authorization": f"Bearer {tok}"},
            )
            r.raise_for_status()
            batch = r.json()
            if not batch:
                break

            for payload in batch:
                if not payload.get("enabled", True):
                    continue
                keycloak_id = payload.get("id")
                email = (payload.get("email") or "").strip()
                if not keycloak_id or not email:
                    continue

                existing = (
                    await s.execute(select(UserMirror).where(UserMirror.keycloak_id == keycloak_id))
                ).scalar_one_or_none()

                if not existing:
                    email_owner = (
                        await s.execute(select(UserMirror).where(UserMirror.email == email))
                    ).scalar_one_or_none()
                    if email_owner and email_owner.keycloak_id != keycloak_id:
                        skipped_conflicts += 1
                        continue
                    existing = UserMirror(
                        keycloak_id=keycloak_id,
                        email=email,
                        name=_user_name(payload),
                        tenant_id=(payload.get("attributes") or {}).get("tenant_id", [None])[0],
                        roles=[],
                        active=True,
                        identity_source="keycloak",
                    )
                    s.add(existing)
                    await s.flush()
                    created_users += 1
                else:
                    existing.active = True
                    # Legacy records remain sourced from the previous website.
                    if existing.identity_source != "legacy_sql":
                        existing.email = email
                        existing.name = _user_name(payload) or existing.name
                        attrs = payload.get("attributes") or {}
                        tenant_values = attrs.get("tenant_id") or []
                        if tenant_values:
                            existing.tenant_id = tenant_values[0]

                profile = (
                    await s.execute(select(UserProfile).where(UserProfile.user_id == existing.id))
                ).scalar_one_or_none()
                if not profile:
                    profile = UserProfile(
                        user_id=existing.id,
                        display_name=existing.name or email.split("@")[0],
                        first_name=(payload.get("firstName") or payload.get("givenName") or "").strip() or None,
                        last_name=(payload.get("lastName") or payload.get("familyName") or "").strip() or None,
                        source="legacy_sql" if existing.identity_source == "legacy_sql" else "keycloak_sync",
                    )
                    s.add(profile)
                    created_profiles += 1
                synced += 1

            await s.commit()
            if len(batch) < 200:
                break
            first += len(batch)

    return {
        "status": "completed",
        "keycloak_users_synced": synced,
        "users_created": created_users,
        "profiles_created": created_profiles,
        "conflicts_skipped": skipped_conflicts,
        "legacy_records_recreated": 0,
    }


@router.get("/me")
async def me(creds: HTTPAuthorizationCredentials = Depends(bearer), s: AsyncSession = Depends(db)):
    payload = await verify_token(creds.credentials)
    u = await ensure_user_mirror(payload, s)
    return _user_out(u)
