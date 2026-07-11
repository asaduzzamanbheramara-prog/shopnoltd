from enum import Enum
from typing import Optional, List
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
    last_error: Optional[str] = None
    detected_issue: Optional[str] = None
    image_tag: Optional[str] = None


class FixReport(BaseModel):
    job_id: str
    started_at: str
    finished_at: Optional[str] = None
    overall_status: StepStatus = StepStatus.RUNNING
    services: List[ServiceRunLog] = []
    notes: List[str] = []
