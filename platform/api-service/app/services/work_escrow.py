"""Trusted API-service client for payment-service Work Marketplace escrow."""
import hashlib
import os
from decimal import Decimal

import httpx
from fastapi import HTTPException

PAYMENTS = "http://payment-service.shopno-payments.svc.cluster.local:80"


def _headers():
    key = os.getenv("PAYMENT_INTERNAL_API_KEY", "").strip()
    if not key:
        raise HTTPException(503, "Work escrow payment bridge is not configured; task cannot be published or paid")
    return {"X-Internal-API-Key": key}


async def _request(path: str, payload: dict):
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{PAYMENTS}/api/v1/internal/work-escrow/{path}", headers=_headers(), json=payload)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        raise HTTPException(503, "Work escrow payment service unavailable; no task status was changed") from exc
    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise HTTPException(409, {"message": "Work escrow operation failed", "payment_error": detail})
    return response.json()


async def reserve_work_budget(work):
    amount = (Decimal(str(work.reward_amount)) * Decimal(int(work.max_workers))).quantize(Decimal("0.00000001"))
    return await _request("reserve", {
        "tenant_id": work.tenant_id, "creator_id": work.creator_id,
        "work_id": work.id, "currency": work.currency, "amount": str(amount),
    })


async def payout_work_escrow(work, recipient_id: str, amount: Decimal, idempotency_scope: str, note: str):
    amount = Decimal(str(amount)).quantize(Decimal("0.00000001"))
    if amount <= 0:
        return {"status": "skipped", "amount": "0"}
    key = "work-escrow-pay:" + hashlib.sha256(f"{work.id}:{idempotency_scope}".encode()).hexdigest()
    return await _request("payout", {
        "tenant_id": work.tenant_id, "creator_id": work.creator_id,
        "work_id": work.id, "recipient_id": recipient_id,
        "currency": work.currency, "amount": str(amount),
        "idempotency_key": key, "note": note[:128],
    })


async def release_unused_work_budget(work):
    return await _request("release-unused", {
        "tenant_id": work.tenant_id, "creator_id": work.creator_id,
        "work_id": work.id, "currency": work.currency,
    })
