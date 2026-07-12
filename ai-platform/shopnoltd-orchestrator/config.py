"""
Central configuration for the Shopnoltd orchestrator.
Everything is env-driven so the same code runs locally (kubeconfig) and
in-cluster (service account token).
"""
import os
from pathlib import Path

# --- Repo / workspace -------------------------------------------------
REPO_ROOT = Path(os.environ.get("SHOPNOLTD_REPO_ROOT", "/mnt/c/Users/asadu/PROJECTS/shopnoltd"))
GITHUB_REPO_URL = os.environ.get("GITHUB_REPO_URL", "")  # e.g. https://github.com/org/shopnoltd.git
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# --- Container registry (GHCR) ----------------------------------------
GHCR_REGISTRY = os.environ.get("GHCR_REGISTRY", "ghcr.io")
GHCR_NAMESPACE = os.environ.get("GHCR_NAMESPACE", "")   # e.g. your github org/user
GHCR_USERNAME = os.environ.get("GHCR_USERNAME", "")
GHCR_TOKEN = os.environ.get("GHCR_TOKEN", "")           # PAT with write:packages

# --- Kubernetes ---------------------------------------------------------
K8S_NAMESPACE = os.environ.get("K8S_NAMESPACE", "default")
# If true, use in-cluster service account; else load local kubeconfig.
K8S_IN_CLUSTER = os.environ.get("K8S_IN_CLUSTER", "false").lower() == "true"

# --- Orchestrator behavior ---------------------------------------------
MAX_RETRIES_PER_SERVICE = int(os.environ.get("MAX_RETRIES_PER_SERVICE", "3"))
ROLLOUT_TIMEOUT_SECONDS = int(os.environ.get("ROLLOUT_TIMEOUT_SECONDS", "180"))
SERVICES_CONFIG_PATH = os.environ.get("SERVICES_CONFIG_PATH", str(Path(__file__).parent / "services.yaml"))

def image_tag(service_name: str, sha: str) -> str:
    ns = GHCR_NAMESPACE or "shopnoltd"
    return f"{GHCR_REGISTRY}/{ns}/{service_name}:{sha}"
