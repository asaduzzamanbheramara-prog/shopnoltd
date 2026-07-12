"""Traefik forwardAuth endpoint."""
from fastapi import APIRouter, Request
router = APIRouter()
@router.all("")
async def verify(request: Request):
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        from fastapi.responses import Response
        return Response(status_code=401)
    token = auth.split(" ", 1)[1]
    try:
        from app.core.security import verify_token
        payload = await verify_token(token)
        # Forward user info as headers
        from fastapi.responses import Response
        h = {"X-Forwarded-User": payload.get("sub", ""), "X-Forwarded-Email": payload.get("email", ""), "X-Forwarded-Tenant": payload.get("tenant_id", "default"), "X-Forwarded-Roles": ",".join(payload.get("roles", []))}
        return Response(status_code=200, headers=h)
    except Exception:
        from fastapi.responses import Response
        return Response(status_code=401)
