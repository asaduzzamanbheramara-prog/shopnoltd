"""Server-authoritative Work Evidence/Time Tracking API."""
import json
from datetime import datetime
from decimal import Decimal
import hashlib
import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.work import Work, WorkAssignment, WorkSubmission
from app.models.work_evidence import WorkTaskConfig, WorkSession, WorkEvidence, WorkEvent

router = APIRouter(prefix="/work")
bearer = HTTPBearer()
PAYMENTS = "http://payment-service.shopno-payments.svc.cluster.local:80"

async def db():
    async with SessionLocal() as session:
        yield session

async def user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return await verify_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(401, "Invalid authentication token") from exc

def tenant_ok(work, u):
    return work and work.tenant_id == u.get("tenant_id", "default")

def parse_json(value, default):
    try: return json.loads(value) if value else default
    except Exception: return default

def session_dict(x):
    return {"id":x.id,"work_id":x.work_id,"worker_id":x.worker_id,"stage":x.stage,"started_at":x.started_at.isoformat() if x.started_at else None,"ended_at":x.ended_at.isoformat() if x.ended_at else None,"work_seconds":x.work_seconds,"watch_seconds":x.watch_seconds,"interaction_seconds":x.interaction_seconds,"eligible_watch_seconds":x.eligible_watch_seconds,"calculated_amount":str(x.calculated_amount),"currency":x.currency}

def config_dict(c):
    return {"id":c.id,"work_id":c.work_id,"task_url":c.task_url,"media_url":c.media_url,"media_type":c.media_type,"required_watch_seconds":c.required_watch_seconds,"watch_rate_per_minute":str(c.watch_rate_per_minute),"rate_currency":c.rate_currency,"rate_rules":parse_json(c.rate_rules,[]),"social_rates":parse_json(c.social_rates,{})}

def calculate_amount(seconds, rate, rules):
    # Rules are optional ordered stages: {"from_second":0,"to_second":600,"rate_per_minute":0.02}.
    if not rules: return (Decimal(seconds) / Decimal(60) * rate).quantize(Decimal("0.00000001"))
    remaining, total = int(seconds), Decimal("0")
    for rule in sorted(rules, key=lambda r:int(r.get("from_second",0))):
        start = max(0, int(rule.get("from_second",0))); end = rule.get("to_second")
        if end is None: end = seconds
        end = min(seconds, int(end))
        portion = max(0, end - max(start, seconds-remaining))
        if portion:
            total += Decimal(portion) / Decimal(60) * Decimal(str(rule.get("rate_per_minute", rate)))
    return total.quantize(Decimal("0.00000001"))

@router.get("/{work_id}/config")
async def get_config(work_id:str, s:AsyncSession=Depends(db), u=Depends(user)):
    w=await s.get(Work,work_id)
    if not tenant_ok(w,u): raise HTTPException(404,"work not found")
    c=await s.scalar(select(WorkTaskConfig).where(WorkTaskConfig.work_id==work_id))
    return config_dict(c) if c else {"work_id":work_id,"task_url":None,"media_url":None,"media_type":"none","required_watch_seconds":0,"watch_rate_per_minute":"0","rate_currency":w.currency,"rate_rules":[],"social_rates":{}}

@router.put("/{work_id}/config")
async def put_config(work_id:str, body:dict, s:AsyncSession=Depends(db), u=Depends(user)):
    w=await s.get(Work,work_id)
    if not tenant_ok(w,u): raise HTTPException(404,"work not found")
    if w.creator_id!=u["sub"]: raise HTTPException(403,"only the creator can configure work")
    c=await s.scalar(select(WorkTaskConfig).where(WorkTaskConfig.work_id==work_id))
    if not c: c=WorkTaskConfig(work_id=work_id); s.add(c)
    c.task_url=str(body.get("task_url") or "") or None; c.media_url=str(body.get("media_url") or "") or None
    c.media_type=str(body.get("media_type") or "none").lower()
    c.required_watch_seconds=max(0,int(body.get("required_watch_seconds",0)))
    c.watch_rate_per_minute=Decimal(str(body.get("watch_rate_per_minute",0)))
    if c.watch_rate_per_minute<0: raise HTTPException(422,"watch rate cannot be negative")
    c.rate_currency=str(body.get("rate_currency") or w.currency).upper()
    c.rate_rules=json.dumps(body.get("rate_rules") or [])
    c.social_rates=json.dumps(body.get("social_rates") or {})
    await s.commit(); await s.refresh(c); return config_dict(c)

