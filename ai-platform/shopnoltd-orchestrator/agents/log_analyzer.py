"""
Turns a pod's waiting_reason + log tail into a diagnosis and a suggested
next action the orchestrator can act on automatically.

This is intentionally a small, explicit rule table rather than an LLM
call — these failure modes are well-known and deterministic, so a rule
table is faster, cheaper, and more predictable than an LLM round-trip.
The RAG/LLM agent (agents/llm_agent.py, not yet wired in) is the right
place for *novel* application errors this table doesn't recognize.
"""
from dataclasses import dataclass


@dataclass
class Diagnosis:
    issue: str
    action: str  # one of: rebuild_push, wait, create_configmap, check_db, manual


def diagnose(pod_status: dict, log_tail: str) -> Diagnosis:
    reason = (pod_status.get("waiting_reason") or "").strip()
    log_tail_lower = log_tail.lower()

    if reason == "ImagePullBackOff" or reason == "ErrImagePull":
        return Diagnosis(
            issue="Image does not exist in registry or wrong tag/name in manifest",
            action="rebuild_push",
        )

    if reason == "CrashLoopBackOff":
        if "connection refused" in log_tail_lower and "5432" in log_tail_lower:
            return Diagnosis(
                issue="App can't reach Postgres (connection refused on 5432) — "
                      "likely DB not ready yet or wrong service DNS name",
                action="wait",
            )
        if "connection refused" in log_tail_lower and "6379" in log_tail_lower:
            return Diagnosis(
                issue="App can't reach Redis (connection refused on 6379)",
                action="wait",
            )
        if "no such file or directory" in log_tail_lower and "configmap" in log_tail_lower:
            return Diagnosis(
                issue="Mounted ConfigMap volume missing",
                action="create_configmap",
            )
        if "relation" in log_tail_lower and "does not exist" in log_tail_lower:
            return Diagnosis(
                issue="Database migrations haven't been applied",
                action="check_db",
            )
        return Diagnosis(
            issue=f"CrashLoopBackOff, cause not auto-recognized. Tail: {log_tail[-500:]}",
            action="manual",
        )

    if reason in ("CreateContainerConfigError", "CreateContainerError"):
        return Diagnosis(
            issue="Referenced ConfigMap/Secret is missing or malformed",
            action="create_configmap",
        )

    if pod_status.get("phase") == "Pending":
        return Diagnosis(issue="Pod stuck Pending (scheduling/resources)", action="wait")

    return Diagnosis(issue="No obvious issue detected", action="manual")
