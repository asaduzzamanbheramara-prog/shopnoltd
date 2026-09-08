import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_secret, encrypt_secret, mask_secret, require_admin
from app.db.models import AIProvider
from app.db.session import get_db
from app.schemas.ai_provider import ProviderCreate, ProviderOut, ProviderUpdate
from app.services.model_router import ADAPTER_MAP, _build_adapter

router = APIRouter(
    prefix="/api/ai/providers", tags=["ai-providers"], dependencies=[Depends(require_admin)]
)


def _to_out(p: AIProvider) -> ProviderOut:
    plaintext = decrypt_secret(p.api_key_encrypted) if p.api_key_encrypted else None
    return ProviderOut(
        id=p.id,
        name=p.name,
        provider_type=p.provider_type,
        base_url=p.base_url,
        is_active=p.is_active,
        api_key_masked=mask_secret(plaintext) if plaintext else None,
        extra_config=p.extra_config,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


@router.get("", response_model=list[ProviderOut])
async def list_providers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AIProvider).order_by(AIProvider.name))
    return [_to_out(p) for p in result.scalars().all()]


@router.post("", response_model=ProviderOut, status_code=status.HTTP_201_CREATED)
async def create_provider(payload: ProviderCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(AIProvider).where(AIProvider.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, f"Provider '{payload.name}' already exists")

    provider = AIProvider(
        name=payload.name,
        provider_type=payload.provider_type,
        api_key_encrypted=encrypt_secret(payload.api_key) if payload.api_key else None,
        base_url=payload.base_url,
        is_active=payload.is_active,
        extra_config=payload.extra_config,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return _to_out(provider)


@router.get("/{provider_id}", response_model=ProviderOut)
async def get_provider(provider_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    provider = await db.get(AIProvider, provider_id)
    if not provider:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Provider not found")
    return _to_out(provider)


@router.patch("/{provider_id}", response_model=ProviderOut)
async def update_provider(
    provider_id: uuid.UUID, payload: ProviderUpdate, db: AsyncSession = Depends(get_db)
):
    provider = await db.get(AIProvider, provider_id)
    if not provider:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Provider not found")

    if payload.name is not None:
        provider.name = payload.name
    if payload.api_key is not None:
        provider.api_key_encrypted = encrypt_secret(payload.api_key)
    if payload.base_url is not None:
        provider.base_url = payload.base_url
    if payload.is_active is not None:
        provider.is_active = payload.is_active
    if payload.extra_config is not None:
        provider.extra_config = payload.extra_config

    await db.commit()
    await db.refresh(provider)
    return _to_out(provider)


@router.post("/{provider_id}/activate", response_model=ProviderOut)
async def activate_provider(provider_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    provider = await db.get(AIProvider, provider_id)
    if not provider:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Provider not found")
    provider.is_active = True
    await db.commit()
    await db.refresh(provider)
    return _to_out(provider)


@router.post("/{provider_id}/deactivate", response_model=ProviderOut)
async def deactivate_provider(provider_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    provider = await db.get(AIProvider, provider_id)
    if not provider:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Provider not found")
    provider.is_active = False
    await db.commit()
    await db.refresh(provider)
    return _to_out(provider)


@router.post("/{provider_id}/test")
async def test_provider(provider_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Test provider reachability/authentication without exposing credentials."""
    provider = await db.get(AIProvider, provider_id)
    if not provider:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Provider not found")

    if provider.provider_type not in ADAPTER_MAP:
        return {
            "provider": provider.name,
            "ok": False,
            "status": "unsupported",
            "message": f"No adapter implemented for provider type '{provider.provider_type}'.",
        }

    try:
        adapter = _build_adapter(provider)
        ok = await adapter.health_check()
    except Exception as exc:
        # Never return upstream response bodies or exception data because they
        # can contain credential material, request headers, or provider internals.
        message = str(exc).lower()
        if "api key" in message or "credential" in message or "configured" in message:
            safe_message = "Provider credential is missing or not configured."
        elif isinstance(exc, TimeoutError):
            safe_message = "Provider connectivity test timed out."
        else:
            safe_message = "Provider connectivity/authentication test failed."
        return {
            "provider": provider.name,
            "ok": False,
            "status": "error",
            "message": safe_message,
        }

    return {
        "provider": provider.name,
        "ok": ok,
        "status": "connected" if ok else "rejected",
        "message": "Provider authentication/connectivity verified." if ok else "Provider rejected the connectivity check.",
    }


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(provider_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    provider = await db.get(AIProvider, provider_id)
    if not provider:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Provider not found")
    await db.delete(provider)
    await db.commit()