@router.post("/{work_id}/sessions",status_code=201)
async def create_session(work_id:str,s:AsyncSession=Depends(db),u=Depends(user)):
    w=await s.get(Work,work_id)
    if not tenant_ok(w,u): raise HTTPException(404,"work not found")
    a=await s.scalar(select(WorkAssignment).where(WorkAssignment.work_id==work_id,WorkAssignment.worker_id==u["sub"],WorkAssignment.status=="active"))
    if not a: raise HTTPException(409,"accept the work before starting")
    active=await s.scalar(select(WorkSession).where(WorkSession.work_id==work_id,WorkSession.worker_id==u["sub"],WorkSession.stage.not_in(["finished","submitted"])))
    if active: return session_dict(active)
    x=WorkSession(work_id=work_id,worker_id=u["sub"],stage="before",currency=w.currency); s.add(x); await s.commit(); await s.refresh(x); return session_dict(x)

@router.get("/sessions/{session_id}")
async def get_session(session_id:str,s:AsyncSession=Depends(db),u=Depends(user)):
    x=await s.get(WorkSession,session_id)
    if not x or x.worker_id!=u["sub"]: raise HTTPException(404,"session not found")
    return session_dict(x)

@router.post("/sessions/{session_id}/start")
async def start_session(session_id:str,s:AsyncSession=Depends(db),u=Depends(user)):
    x=await s.get(WorkSession,session_id)
    if not x or x.worker_id!=u["sub"]: raise HTTPException(404,"session not found")
    if x.stage in {"finished","submitted"}: raise HTTPException(409,"session already finished")
    now=datetime.utcnow(); x.stage="working"; x.started_at=x.started_at or now; x.last_heartbeat_at=now
    s.add(WorkEvent(session_id=x.id,work_id=x.work_id,worker_id=u["sub"],event_type="work_started",event_at=now,rate_basis="server_start"))
    await s.commit(); return session_dict(x)

@router.post("/sessions/{session_id}/heartbeat")
async def heartbeat(session_id:str,body:dict,s:AsyncSession=Depends(db),u=Depends(user)):
    x=await s.get(WorkSession,session_id)
    if not x or x.worker_id!=u["sub"]: raise HTTPException(404,"session not found")
    if x.stage!="working" or not x.last_heartbeat_at: raise HTTPException(409,"session is not working")
    now=datetime.utcnow(); delta=min(max(int((now-x.last_heartbeat_at).total_seconds()),0),30)
    visible=bool(body.get("visible",True)); playing=bool(body.get("playing",False)); interaction=bool(body.get("interacting",False))
    # Work time is server elapsed time; watch time is only credited when playback is active and visible.
    x.work_seconds += delta
    if visible and playing:
        x.watch_seconds += delta; x.eligible_watch_seconds += delta
    if visible and interaction: x.interaction_seconds += delta
    x.last_heartbeat_at=now
    payload={"visible":visible,"playing":playing,"position":body.get("position"),"ready":body.get("ready",False)}
    s.add(WorkEvent(session_id=x.id,work_id=x.work_id,worker_id=u["sub"],event_type="playback_heartbeat",event_at=now,duration_seconds=delta,payload_json=json.dumps(payload)))
    c=await s.scalar(select(WorkTaskConfig).where(WorkTaskConfig.work_id==x.work_id))
    if c:
        x.calculated_amount=calculate_amount(x.eligible_watch_seconds,Decimal(str(c.watch_rate_per_minute)),parse_json(c.rate_rules,[])); x.currency=c.rate_currency
    await s.commit(); return session_dict(x)

