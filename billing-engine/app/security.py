"""
Minimal internal-auth guard for privileged billing endpoints (deduct, fine,
adjust). This is deliberately simple - a shared secret header, not a full
user auth system - because billing-engine currently has NO user-facing auth
at all (CORSMiddleware(allow_origins=["*"]), no auth dependency anywhere).

This is a stopgap, not a destination: once the platform has real user auth
(JWT, likely via ai-platform/backend which already has python-jose/pyjwt in
its dependencies), these endpoints should additionally verify the caller is
an admin/service account, not just holding a shared key. Track that as
follow-up work rather than treating this as "done."
"""
from fastapi import Header, HTTPException
from app import config


def require_internal_key(x_internal_api_key: str = Header(...)):
    if not config.INTERNAL_API_KEY:
        raise HTTPException(
            500,
            "INTERNAL_API_KEY is not configured on the server - refusing to "
            "run privileged billing operations with no secret set at all.",
        )
    if x_internal_api_key != config.INTERNAL_API_KEY:
        raise HTTPException(403, "Invalid internal API key")
    return True
