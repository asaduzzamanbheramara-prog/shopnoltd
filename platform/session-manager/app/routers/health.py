from fastapi import APIRouter

router = APIRouter()


@router.get("/health/live")
def live():
    return {"status": "live"}


@router.get("/health/ready")
def ready():
    return {"status": "ready"}