@router.post("/sessions/{session_id}/event")
async def event(session_id:str,body:dict,s:AsyncSession=Depends(db),u=Depends(user)):
    x=await s.get(WorkSession,session_id)
    if not x or x.worker_id!=u["sub"]: raise HTTPException(404,"session not found")
    kind=str(body.get("event_type") or "").strip().lower()
    allowed={"play","pause","seek","buffer","visibility_hidden","visibility_visible","like","comment","share","follow","rating","link_open","custom"}
    if kind not in allowed: raise HTTPException(422,"unsupported work event")
    c=await s.scalar(select(WorkTaskConfig).where(WorkTaskConfig.work_id==x.work_id)); rates=parse_json(c.social_rates,{}) if c else {}
    basis=json.dumps({"rate":rates.get(kind),"currency":c.rate_currency if c else x.currency})
    s.add(WorkEvent(session_id=x.id,work_id=x.work_id,worker_id=u["sub"],event_type=kind,event_at=datetime.utcnow(),rate_basis=basis,payload_json=json.dumps(body.get("payload") or {})))
    await s.commit(); return {"recorded":True,"event_type":kind,"timestamp":datetime.utcnow().isoformat(),"rate_basis":json.loads(basis)}

@router.post("/sessions/{session_id}/evidence",status_code=201)
async def evidence(session_id:str,body:dict,s:AsyncSession=Depends(db),u=Depends(user)):
    x=await s.get(WorkSession,session_id)
    if not x or x.worker_id!=u["sub"]: raise HTTPException(404,"session not found")
    kind=str(body.get("kind") or "").lower(); allowed={"before","start","checkpoint","end","social","other"}
    if kind not in allowed: raise HTTPException(422,"unsupported evidence type")
    data=str(body.get("data_url") or ""); url=str(body.get("evidence_url") or "")
    if not data and not url: raise HTTPException(422,"evidence data or URL is required")
    if len(data)>8_000_000: raise HTTPException(413,"evidence image is too large")
    e=WorkEvidence(session_id=x.id,work_id=x.work_id,worker_id=u["sub"],kind=kind,title=str(body.get("title") or "") or None,evidence_url=url or None,data_url=data or None,metadata_json=json.dumps(body.get("metadata") or {}))
    s.add(e); await s.commit(); await s.refresh(e)
    return {"id":e.id,"kind":e.kind,"title":e.title,"evidence_url":e.evidence_url,"captured_at":e.captured_at.isoformat()}

@router.get("/{work_id}/evidence")
async def list_evidence(work_id:str,s:AsyncSession=Depends(db),u=Depends(user)):
    w=await s.get(Work,work_id)
    if not tenant_ok(w,u): raise HTTPException(404,"work not found")
    q=select(WorkEvidence).where(WorkEvidence.work_id==work_id,WorkEvidence.deleted_at.is_(None)).order_by(desc(WorkEvidence.captured_at))
    result=await s.execute(q)
    return [{"id":e.id,"session_id":e.session_id,"kind":e.kind,"title":e.title,"evidence_url":e.evidence_url,"data_url":e.data_url,"metadata":parse_json(e.metadata_json,{}),"captured_at":e.captured_at.isoformat()} for e in result.scalars().all() if e.worker_id==u["sub"] or w.creator_id==u["sub"]]

@router.patch("/evidence/{evidence_id}")
async def edit_evidence(evidence_id:str,body:dict,s:AsyncSession=Depends(db),u=Depends(user)):
    e=await s.get(WorkEvidence,evidence_id)
    if not e or e.deleted_at: raise HTTPException(404,"evidence not found")
    w=await s.get(Work,e.work_id)
    if e.worker_id!=u["sub"] and w.creator_id!=u["sub"]: raise HTTPException(403,"not permitted")
    if "title" in body: e.title=str(body["title"]).strip() or None
    if "metadata" in body: e.metadata_json=json.dumps(body["metadata"] or {})
    await s.commit(); return {"updated":True,"id":e.id}

@router.delete("/evidence/{evidence_id}")
async def delete_evidence(evidence_id:str,s:AsyncSession=Depends(db),u=Depends(user)):
    e=await s.get(WorkEvidence,evidence_id)
    if not e or e.deleted_at: raise HTTPException(404,"evidence not found")
    w=await s.get(Work,e.work_id)
    if e.worker_id!=u["sub"] and w.creator_id!=u["sub"]: raise HTTPException(403,"not permitted")
    e.deleted_at=datetime.utcnow(); s.add(WorkEvent(session_id=e.session_id,work_id=e.work_id,worker_id=u["sub"],event_type="evidence_deleted",event_at=datetime.utcnow(),payload_json=json.dumps({"evidence_id":e.id}))); await s.commit(); return {"deleted":True}

