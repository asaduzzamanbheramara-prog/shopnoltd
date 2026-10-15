import sys
from pathlib import Path
from types import SimpleNamespace

# Resolve this service's app package and the repository's shared Python library.
REPO_ROOT = Path(__file__).resolve().parents[3]
SERVICE_ROOT = REPO_ROOT / "platform" / "oauth-service"
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))
if str(REPO_ROOT / "shared" / "libraries" / "python") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "shared" / "libraries" / "python"))

from app.api.users import _ensure_account_provisioning_jobs


class RecordingSession:
    def __init__(self):
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)


def test_enqueue_is_idempotent_for_subdomain_and_mailbox_jobs():
    import asyncio
    from sqlalchemy.dialects import postgresql

    session = RecordingSession()
    user = SimpleNamespace(id="user-123", keycloak_id="kc-subject-456")

    asyncio.run(_ensure_account_provisioning_jobs(session, user))

    assert len(session.statements) == 2
    compiled = [str(statement.compile(dialect=postgresql.dialect())) for statement in session.statements]
    params = [statement.compile(dialect=postgresql.dialect()).params for statement in session.statements]

    assert all("INSERT INTO account_provisioning_jobs" in sql for sql in compiled)
    assert all("ON CONFLICT ON CONSTRAINT uq_account_provisioning_user_resource DO NOTHING" in sql for sql in compiled)
    assert {item["resource_type"] for item in params} == {"subdomain", "mailbox"}
    assert all(item["user_id"] == "user-123" for item in params)
    assert all(item["keycloak_id"] == "kc-subject-456" for item in params)
    assert all(item["status"] == "pending" and item["attempts"] == 0 for item in params)

def test_outbox_model_enforces_valid_resource_status_and_attempt_count():
    from app.models.models import AccountProvisioningJob

    constraint_names = {
        constraint.name for constraint in AccountProvisioningJob.__table__.constraints
    }
    assert "uq_account_provisioning_user_resource" in constraint_names
    assert "ck_account_provisioning_resource_type" in constraint_names
    assert "ck_account_provisioning_status" in constraint_names
    assert "ck_account_provisioning_attempts_nonnegative" in constraint_names
