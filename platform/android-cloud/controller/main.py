from __future__ import annotations

import os
import secrets
import time
from dataclasses import dataclass
from typing import Any

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from pydantic import BaseModel, Field

NAMESPACE = os.getenv("ANDROID_CLOUD_NAMESPACE", "shopno-android")
EMULATOR_IMAGE = os.getenv("ANDROID_CLOUD_EMULATOR_IMAGE", "us-docker.pkg.dev/android-emulator-268719/images/30-google-x64:30.1.2")
GATEWAY_IMAGE = os.getenv("ANDROID_CLOUD_GATEWAY_IMAGE", "ghcr.io/asaduzzamanbheramara-prog/shopnoltd-android-cloud-gateway:latest")
PUBLIC_GATEWAY_BASE = os.getenv("ANDROID_CLOUD_GATEWAY_BASE", "https://android.shopnoltd.dpdns.org/sessions")
PUBLIC_HOST = os.getenv("ANDROID_CLOUD_PUBLIC_HOST", "android.shopnoltd.dpdns.org")
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
MAX_SESSIONS = int(os.getenv("ANDROID_CLOUD_MAX_SESSIONS", "1"))
SESSION_TTL_SECONDS = int(os.getenv("ANDROID_CLOUD_SESSION_TTL_SECONDS", "1800"))
TURN_URLS = [x.strip() for x in os.getenv("ANDROID_CLOUD_TURN_URLS", "").split(",") if x.strip()]
TURN_USERNAME = os.getenv("ANDROID_CLOUD_TURN_USERNAME", "")
TURN_CREDENTIAL = os.getenv("ANDROID_CLOUD_TURN_CREDENTIAL", "")

try:
    config.load_incluster_config()
except Exception:
    config.load_kube_config()

core = client.CoreV1Api()
networking = client.NetworkingV1Api()
app = FastAPI(title="Shopnoltd Android Cloud", version="1.0.0")

@dataclass
class Session:
    session_id: str
    user_id: str
    emulator_name: str
    gateway_name: str
    created_at: float
    last_seen: float

sessions: dict[str, Session] = {}

class CreateSessionIn(BaseModel):
    ttl_seconds: int = Field(default=SESSION_TTL_SECONDS, ge=300, le=14400)

def user_from_request(request: Request) -> str:
    if not JWT_SECRET:
        raise HTTPException(status_code=503, detail="android_cloud_auth_not_configured")
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing_bearer_token")
    try:
        payload = jwt.decode(auth.split(" ", 1)[1].strip(), JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="invalid_bearer_token")
    subject = str(payload.get("sub", "")).strip()
    if not subject:
        raise HTTPException(status_code=401, detail="token_has_no_subject")
    return subject

def safe_name(prefix: str, session_id: str) -> str:
    return f"{prefix}-{session_id[:16]}"

def emulator_pod(session: Session) -> client.V1Pod:
    return client.V1Pod(
        metadata=client.V1ObjectMeta(name=session.emulator_name, namespace=NAMESPACE, labels={"app.kubernetes.io/name": "android-emulator", "shopnoltd.dev/session": session.session_id}),
        spec=client.V1PodSpec(
            restart_policy="Never", automount_service_account_token=False,
            containers=[client.V1Container(
                name="emulator", image=EMULATOR_IMAGE, image_pull_policy="IfNotPresent",
                ports=[client.V1ContainerPort(name="grpc", container_port=8554), client.V1ContainerPort(name="adb", container_port=5555)],
                env=[client.V1EnvVar(name="EMULATOR_PARAMS", value="-no-window -grpc 8554")],
                resources=client.V1ResourceRequirements(requests={"cpu": "2", "memory": "3Gi", "ephemeral-storage": "4Gi"}, limits={"cpu": "4", "memory": "4Gi", "ephemeral-storage": "8Gi"}),
                volume_mounts=[client.V1VolumeMount(name="android-data", mount_path="/data")],
                security_context=client.V1SecurityContext(privileged=True, allow_privilege_escalation=True),
            )],
            volumes=[client.V1Volume(name="android-data", empty_dir=client.V1EmptyDirVolumeSource(medium="Memory", size_limit="6Gi"))],
        ),
    )

def gateway_pod(session: Session) -> client.V1Pod:
    return client.V1Pod(
        metadata=client.V1ObjectMeta(name=session.gateway_name, namespace=NAMESPACE, labels={"app.kubernetes.io/name": "android-cloud-gateway", "shopnoltd.dev/session": session.session_id}),
        spec=client.V1PodSpec(
            restart_policy="Always", automount_service_account_token=False,
            containers=[client.V1Container(
                name="gateway", image=GATEWAY_IMAGE, image_pull_policy="IfNotPresent",
                env=[client.V1EnvVar(name="EMULATOR_HOST", value=f"{session.emulator_name}:8554"), client.V1EnvVar(name="SESSION_ID", value=session.session_id)],
                ports=[client.V1ContainerPort(name="http", container_port=8080)],
                resources=client.V1ResourceRequirements(requests={"cpu": "100m", "memory": "128Mi"}, limits={"cpu": "500m", "memory": "512Mi"}),
                security_context=client.V1SecurityContext(run_as_non_root=True, run_as_user=10001, allow_privilege_escalation=False),
            )],
        ),
    )

def svc(name: str, selector: dict[str, str], port: int, target: int) -> client.V1Service:
    return client.V1Service(metadata=client.V1ObjectMeta(name=name, namespace=NAMESPACE), spec=client.V1ServiceSpec(selector=selector, ports=[client.V1ServicePort(name="http", port=port, target_port=target)]))

