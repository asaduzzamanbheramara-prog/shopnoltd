"""Queue worker skeleton with bounded retries; actions must be implemented by allowlisted adapters."""
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.main import SessionLocal
from app.models import Automation, AutomationExecution, ExecutionStatus
from app.safety import ALLOWED_ACTIONS


def execute_allowlisted(action_type: str, action_config: dict, payload: dict) -> dict:
    if action_type not in ALLOWED_ACTIONS:
        raise ValueError("action is not allowlisted")
    # Adapter dispatch is intentionally explicit. There is no shell/subprocess/eval path.
    if action_type == "wallet.check":
        return {"status": "accepted", "action": action_type}
    if action_type == "notify":
        return {"status": "accepted", "action": action_type}
    raise RuntimeError(f"action adapter not implemented: {action_type}")


def run_once() -> int:
    processed = 0
    with SessionLocal() as db:
        rows = db.scalars(select(AutomationExecution).where(AutomationExecution.status == ExecutionStatus.QUEUED.value).limit(25)).all()
        for execution in rows:
            automation = db.scalar(select(Automation).where(Automation.id == execution.automation_id, Automation.tenant_id == execution.tenant_id))
            if not automation or automation.status != "enabled":
                execution.status = ExecutionStatus.FAILED.value
                execution.error = "automation disabled or missing"
                db.commit()
                continue
            execution.status = ExecutionStatus.RUNNING.value
            execution.attempt += 1
            execution.started_at = datetime.now(timezone.utc)
            try:
                execution.output_payload = execute_allowlisted(automation.action_type, automation.action_config, execution.input_payload)
                execution.status = ExecutionStatus.SUCCEEDED.value
                execution.finished_at = datetime.now(timezone.utc)
            except Exception as exc:
                execution.error = str(exc)[:2000]
                if execution.attempt <= automation.max_retries:
                    execution.status = ExecutionStatus.QUEUED.value
                else:
                    execution.status = ExecutionStatus.DEAD_LETTER.value
                execution.finished_at = datetime.now(timezone.utc)
            db.commit()
            processed += 1
    return processed


if __name__ == "__main__":
    while True:
        run_once()
        time.sleep(2)