@router.post("/sessions/{session_id}/finish")
async def finish_session(session_id:str,s:AsyncSession=Depends(db),u=Depends(user)):
    x=await s.get(WorkSession,session_id)
    if not x or x.worker_id!=u["sub"]: raise HTTPException(404,"session not found")
    if x.stage!="working": raise HTTPException(409,"session is not working")
    now=datetime.utcnow(); x.ended_at=now; x.stage="finished"
    if x.last_heartbeat_at:
        x.work_seconds += min(max(int((now-x.last_heartbeat_at).total_seconds()),0),30)
    c=await s.scalar(select(WorkTaskConfig).where(WorkTaskConfig.work_id==x.work_id))
    if c: x.calculated_amount=calculate_amount(x.eligible_watch_seconds,Decimal(str(c.watch_rate_per_minute)),parse_json(c.rate_rules,[])); x.currency=c.rate_currency
    s.add(WorkEvent(session_id=x.id,work_id=x.work_id,worker_id=u["sub"],event_type="work_finished",event_at=now,rate_basis=json.dumps({"eligible_watch_seconds":x.eligible_watch_seconds,"amount":str(x.calculated_amount),"currency":x.currency})))
    await s.commit(); return session_dict(x)

@router.post("/sessions/{session_id}/submit",status_code=201)
async def submit_session(session_id:str,s:AsyncSession=Depends(db),u=Depends(user)):
    x=await s.get(WorkSession,session_id)
    if not x or x.worker_id!=u["sub"]: raise HTTPException(404,"session not found")
    if x.stage!="finished": raise HTTPException(409,"finish the work before submitting")
    pending=await s.scalar(select(WorkSubmission).where(WorkSubmission.work_id==x.work_id,WorkSubmission.worker_id==u["sub"],WorkSubmission.status=="pending"))
    if pending: raise HTTPException(409,"a submission is already pending")
    proof=json.dumps({"session_id":x.id,"work_seconds":x.work_seconds,"watch_seconds":x.watch_seconds,"eligible_watch_seconds":x.eligible_watch_seconds,"calculated_amount":str(x.calculated_amount),"currency":x.currency})
    sub=WorkSubmission(work_id=x.work_id,worker_id=u["sub"],proof=proof); s.add(sub); x.stage="submitted"
    await s.commit(); await s.refresh(sub); return {"id":sub.id,"session_id":x.id,"status":sub.status,"calculated_amount":str(x.calculated_amount),"currency":x.currency}

@router.post("/submissions/{submission_id}/approve")
async def approve_submission(submission_id:str,creds:HTTPAuthorizationCredentials=Depends(bearer),s:AsyncSession=Depends(db),u=Depends(user)):
    sub=await s.get(WorkSubmission,submission_id); w=await s.get(Work,sub.work_id) if sub else None
    if not sub or not w: raise HTTPException(404,"submission not found")
    if w.creator_id!=u["sub"]: raise HTTPException(403,"only the creator can approve")
    if sub.status!="pending": raise HTTPException(409,"submission already reviewed")
    data=parse_json(sub.proof,{}) ; amount=Decimal(str(data.get("calculated_amount",0))); currency=str(data.get("currency") or w.currency)
    key="work-evidence-settle:"+hashlib.sha256(sub.id.encode()).hexdigest()
    payload={"to_user_id":sub.worker_id,"currency":currency,"amount":float(amount),"note":f"work:{sub.id}:verified-time","idempotency_key":key}
    try:
        async with httpx.AsyncClient(timeout=15) as client: r=await client.post(f"{PAYMENTS}/api/v1/transfers",headers={"Authorization":f"Bearer {creds.credentials}"},json=payload)
    except (httpx.ConnectError,httpx.ConnectTimeout,httpx.ReadTimeout) as exc: raise HTTPException(503,"Payment service unavailable; submission remains pending") from exc
    if r.status_code>=400: raise HTTPException(409,{"message":"verified reward settlement failed; submission remains pending","payment_error":r.text})
    sub.status="approved"; sub.reviewer_id=u["sub"]; sub.reviewed_at=datetime.utcnow(); sub.review_note=f"Verified reward settled: {amount} {currency}"
    a=await s.scalar(select(WorkAssignment).where(WorkAssignment.work_id=w.id,WorkAssignment.worker_id=sub.worker_id));
    if a: a.status="completed"
    await s.commit(); return {"id":sub.id,"status":sub.status,"settled_amount":str(amount),"currency":currency}