def gateway_ingress(session: Session) -> client.V1Ingress:
    path = f"/sessions/{session.session_id}(/|$)(.*)"
    annotations = {
        "nginx.ingress.kubernetes.io/use-regex": "true",
        "nginx.ingress.kubernetes.io/rewrite-target": "/$2",
        "nginx.ingress.kubernetes.io/configuration-snippet": f"proxy_set_header X-Shopnoltd-Session {session.session_id};",
        "nginx.ingress.kubernetes.io/proxy-read-timeout": "3600",
        "nginx.ingress.kubernetes.io/proxy-send-timeout": "3600",
    }
    return client.V1Ingress(
        metadata=client.V1ObjectMeta(name=session.gateway_name, namespace=NAMESPACE, annotations=annotations),
        spec=client.V1IngressSpec(ingress_class_name="nginx", rules=[client.V1IngressRule(host=PUBLIC_HOST, http=client.V1HTTPIngressRuleValue(paths=[client.V1HTTPIngressPath(path=path, path_type="ImplementationSpecific", backend=client.V1IngressBackend(service=client.V1IngressServiceBackend(name=session.gateway_name, port=client.V1ServiceBackendPort(number=8080)))]))]),
    )

def create_kube_session(session: Session) -> None:
    try:
        core.create_namespaced_pod(NAMESPACE, emulator_pod(session))
        core.create_namespaced_service(NAMESPACE, svc(session.emulator_name, {"shopnoltd.dev/session": session.session_id, "app.kubernetes.io/name": "android-emulator"}, 8554, 8554))
        core.create_namespaced_pod(NAMESPACE, gateway_pod(session))
        core.create_namespaced_service(NAMESPACE, svc(session.gateway_name, {"shopnoltd.dev/session": session.session_id, "app.kubernetes.io/name": "android-cloud-gateway"}, 8080, 8080))
        networking.create_namespaced_ingress(NAMESPACE, gateway_ingress(session))
    except Exception:
        delete_kube_session(session)
        raise

def delete_kube_session(session: Session) -> None:
    for kind, name in (("ingress", session.gateway_name), ("pod", session.gateway_name), ("service", session.gateway_name), ("service", session.emulator_name), ("pod", session.emulator_name)):
        try:
            if kind == "pod": core.delete_namespaced_pod(name, NAMESPACE, grace_period_seconds=0)
            elif kind == "service": core.delete_namespaced_service(name, NAMESPACE)
            else: networking.delete_namespaced_ingress(name, NAMESPACE)
        except ApiException as exc:
            if exc.status != 404: raise

def cleanup_expired() -> None:
    now = time.time()
    for sid, session in list(sessions.items()):
        if now - session.last_seen > SESSION_TTL_SECONDS:
            try: delete_kube_session(session)
            finally: sessions.pop(sid, None)

@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    return {"status": "ok", "service": "android-cloud-controller"}

@app.get("/readyz")
async def readyz() -> JSONResponse:
    if not JWT_SECRET: return JSONResponse({"status": "not_ready", "reason": "auth_not_configured"}, status_code=503)
    try: core.list_namespaced_pod(NAMESPACE, limit=1)
    except Exception as exc: return JSONResponse({"status": "not_ready", "reason": str(exc)}, status_code=503)
    return JSONResponse({"status": "ready", "capacity": MAX_SESSIONS, "kvm_required": True})

@app.get("/api/v1/android-cloud/capabilities")
async def capabilities(user_id: str = Depends(user_from_request)) -> dict[str, Any]:
    return {"product": "shopnoltd_android_cloud", "user": user_id, "browser_control": True, "web_rtc": True, "apk_install": True, "mock_gps": True, "adb_public": False, "max_sessions": MAX_SESSIONS, "turn_configured": bool(TURN_URLS)}

@app.post("/api/v1/android-cloud/sessions")
async def create_session(body: CreateSessionIn, user_id: str = Depends(user_from_request)) -> dict[str, Any]:
    cleanup_expired()
    existing = next((s for s in sessions.values() if s.user_id == user_id), None)
    if existing:
        existing.last_seen = time.time(); return session_response(existing)
    if len(sessions) >= MAX_SESSIONS: raise HTTPException(status_code=429, detail="android_cloud_capacity_exhausted")
    sid = secrets.token_urlsafe(24).replace("-", "").replace("_", "")
    session = Session(sid, user_id, safe_name("aemu", sid), safe_name("agw", sid), time.time(), time.time())
    try: create_kube_session(session)
    except ApiException as exc: raise HTTPException(status_code=503, detail=f"android_cloud_provision_failed:{exc.reason}")
    sessions[sid] = session
    return session_response(session)

@app.get("/api/v1/android-cloud/sessions/{session_id}")
async def get_session(session_id: str, user_id: str = Depends(user_from_request)) -> dict[str, Any]:
    session = sessions.get(session_id)
    if not session or session.user_id != user_id: raise HTTPException(status_code=404, detail="session_not_found")
    session.last_seen = time.time(); return session_response(session)

@app.delete("/api/v1/android-cloud/sessions/{session_id}")
async def delete_session(session_id: str, user_id: str = Depends(user_from_request)) -> dict[str, Any]:
    session = sessions.get(session_id)
    if not session or session.user_id != user_id: raise HTTPException(status_code=404, detail="session_not_found")
    delete_kube_session(session); sessions.pop(session_id, None)
    return {"status": "stopped", "session_id": session_id}

def session_response(session: Session) -> dict[str, Any]:
    return {"session_id": session.session_id, "status": "starting", "gateway_url": f"{PUBLIC_GATEWAY_BASE}/{session.session_id}", "expires_at": int(session.created_at + SESSION_TTL_SECONDS), "turn": {"urls": TURN_URLS, "username": TURN_USERNAME, "credential": TURN_CREDENTIAL} if TURN_URLS else None}
