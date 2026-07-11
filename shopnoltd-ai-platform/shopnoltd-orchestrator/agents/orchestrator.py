"""
The piece that was missing: this actually ties the agents together into
the loop described as the goal —

  scan -> build -> push -> apply -> wait -> diagnose -> retry -> report

Each service is handled independently and failures in one don't block
the others. State for a running job lives in memory (JOBS dict) so the
API layer can poll progress; for production use, swap that dict for
Redis (you already have Redis running in the cluster).
"""
import uuid
import time
import yaml
from datetime import datetime, timezone

import config
from agents import github_agent, docker_agent, k8s_agent, log_analyzer
from models.schemas import ServiceConfig, ServiceRunLog, FixReport, StepStatus

JOBS: dict[str, FixReport] = {}


def _load_service_configs() -> tuple[list[ServiceConfig], list[dict]]:
    with open(config.SERVICES_CONFIG_PATH) as f:
        raw = yaml.safe_load(f)
    services = [ServiceConfig(**s) for s in raw.get("services", [])]
    configmaps = raw.get("configmaps", [])
    return services, configmaps


def start_fix_job() -> str:
    job_id = str(uuid.uuid4())[:8]
    report = FixReport(job_id=job_id, started_at=datetime.now(timezone.utc).isoformat())
    JOBS[job_id] = report
    _run_fix(job_id)  # NOTE: caller (main.py) runs this as a background task
    return job_id


def _run_fix(job_id: str) -> None:
    report = JOBS[job_id]
    try:
        services, configmaps = _load_service_configs()
    except Exception as e:
        report.notes.append(f"Failed to load services.yaml: {e}")
        report.overall_status = StepStatus.FAILED
        return

    # Step 0: make sure ConfigMaps dependent services need actually exist.
    for cm in configmaps:
        if not k8s_agent.configmap_exists(cm["name"]):
            ok, msg = k8s_agent.apply_manifest(cm["manifest"])
            report.notes.append(
                f"ConfigMap '{cm['name']}' missing -> applied {cm['manifest']}: {msg}"
                if ok else
                f"ConfigMap '{cm['name']}' missing and failed to apply: {msg}"
            )

    # Step 1: get a commit SHA to tag images with, for traceability.
    try:
        sha = github_agent.ensure_repo_current()
        report.notes.append(f"Repo synced at commit {sha}")
    except Exception as e:
        sha = "manual"
        report.notes.append(f"Could not sync repo automatically ({e}); tagging as 'manual'")

    try:
        docker_agent.login()
    except Exception as e:
        report.notes.append(f"GHCR login failed: {e}")
        report.overall_status = StepStatus.FAILED
        return

    for svc in services:
        run_log = ServiceRunLog(service=svc.name)
        report.services.append(run_log)
        _fix_one_service(svc, sha, run_log)

    any_failed = any(
        s.build == StepStatus.FAILED or s.push == StepStatus.FAILED
        or s.apply == StepStatus.FAILED or s.rollout == StepStatus.FAILED
        for s in report.services
    )
    report.overall_status = StepStatus.FAILED if any_failed else StepStatus.SUCCESS
    report.finished_at = datetime.now(timezone.utc).isoformat()


def _fix_one_service(svc: ServiceConfig, sha: str, run_log: ServiceRunLog) -> None:
    tag = config.image_tag(svc.name, sha)
    run_log.image_tag = tag

    for attempt in range(1, config.MAX_RETRIES_PER_SERVICE + 1):
        run_log.attempts = attempt

        run_log.build = StepStatus.RUNNING
        ok, msg = docker_agent.build_image(svc.dockerfile, svc.context, tag)
        run_log.build = StepStatus.SUCCESS if ok else StepStatus.FAILED
        if not ok:
            run_log.last_error = msg[-1000:]
            return  # can't proceed without an image

        run_log.push = StepStatus.RUNNING
        ok, msg = docker_agent.push_image(tag)
        run_log.push = StepStatus.SUCCESS if ok else StepStatus.FAILED
        if not ok:
            run_log.last_error = msg
            return

        run_log.apply = StepStatus.RUNNING
        ok, msg = k8s_agent.patch_deployment_image(svc.deployment_name, svc.container_name, tag)
        if not ok:
            # deployment may not exist yet at all -> apply the full manifest
            ok, msg = k8s_agent.apply_manifest(svc.deployment_manifest)
        run_log.apply = StepStatus.SUCCESS if ok else StepStatus.FAILED
        if not ok:
            run_log.last_error = msg
            return

        run_log.rollout = StepStatus.RUNNING
        ok, msg = k8s_agent.wait_for_rollout(svc.deployment_name)
        run_log.rollout = StepStatus.SUCCESS if ok else StepStatus.FAILED

        if ok:
            run_log.healthy = StepStatus.SUCCESS
            return

        # Rollout didn't succeed in time -> diagnose why and decide whether
        # to retry, wait longer, or give up and flag for a human.
        pod_statuses = k8s_agent.get_pod_statuses(svc.deployment_name)
        if not pod_statuses:
            run_log.last_error = "No pods found for deployment"
            run_log.healthy = StepStatus.FAILED
            return

        worst_pod = pod_statuses[0]
        log_tail = k8s_agent.get_pod_logs(worst_pod["name"])
        diagnosis = log_analyzer.diagnose(worst_pod, log_tail)
        run_log.detected_issue = diagnosis.issue

        if diagnosis.action == "wait":
            time.sleep(15)
            continue  # retry the wait/rollout, no rebuild needed
        elif diagnosis.action == "rebuild_push":
            continue  # loop retries build+push+apply from the top
        elif diagnosis.action == "create_configmap":
            run_log.last_error = f"{diagnosis.issue} — needs a ConfigMap fix, stopping."
            run_log.healthy = StepStatus.FAILED
            return
        else:  # check_db or manual
            run_log.last_error = f"{diagnosis.issue} — needs human review, stopping."
            run_log.healthy = StepStatus.FAILED
            return

    run_log.healthy = StepStatus.FAILED
    run_log.last_error = run_log.last_error or f"Exhausted {config.MAX_RETRIES_PER_SERVICE} attempts"
