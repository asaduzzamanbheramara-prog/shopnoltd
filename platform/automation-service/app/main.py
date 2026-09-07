from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Automation, AutomationExecution, Base, ExecutionStatus
from app.safety import ALLOWED_TRIGGERS, validate_definition, reject_secrets
from app.schemas import AutomationCreate, EventIn

DATABASE_URL = "postgresql+psycopg://shopno:shopno@postgres.shopno-data.svc.cluster.local:5432/automation"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

app = FastAPI(title="Shopnoltd Automation Service", version="1.0.0")
bearer = HTTPBearer(auto_error=True)


def identity(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    """Temporary identity boundary: production deployment must inject verified Keycloak claims."""
    token = credentials.credentials
    # Never treat token contents as identity. The gateway should pass verified headers/claims.
    if not token:
        raise HTTPException(401, "authentication required")
    return {"subject": "verified-user", "tenant_id": "verified-tenant"}


@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "automation-service"}


@app.post("/api/v1/automations")
def create_automation(payload: AutomationCreate, user=Depends(identity)):
    try:
        validate_definition(payload.trigger_type, payload.action_type, payload.max_retries)
        reject_secrets(payload.trigger_config)
        reject_secrets(payload.action_config)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    with SessionLocal() as db:
        row = Automation(
            tenant_id=user["tenant_id"], owner_id=user["subject"], name=payload.name,
            status="disabled", trigger_type=payload.trigger_type,
            trigger_config=payload.trigger_config, action_type=payload.action_type,
            action_config=payload.action_config, max_retries=payload.max_retries,
            next_run_at=payload.next_run_at,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row


@app.get("/api/v1/automations")
def list_automations(user=Depends(identity)):
    with SessionLocal() as db:
        return db.scalars(select(Automation).where(Automation.tenant_id == user["tenant_id"]).order_by(Automation.created_at.desc())).all()


@app.post("/api/v1/automations/{automation_id}/enable")
def enable(automation_id: str, user=Depends(identity)):
    with SessionLocal() as db:
        row = db.scalar(select(Automation).where(Automation.id == automation_id, Automation.tenant_id == user["tenant_id"]))
        if not row:
            raise HTTPException(404, "automation not found")
        row.status = "enabled"
        db.commit()
        return {"id": row.id, "status": row.status}


@app.post("/api/v1/automations/{automation_id}/disable")
def disable(automation_id: str, user=Depends(identity)):
    with SessionLocal() as db:
        row = db.scalar(select(Automation).where(Automation.id == automation_id, Automation.tenant_id == user["tenant_id"]))
        if not row:
            raise HTTPException(404, "automation not found")
        row.status = "disabled"
        db.commit()
        return {"id": row.id, "status": row.status}


@app.post("/api/v1/events")
def publish_event(event: EventIn, user=Depends(identity)):
    if event.event_type not in ALLOWED_TRIGGERS:
        raise HTTPException(422, "unsupported event trigger")
    reject_secrets(event.payload)
    with SessionLocal() as db:
        rows = db.scalars(select(Automation).where(Automation.tenant_id == user["tenant_id"], Automation.status == "enabled", Automation.trigger_type == event.event_type)).all()
        created = []
        for automation in rows:
            key = f"{automation.id}:{event.idempotency_key}"
            existing = db.scalar(select(AutomationExecution).where(AutomationExecution.idempotency_key == key))
            if existing:
                continue
            execution = AutomationExecution(
                automation_id=automation.id, tenant_id=user["tenant_id"],
                idempotency_key=key, status=ExecutionStatus.QUEUED.value,
                input_payload=event.payload,
            )
            db.add(execution)
            created.append(execution)
        db.commit()
        return {"queued": len(created), "execution_ids": [x.id for x in created]}


@app.get("/api/v1/automations/{automation_id}/executions")
def executions(automation_id: str, user=Depends(identity)):
    with SessionLocal() as db:
        automation = db.scalar(select(Automation).where(Automation.id == automation_id, Automation.tenant_id == user["tenant_id"]))
        if not automation:
            raise HTTPException(404, "automation not found")
        return db.scalars(select(AutomationExecution).where(AutomationExecution.automation_id == automation_id, AutomationExecution.tenant_id == user["tenant_id"]).order_by(AutomationExecution.id.desc())).all()
