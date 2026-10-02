from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.security import current_user
from app.services.media_client import MediaServiceClient, MediaServiceError

router = APIRouter(prefix="/api/v1/media", tags=["media"])


class DesignRenderIn(BaseModel):
    source: str = Field(min_length=1, max_length=2_000_000)
    kind: str = "svg"
    format: str = "png"
    width: int | None = Field(default=None, ge=1, le=8000)
    height: int | None = Field(default=None, ge=1, le=8000)
    background: str = "#ffffff"
    name: str = Field(default="design", min_length=1, max_length=80)


def _owner(user: dict) -> str:
    return str(user.get("sub") or user.get("preferred_username") or user.get("email") or "ai-user")[:64]


@router.post("/design/render")
async def render_design(body: DesignRenderIn, user=Depends(current_user)):
    try:
        data, media_type, disposition = await MediaServiceClient().render_design(
            source=body.source,
            kind=body.kind,
            fmt=body.format,
            width=body.width,
            height=body.height,
            background=body.background,
            name=body.name,
            owner=_owner(user),
        )
    except MediaServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": disposition},
    )
