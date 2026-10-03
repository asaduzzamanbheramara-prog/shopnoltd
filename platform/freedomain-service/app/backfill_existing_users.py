import asyncio
import os

import httpx
from sqlalchemy import select

from app.api.domains import ensure_free_domain_schema, provision_for_user
from app.core.db import SessionLocal
from app.models.models import FreeDomain

KEYCLOAK_URL = os.environ.get(
    "KEYCLOAK_URL",
    "http://keycloak.shopno-identity.svc.cluster.local",
).rstrip("/")
REALM = os.environ.get("KEYCLOAK_REALM", "shopnoltd")
ADMIN_USER = os.environ.get("KEYCLOAK_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "")
PAGE_SIZE = 100
INCLUDE_DISABLED = os.environ.get("BACKFILL_INCLUDE_DISABLED", "true").lower() == "true"


async def admin_token(client: httpx.AsyncClient) -> str:
    if not ADMIN_PASSWORD:
        raise RuntimeError("KEYCLOAK_ADMIN_PASSWORD is not configured")
    last_error: Exception | None = None
    for attempt in range(1, 9):
        try:
            response = await client.post(
                f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
                data={
                    "grant_type": "password",
                    "client_id": "admin-cli",
                    "username": ADMIN_USER,
                    "password": ADMIN_PASSWORD,
                },
            )
            response.raise_for_status()
            token = response.json().get("access_token")
            if not token:
                raise RuntimeError("Keycloak admin token was not returned")
            return token
        except (httpx.HTTPError, RuntimeError) as exc:
            last_error = exc
            if attempt == 8:
                break
            await asyncio.sleep(min(5 * attempt, 30))
    raise RuntimeError(f"Keycloak admin token unavailable after retries: {last_error}")


async def list_users(client: httpx.AsyncClient, token: str) -> list[dict]:
    users: list[dict] = []
    first = 0
    headers = {"Authorization": f"Bearer {token}"}
    while True:
        response = await client.get(
            f"{KEYCLOAK_URL}/admin/realms/{REALM}/users",
            params={
                "first": first,
                "max": PAGE_SIZE,
                "briefRepresentation": "true",
            },
            headers=headers,
        )
        response.raise_for_status()
        page = response.json()
        if not isinstance(page, list):
            raise RuntimeError("Keycloak users response was not a list")
        users.extend(page)
        if len(page) < PAGE_SIZE:
            return users
        first += PAGE_SIZE


async def run() -> None:
    await ensure_free_domain_schema()

    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
        token = await admin_token(client)
        users = await list_users(client, token)

    candidates = [
        user
        for user in users
        if user.get("id")
        and not user.get("serviceAccountClientId")
        and (INCLUDE_DISABLED or user.get("enabled", True))
    ]

    async with SessionLocal() as session:
        existing_ids = set(
            (
                await session.execute(
                    select(FreeDomain.user_id).where(FreeDomain.active == 1)
                )
            )
            .scalars()
            .all()
        )

    created = 0
    already_present = 0
    failed: list[tuple[str, str]] = []

    for user in candidates:
        user_id = str(user["id"])
        username = str(user.get("username") or "").strip()
        if user_id in existing_ids:
            already_present += 1
            continue

        user_claims = {
            "sub": user_id,
            "preferred_username": username,
        }

        try:
            async with SessionLocal() as session:
                domain = await provision_for_user(user_claims, session)
            existing_ids.add(user_id)
            created += 1
            print(f"[OK] {username or user_id} -> {domain.subdomain}")
        except Exception as exc:
            failed.append((username or user_id, str(exc)))
            print(f"[FAIL] {username or user_id}: {exc}")

    print(
        f"[SUMMARY] keycloak_users={len(users)} candidates={len(candidates)} "
        f"already_present={already_present} created={created} failed={len(failed)}"
    )

    if failed:
        raise RuntimeError(
            f"free-domain backfill failed for {len(failed)} user(s)"
        )


if __name__ == "__main__":
    asyncio.run(run())
