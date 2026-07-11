"""
Shopnoltd AI — orchestration API.

This replaces the placeholder app.py that only returned a health check.
It keeps that same health endpoint, and adds the endpoints that actually
drive the fix loop.

Run locally:
    uvicorn main:app --reload --port 8080

Trigger a full fix:
    curl -X POST http://localhost:8080/fix
    curl http://localhost:8080/fix/<job_id>
"""
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import PlainTextResponse

from agents import orchestrator, k8s_agent

app = FastAPI(title="Shopnoltd AI", version="2.0.0")


@app.get("/")
def home():
    return {
        "status": "running",
        "platform": "Shopnoltd AI",
        "version": "2.0.0",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/fix")
def trigger_fix(background_tasks: BackgroundTasks):
    """
    Kick off the full scan -> build -> push -> deploy -> heal loop.
    Runs in the background; poll /fix/{job_id} for progress.
    """
    import uuid
    from datetime import datetime, timezone
    from models.schemas import FixReport

    job_id = str(uuid.uuid4())[:8]
    orchestrator.JOBS[job_id] = FixReport(
        job_id=job_id, started_at=datetime.now(timezone.utc).isoformat()
    )
    background_tasks.add_task(orchestrator._run_fix, job_id)
    return {"job_id": job_id, "status": "started"}


@app.get("/fix/{job_id}")
def fix_status(job_id: str):
    report = orchestrator.JOBS.get(job_id)
    if not report:
        raise HTTPException(status_code=404, detail="job not found")
    return report


@app.get("/logs/{deployment_name}", response_class=PlainTextResponse)
def service_logs(deployment_name: str, tail: int = 200):
    pods = k8s_agent.get_pod_statuses(deployment_name)
    if not pods:
        raise HTTPException(status_code=404, detail="no pods found for that deployment")
    return k8s_agent.get_pod_logs(pods[0]["name"], tail_lines=tail)
