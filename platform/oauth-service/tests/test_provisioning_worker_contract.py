import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SERVICE_ROOT = REPO_ROOT / "platform" / "oauth-service"
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))
if str(REPO_ROOT / "shared" / "libraries" / "python") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "shared" / "libraries" / "python"))

from app.core.provisioning_worker import domain_confirmation_is_valid


def test_domain_job_requires_explicit_active_confirmation():
    assert domain_confirmation_is_valid({"status": "active", "subdomain": "alice.shopnoltd.dpdns.org"})


def test_domain_job_rejects_empty_or_unconfirmed_provider_responses():
    assert not domain_confirmation_is_valid(None)
    assert not domain_confirmation_is_valid({})
    assert not domain_confirmation_is_valid({"status": "pending", "subdomain": "alice.shopnoltd.dpdns.org"})
    assert not domain_confirmation_is_valid({"status": "active", "subdomain": ""})
    assert not domain_confirmation_is_valid({"status": "active", "subdomain": None})
