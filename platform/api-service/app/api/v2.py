"""Unified marketplace/social facade. Keeps the browser on one API origin."""

from datetime import datetime
from decimal import Decimal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.work import Work, WorkAssignment, WorkSubmission

router = APIRouter()
bearer = HTTPBearer()
SOCIAL = "http://social-service.shopno-platform.svc.cluster.local:80"
PAYMENTS = "http://payment-service.shopno-payments.svc.cluster.local:80"


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return await verify_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(401, "Invalid authentication token") from exc


async def db():
    async with SessionLocal() as session:
        yield session


async def social_call(method: str, path: str, token: str, **kwargs):
    headers = {"Authorization": f"Bearer {token}" } if token else {}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.request(method, f"{SOCIAL}{path}", headers=headers, **kwargs)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        raise HTTPException(503, "Social service unavailable") from exc
    if response.status_code >= 400:
        try: detail = response.json()
        except Exception: detail = response.text
        raise HTTPException(response.status_code, detail)
    return response.json() if response.text else None


async def settle_reward(user, submission_id: str, amount: Decimal, currency: str, token: str):
    payload = {
        "to_user_id": user["worker_id"],
        "currency": currency,
        "amount": float(amount),
        "note": f"work:{submission_id}",
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{PAYMENTS}/api/v1/transfers",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        raise HTTPException(503, "Payment service unavailable; submission remains pending") from exc
    if response.status_code >= 400:
        try: detail = response.json()
        except Exception: detail = response.text
        raise HTTPException(409, {"message": "Reward settlement failed; submission remains pending", "payment_error": detail})
    return response.json()


def work_dict(w: Work):
    return {"id": w.id, "tenant_id": w.tenant_id, "creator_id": w.creator_id, "title": w.title,
            "description": w.description, "requirements": w.requirements, "reward_amount": str(w.reward_amount),
            "currency": w.currency, "max_workers": w.max_workers,
            "deadline": w.deadline.isoformat() if w.deadline else None, "status": w.status,
            "created_at": w.created_at.isoformat()}


@router.get("/social/feed")
async def social_feed(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await social_call("GET", "/api/v1/feed/me", creds.credentials)


@router.get("/social/global")
async def social_global(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await social_call("GET", "/api/v1/feed/global", creds.credentials)


@router.post("/social/posts")
async def social_create_post(body: dict, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await social_call("POST", "/api/v1/posts", creds.credentials, json=body)


@router.get("/social/posts/{post_id}")
async def social_post(post_id: str):
    return await social_call("GET", f"/api/v1/posts/{post_id}", "")


@router.post("/social/posts/{post_id}/like")
async def social_like(post_id: str, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await social_call("POST", f"/api/v1/likes/{post_id}", creds.credentials)


@router.delete("/social/posts/{post_id}/like")
async def social_unlike(post_id: str, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await social_call("DELETE", f"/api/v1/likes/{post_id}", creds.credentials)


@router.post("/social/posts/{post_id}/share")
async def social_share(post_id: str, body: dict | None = None, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await social_call("POST", f"/api/v1/shares/{post_id}", creds.credentials, json=body or {})


@router.post("/social/posts/{post_id}/view")
async def social_view(post_id: str, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await social_call("POST", f"/api/v1/views/{post_id}", creds.credentials)


@router.get("/social/posts/{post_id}/views")
async def social_views(post_id: str):
    return await social_call("GET", f"/api/v1/views/{post_id}/count", "")


@router.get("/social/posts/{post_id}/comments")
async def social_comments(post_id: str):
    return await social_call("GET", f"/api/v1/posts/{post_id}/comments", "")


@router.post("/social/posts/{post_id}/comments")
async def social_comment(post_id: str, body: dict, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await social_call("POST", f"/api/v1/posts/{post_id}/comments", creds.credentials, json=body)


@router.get("/works")
async def list_works(status: str = Query("open"), limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), s: AsyncSession = Depends(db), user=Depends(current_user)):
    query = select(Work).where(Work.tenant_id == user.get("tenant_id", "default"))
    if status != "all": query = query.where(Work.status == status)
    result = await s.execute(query.order_by(desc(Work.created_at)).limit(limit).offset(offset))
    return [work_dict(w) for w in result.scalars().all()]


@router.post("/works", status_code=201)
async def create_work(body: dict, s: AsyncSession = Depends(db), user=Depends(current_user)):
    title, description, reward = str(body.get("title", "")).strip(), str(body.get("description", "")).strip(), body.get("reward_amount")
    if not title or not description or reward is None: raise HTTPException(422, "title, description and reward_amount are required")
    try: reward_decimal = Decimal(str(reward))
    except Exception as exc: raise HTTPException(422, "reward_amount must be numeric") from exc
    if reward_decimal <= 0: raise HTTPException(422, "reward_amount must be greater than zero")
    max_workers = int(body.get("max_workers", 1))
    if not 1 <= max_workers <= 1000: raise HTTPException(422, "max_workers must be between 1 and 1000")
    deadline = None
    if body.get("deadline"):
        try: deadline = datetime.fromisoformat(str(body["deadline"]).replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError as exc: raise HTTPException(422, "deadline must be ISO-8601") from exc
    work = Work(tenant_id=user.get("tenant_id", "default"), creator_id=user["sub"], title=title, description=description,
                requirements=str(body.get("requirements", "")) or None, reward_amount=reward_decimal,
                currency=str(body.get("currency", "BDT")).upper(), max_workers=max_workers, deadline=deadline, status="open")
    s.add(work); await s.commit(); await s.refresh(work)
    return work_dict(work)


@router.get("/works/{work_id}")
async def get_work(work_id: str, s: AsyncSession = Depends(db), user=Depends(current_user)):
    work = await s.get(Work, work_id)
    if not work or work.tenant_id != user.get("tenant_id", "default"): raise HTTPException(404, "work not found")
    return work_dict(work)


@router.post("/works/{work_id}/accept")
async def accept_work(work_id: str, s: AsyncSession = Depends(db), user=Depends(current_user)):
    work = await s.get(Work, work_id)
    if not work or work.tenant_id != user.get("tenant_id", "default"): raise HTTPException(404, "work not found")
    if work.creator_id == user["sub"]: raise HTTPException(400, "creator cannot accept own work")
    if work.status != "open": raise HTTPException(409, "work is not open")
    existing = await s.scalar(select(WorkAssignment).where(WorkAssignment.work_id == work_id, WorkAssignment.worker_id == user["sub"]))
    if existing: return {"accepted": True, "already": True}
    count = await s.scalar(select(func.count(WorkAssignment.id)).where(WorkAssignment.work_id == work_id, WorkAssignment.status == "active"))
    if int(count or 0) >= work.max_workers:
        work.status = "full"; await s.commit(); raise HTTPException(409, "work has no remaining slots")
    s.add(WorkAssignment(work_id=work_id, worker_id=user["sub"], status="active"))
    if int(count or 0) + 1 >= work.max_workers: work.status = "full"
    await s.commit(); return {"accepted": True, "work_id": work_id}


@router.get("/works/active/me")
async def active_works(s: AsyncSession = Depends(db), user=Depends(current_user)):
    result = await s.execute(select(Work, WorkAssignment).join(WorkAssignment, WorkAssignment.work_id == Work.id)
                             .where(WorkAssignment.worker_id == user["sub"], WorkAssignment.status == "active")
                             .order_by(desc(WorkAssignment.accepted_at)))
    return [{"work": work_dict(w), "assignment_id": a.id, "accepted_at": a.accepted_at.isoformat()} for w, a in result.all()]


@router.post("/works/{work_id}/submit", status_code=201)
async def submit_work(work_id: str, body: dict, s: AsyncSession = Depends(db), user=Depends(current_user)):
    proof = str(body.get("proof", "")).strip()
    if not proof: raise HTTPException(422, "proof is required")
    work = await s.get(Work, work_id)
    if not work or work.tenant_id != user.get("tenant_id", "default"): raise HTTPException(404, "work not found")
    assignment = await s.scalar(select(WorkAssignment).where(WorkAssignment.work_id == work_id, WorkAssignment.worker_id == user["sub"], WorkAssignment.status == "active"))
    if not assignment: raise HTTPException(409, "accept the work before submitting")
    pending = await s.scalar(select(WorkSubmission).where(WorkSubmission.work_id == work_id, WorkSubmission.worker_id == user["sub"], WorkSubmission.status == "pending"))
    if pending: raise HTTPException(409, "a submission is already pending")
    submission = WorkSubmission(work_id=work_id, worker_id=user["sub"], proof=proof)
    s.add(submission); await s.commit(); await s.refresh(submission)
    return {"id": submission.id, "work_id": work_id, "status": submission.status, "submitted_at": submission.submitted_at.isoformat()}


@router.get("/submissions/me")
async def my_submissions(s: AsyncSession = Depends(db), user=Depends(current_user)):
    result = await s.execute(select(WorkSubmission).where(WorkSubmission.worker_id == user["sub"]).order_by(desc(WorkSubmission.submitted_at)))
    return [{"id": x.id, "work_id": x.work_id, "proof": x.proof, "status": x.status, "review_note": x.review_note,
             "submitted_at": x.submitted_at.isoformat(), "reviewed_at": x.reviewed_at.isoformat() if x.reviewed_at else None} for x in result.scalars().all()]


@router.get("/works/created/me/submissions")
async def creator_submissions(s: AsyncSession = Depends(db), user=Depends(current_user)):
    result = await s.execute(select(WorkSubmission, Work).join(Work, Work.id == WorkSubmission.work_id)
                             .where(Work.creator_id == user["sub"]).order_by(desc(WorkSubmission.submitted_at)))
    return [{"id": x.id, "work": work_dict(w), "worker_id": x.worker_id, "proof": x.proof, "status": x.status,
             "review_note": x.review_note, "submitted_at": x.submitted_at.isoformat()} for x, w in result.all()]


@router.post("/submissions/{submission_id}/review")
async def review_submission(submission_id: str, body: dict, creds: HTTPAuthorizationCredentials = Depends(bearer), s: AsyncSession = Depends(db), user=Depends(current_user)):
    decision = str(body.get("decision", "")).lower()
    if decision not in {"approved", "rejected"}: raise HTTPException(422, "decision must be approved or rejected")
    submission = await s.get(WorkSubmission, submission_id)
    if not submission: raise HTTPException(404, "submission not found")
    work = await s.get(Work, submission.work_id)
    if not work or work.creator_id != user["sub"]: raise HTTPException(403, "only the creator can review this submission")
    if submission.status != "pending": raise HTTPException(409, "submission has already been reviewed")

    if decision == "approved":
        await settle_reward({"worker_id": submission.worker_id}, submission.id, Decimal(str(work.reward_amount)), work.currency, creds.credentials)

    submission.status = decision
    submission.reviewer_id = user["sub"]
    submission.review_note = str(body.get("note", "")) or None
    submission.reviewed_at = datetime.utcnow()
    assignment = await s.scalar(select(WorkAssignment).where(WorkAssignment.work_id == work.id, WorkAssignment.worker_id == submission.worker_id))
    if assignment and decision == "approved": assignment.status = "completed"
    await s.commit()
    return {"id": submission.id, "status": submission.status, "settlement": "completed" if decision == "approved" else "not_required"}
