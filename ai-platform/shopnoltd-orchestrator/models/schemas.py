from enum import Enum

from pydantic import BaseModel


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ServiceConfig(BaseModel):
    name: str
    dockerfile: str
    context: str
    deployment_name: str
    deployment_manifest: str
    container_name: str
    health_path: str = "/"


class ServiceRunLog(BaseModel):
    service: str
    build: StepStatus = StepStatus.PENDING
    push: StepStatus = StepStatus.PENDING
    apply: StepStatus = StepStatus.PENDING
    rollout: StepStatus = StepStatus.PENDING
    healthy: StepStatus = StepStatus.PENDING
    attempts: int = 0
    last_error: str | None = None
    detected_issue: str | None = None
    image_tag: str | None = None


class FixReport(BaseModel):
    job_id: str
    started_at: str
    finished_at: str | None = None
    overall_status: StepStatus = StepStatus.RUNNING
    services: list[ServiceRunLog] = []
    notes: list[str] = []
