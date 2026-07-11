from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Basic liveness endpoint — used by Kubernetes probes in later milestones."""
    return {"status": "ok"}
