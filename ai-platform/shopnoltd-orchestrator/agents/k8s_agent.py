"""
Kubernetes agent. Wraps the official python client so the orchestrator
never shells out to `kubectl` (fewer moving parts, real error objects
instead of parsed stdout).
"""
import time
import yaml
from pathlib import Path
from kubernetes import client, config as kconfig
from kubernetes.client.rest import ApiException
from kubernetes.utils import create_from_yaml

import config


def load_k8s_config():
    if config.K8S_IN_CLUSTER:
        kconfig.load_incluster_config()
    else:
        kconfig.load_kube_config()


def apply_manifest(manifest_rel_path: str) -> tuple[bool, str]:
    """Apply (create-or-replace) a manifest file from the repo."""
    load_k8s_config()
    path = config.REPO_ROOT / manifest_rel_path
    if not path.exists():
        return False, f"Manifest not found: {path}"
    api_client = client.ApiClient()
    try:
        create_from_yaml(api_client, str(path), namespace=config.K8S_NAMESPACE)
        return True, "applied"
    except Exception as e:
        # create_from_yaml raises if the object already exists; fall back
        # to a patch for the Deployment case, which is the common one.
        msg = str(e)
        if "already exists" in msg or "Conflict" in msg:
            return _patch_existing(path)
        return False, msg


def _patch_existing(path: Path) -> tuple[bool, str]:
    apps_v1 = client.AppsV1Api()
    core_v1 = client.CoreV1Api()
    try:
        with open(path) as f:
            docs = list(yaml.safe_load_all(f))
        for doc in docs:
            if not doc:
                continue
            kind = doc.get("kind")
            name = doc["metadata"]["name"]
            ns = doc["metadata"].get("namespace", config.K8S_NAMESPACE)
            if kind == "Deployment":
                apps_v1.patch_namespaced_deployment(name, ns, doc)
            elif kind == "ConfigMap":
                core_v1.patch_namespaced_config_map(name, ns, doc)
            elif kind == "Service":
                core_v1.patch_namespaced_service(name, ns, doc)
        return True, "patched existing objects"
    except ApiException as e:
        return False, f"K8s API error on patch: {e.reason}"


def patch_deployment_image(deployment_name: str, container_name: str, image: str) -> tuple[bool, str]:
    load_k8s_config()
    apps_v1 = client.AppsV1Api()
    patch = {
        "spec": {
            "template": {
                "spec": {"containers": [{"name": container_name, "image": image}]}
            }
        }
    }
    try:
        apps_v1.patch_namespaced_deployment(deployment_name, config.K8S_NAMESPACE, patch)
        return True, "image patched"
    except ApiException as e:
        return False, f"K8s API error: {e.reason}"


def wait_for_rollout(deployment_name: str, timeout: int = None) -> tuple[bool, str]:
    load_k8s_config()
    apps_v1 = client.AppsV1Api()
    timeout = timeout or config.ROLLOUT_TIMEOUT_SECONDS
    start = time.time()
    while time.time() - start < timeout:
        try:
            dep = apps_v1.read_namespaced_deployment_status(deployment_name, config.K8S_NAMESPACE)
            status = dep.status
            desired = dep.spec.replicas or 1
            ready = status.ready_replicas or 0
            updated = status.updated_replicas or 0
            if ready >= desired and updated >= desired:
                return True, f"{ready}/{desired} replicas ready"
        except ApiException as e:
            return False, f"K8s API error: {e.reason}"
        time.sleep(5)
    return False, f"timed out after {timeout}s waiting for rollout"


def get_pod_statuses(deployment_name: str) -> list[dict]:
    load_k8s_config()
    core_v1 = client.CoreV1Api()
    pods = core_v1.list_namespaced_pod(
        config.K8S_NAMESPACE, label_selector=f"app={deployment_name}"
    )
    results = []
    for pod in pods.items:
        cs = pod.status.container_statuses or []
        waiting_reason = None
        for c in cs:
            if c.state and c.state.waiting:
                waiting_reason = c.state.waiting.reason
        results.append({
            "name": pod.metadata.name,
            "phase": pod.status.phase,
            "waiting_reason": waiting_reason,
            "restart_count": sum(c.restart_count for c in cs) if cs else 0,
        })
    return results


def get_pod_logs(pod_name: str, tail_lines: int = 200) -> str:
    load_k8s_config()
    core_v1 = client.CoreV1Api()
    try:
        return core_v1.read_namespaced_pod_log(
            pod_name, config.K8S_NAMESPACE, tail_lines=tail_lines
        )
    except ApiException as e:
        return f"[could not fetch logs: {e.reason}]"


def configmap_exists(name: str) -> bool:
    load_k8s_config()
    core_v1 = client.CoreV1Api()
    try:
        core_v1.read_namespaced_config_map(name, config.K8S_NAMESPACE)
        return True
    except ApiException:
        return False
