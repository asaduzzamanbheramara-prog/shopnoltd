import httpx
from shopno_core.security.jwt import JWTError, jwt

from app.core.config import settings

_jwks_cache = None


async def _jwks():
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{settings.keycloak_issuer}/protocol/openid-connect/certs")
        r.raise_for_status()
        _jwks_cache = r.json()
    return _jwks_cache


async def verify_token(token: str) -> dict:
    try:
        h = jwt.get_unverified_header(token)
        keys = await _jwks()
        key = next(k for k in keys["keys"] if k["kid"] == h["kid"])
        return jwt.decode(
            token,
            key,
            algorithms=[key["alg"]],
            audience=settings.keycloak_audience,
            options={"verify_aud": True},
        )
    except (JWTError, StopIteration) as e:
        raise ValueError(f"invalid token: {e}") from e


async def verify_token_admin(token: str) -> dict:
    u = await verify_token(token)
    if "admin" not in u.get("roles", []):
        raise PermissionError("admin only")
    return u


# --- 3-tier role model ---------------------------------------------------
# Keycloak realm roles expected in the JWT "roles" claim (see
# scripts/setup_rbac_roles.py): "platform_admin", "tenant_owner", "customer".
# tenant_owner/customer tokens also carry a "tenant_id" claim scoping them
# to one tenant; platform_admin is unscoped.


def _roles(payload: dict) -> set:
    return set(payload.get("roles", []))


async def require_roles(token: str, allowed: set) -> dict:
    u = await verify_token(token)
    if not (_roles(u) & allowed):
        raise PermissionError(f"requires one of: {sorted(allowed)}")
    return u


async def require_tenant_access(token: str, tenant_id: str) -> dict:
    """platform_admin may act on any tenant; tenant_owner/customer only on
    their own tenant_id (from the token, never trust a client-supplied one)."""
    u = await verify_token(token)
    roles = _roles(u)
    if "platform_admin" in roles or "admin" in roles:
        return u
    if roles & {"tenant_owner", "customer"} and u.get("tenant_id") == tenant_id:
        return u
    raise PermissionError("not authorized for this tenant")


async def require_customer_self_or_above(token: str, tenant_id: str, customer_user_id: str) -> dict:
    """platform_admin/tenant_owner may edit any customer in their tenant;
    a customer may only edit their own record."""
    u = await verify_token(token)
    roles = _roles(u)
    if "platform_admin" in roles or "admin" in roles:
        return u
    if "tenant_owner" in roles and u.get("tenant_id") == tenant_id:
        return u
    if "customer" in roles and u.get("tenant_id") == tenant_id and u.get("sub") == customer_user_id:
        return u
    raise PermissionError("not authorized for this customer record")
