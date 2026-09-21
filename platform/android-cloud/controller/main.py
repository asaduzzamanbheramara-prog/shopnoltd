from __future__ import annotations

import hashlib
import os
import re
import secrets
import tempfile
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jwt
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream
from pydantic import BaseModel, Field

NAMESPACE = os.getenv("ANDROID_CLOUD_NAMESPACE", "shopno-android")
EMULATOR_IMAGE = os.getenv("ANDROID_CLOUD_EMULATOR_IMAGE", "us-docker.pkg.dev/android-emulator-268719/images/30-google-x64:30.1.2")
GATEWAY_IMAGE = os.getenv("ANDROID_CLOUD_GATEWAY_IMAGE", "ghcr.io/asaduzzamanbheramara-prog/shopnoltd/android-cloud-gateway:latest")
PUBLIC_GATEWAY_BASE = os.getenv("ANDROID_CLOUD_GATEWAY_BASE", "https://android-gateway.shopnoltd.dpdns.org/sessions")
PUBLIC_HOST = os.getenv("ANDROID_CLOUD_PUBLIC_HOST", "android-gateway.shopnoltd.dpdns.org")
KEYCLOAK_ISSUER = os.getenv("KEYCLOAK_ISSUER", "https://auth.shopnoltd.dpdns.org/realms/shopnoltd").rstrip("/")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "shopnoltd-web")
KEYCLOAK_AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "api-service")
KEYCLOAK_JWKS_URL = os.getenv("KEYCLOAK_JWKS_URL", f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs")
MAX_SESSIONS = int(os.getenv("ANDROID_CLOUD_MAX_SESSIONS", "1"))
SESSION_TTL_SECONDS = int(os.getenv("ANDROID_CLOUD_SESSION_TTL_SECONDS", "1800"))
MAX_APK_BYTES = int(os.getenv("ANDROID_CLOUD_MAX_APK_BYTES", str(100 * 1024 * 1024)))
TURN_URLS = [x.strip() for x in os.getenv("ANDROID_CLOUD_TURN_URLS", "").split(",") if x.strip()]
TURN_USERNAME = os.getenv("ANDROID_CLOUD_TURN_USERNAME", "")
TURN_CREDENTIAL = os.getenv("ANDROID_CLOUD_TURN_CREDENTIAL", "")

OFFICIAL_APPS = {
    "shopnoltd": {
        "id": "shopnoltd",
        "name": "Shopnoltd",
        "url": os.getenv("ANDROID_CLOUD_SHOPNOLTD_APK_URL", "https://shopnoltd.dpdns.org/download/Shopnoltd.apk"),
    },
    "shopnoltd-admin": {
        "id": "shopnoltd-admin",
        "name": "Shopnoltd Admin",
        "url": os.getenv("ANDROID_CLOUD_SHOPNOLTD_ADMIN_APK_URL", "https://shopnoltd.dpdns.org/download/Shopnoltd-Admin.apk"),
    },
    "shopnoltd-collect": {
        "id": "shopnoltd-collect",
        "name": "ShopnoltdCollect",
        "url": os.getenv("ANDROID_CLOUD_SHOPNOLTD_COLLECT_APK_URL", "https://shopnoltd.dpdns.org/download/ShopnoltdCollect.apk"),
    },
}
PACKAGE_RE = re.compile(r"^[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+$")

try:
    config.load_incluster_config()
except Exception:
    config.load_kube_config()

core = client.CoreV1Api()
networking = client.NetworkingV1Api()
jwks_client = jwt.PyJWKClient(KEYCLOAK_JWKS_URL)
app = FastAPI(title="Shopnoltd Android Cloud", version="2.0.0")


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


class PackageIn(BaseModel):
    package_name: str = Field(min_length=3, max_length=255)


def current_user(request: Request) -> str:
    value = request.headers.get("authorization", "")
    if not value.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing_bearer_token")
    token = value.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="missing_bearer_token")
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token).key
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "RS384", "RS512"],
            issuer=KEYCLOAK_ISSUER,
            audience=KEYCLOAK_AUDIENCE,
        )
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="invalid_bearer_token") from exc
    authorized_party = str(payload.get("azp", "")).strip()
    if authorized_party and authorized_party != KEYCLOAK_CLIENT_ID:
        raise HTTPException(status_code=401, detail="invalid_bearer_token")
    subject = str(payload.get("sub", "")).strip()
    if not subject:
        raise HTTPException(status_code=401, detail="token_has_no_subject")
    return subject


def name_for(prefix: str, session_id: str) -> str:
    return f"{prefix}-{session_id[:16].lower()}"


def make_emulator_pod(session: Session) -> client.V1Pod:
    container = client.V1Container(
        name="emulator",
        image=EMULATOR_IMAGE,
        image_pull_policy="IfNotPresent",
        ports=[
            client.V1ContainerPort(name="grpc", container_port=8554),
            client.V1ContainerPort(name="adb", container_port=5555),
        ],
        env=[client.V1EnvVar(name="EMULATOR_PARAMS", value="-no-window -no-audio -memory 2048 -grpc 8554")],
        resources=client.V1ResourceRequirements(
            requests={"cpu": "2", "memory": "3Gi", "ephemeral-storage": "4Gi"},
            limits={"cpu": "4", "memory": "4Gi", "ephemeral-storage": "8Gi"},
        ),
        volume_mounts=[client.V1VolumeMount(name="android-data", mount_path="/data")],
        security_context=client.V1SecurityContext(privileged=True, allow_privilege_escalation=True),
    )
    return client.V1Pod(
        metadata=client.V1ObjectMeta(
            name=session.emulator_name,
            namespace=NAMESPACE,
            labels={"app.kubernetes.io/name": "android-emulator", "shopnoltd.dev/session": session.session_id},
        ),
        spec=client.V1PodSpec(
            restart_policy="Never",
            automount_service_account_token=False,
            containers=[container],
            volumes=[client.V1Volume(name="android-data", empty_dir=client.V1EmptyDirVolumeSource(size_limit="6Gi"))],
        ),
    )


def make_gateway_pod(session: Session) -> client.V1Pod:
    container = client.V1Container(
        name="gateway",
        image=GATEWAY_IMAGE,
        image_pull_policy="IfNotPresent",
        env=[
            client.V1EnvVar(name="EMULATOR_HOST", value=f"{session.emulator_name}:8554"),
            client.V1EnvVar(name="SESSION_ID", value=session.session_id),
        ],
        ports=[client.V1ContainerPort(name="http", container_port=8080)],
        resources=client.V1ResourceRequirements(
            requests={"cpu": "100m", "memory": "128Mi"},
            limits={"cpu": "500m", "memory": "512Mi"},
        ),
        security_context=client.V1SecurityContext(
            run_as_non_root=True, run_as_user=10001, allow_privilege_escalation=False
        ),
    )
    return client.V1Pod(
        metadata=client.V1ObjectMeta(
            name=session.gateway_name,
            namespace=NAMESPACE,
            labels={"app.kubernetes.io/name": "android-cloud-gateway", "shopnoltd.dev/session": session.session_id},
        ),
        spec=client.V1PodSpec(
            restart_policy="Always",
            automount_service_account_token=False,
            containers=[container],
        ),
    )


def make_service(name: str, selector: dict[str, str], port: int, target: int) -> client.V1Service:
    return client.V1Service(
        metadata=client.V1ObjectMeta(name=name, namespace=NAMESPACE),
        spec=client.V1ServiceSpec(
            selector=selector,
            ports=[client.V1ServicePort(name="http", port=port, target_port=target)],
        ),
    )


def make_gateway_ingress(session: Session) -> client.V1Ingress:
    backend = client.V1IngressBackend(
        service=client.V1IngressServiceBackend(
            name=session.gateway_name, port=client.V1ServiceBackendPort(number=8080)
        )
    )
    path = client.V1HTTPIngressPath(
        path=f"/sessions/{session.session_id}(/|$)(.*)",
        path_type="ImplementationSpecific",
        backend=backend,
    )
    rule = client.V1IngressRule(
        host=PUBLIC_HOST,
        http=client.V1HTTPIngressRuleValue(paths=[path]),
    )
    return client.V1Ingress(
        metadata=client.V1ObjectMeta(
            name=session.gateway_name,
            namespace=NAMESPACE,
            annotations={
                "nginx.ingress.kubernetes.io/use-regex": "true",
                "nginx.ingress.kubernetes.io/rewrite-target": "/$2",
                "nginx.ingress.kubernetes.io/proxy-read-timeout": "3600",
                "nginx.ingress.kubernetes.io/proxy-send-timeout": "3600",
            },
        ),
        spec=client.V1IngressSpec(ingress_class_name="nginx", rules=[rule]),
    )


def create_resources(session: Session) -> None:
    try:
        core.create_namespaced_pod(NAMESPACE, make_emulator_pod(session))
        core.create_namespaced_service(
            NAMESPACE,
            make_service(
                session.emulator_name,
                {"app.kubernetes.io/name": "android-emulator", "shopnoltd.dev/session": session.session_id},
                8554,
                8554,
            ),
        )
        core.create_namespaced_pod(NAMESPACE, make_gateway_pod(session))
        core.create_namespaced_service(
            NAMESPACE,
            make_service(
                session.gateway_name,
                {"app.kubernetes.io/name": "android-cloud-gateway", "shopnoltd.dev/session": session.session_id},
                8080,
                8080,
            ),
        )
        networking.create_namespaced_ingress(NAMESPACE, make_gateway_ingress(session))
    except Exception:
        delete_resources(session)
        raise


def delete_resources(session: Session) -> None:
    for kind, name in (
        ("ingress", session.gateway_name),
        ("pod", session.gateway_name),
        ("service", session.gateway_name),
        ("service", session.emulator_name),
        ("pod", session.emulator_name),
    ):
        try:
            if kind == "pod":
                core.delete_namespaced_pod(name, NAMESPACE, grace_period_seconds=0)
            elif kind == "service":
                core.delete_namespaced_service(name, NAMESPACE)
            else:
                networking.delete_namespaced_ingress(name, NAMESPACE)
        except ApiException as exc:
            if exc.status != 404:
                raise


def cleanup_expired() -> None:
    now = time.time()
    for session_id, session in list(sessions.items()):
        if now - session.last_seen > SESSION_TTL_SECONDS:
            try:
                delete_resources(session)
            finally:
                sessions.pop(session_id, None)


def response_for(session: Session) -> dict[str, Any]:
    return {
        "session_id": session.session_id,
        "status": "starting",
        "gateway_url": f"{PUBLIC_GATEWAY_BASE}/{session.session_id}",
        "expires_at": int(session.created_at + SESSION_TTL_SECONDS),
        "turn": {
            "urls": TURN_URLS,
            "username": TURN_USERNAME,
            "credential": TURN_CREDENTIAL,
        }
        if TURN_URLS
        else None,
    }


def get_session_for_user(session_id: str, user_id: str) -> Session:
    session = sessions.get(session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="session_not_found")
    session.last_seen = time.time()
    return session


def exec_emulator(session: Session, command: list[str], stdin_bytes: bytes | None = None) -> str:
    exec_stream = stream(
        core.connect_get_namespaced_pod_exec,
        session.emulator_name,
        NAMESPACE,
        command=command,
        container="emulator",
        stderr=True,
        stdin=stdin_bytes is not None,
        stdout=True,
        tty=False,
        _preload_content=False,
        binary=True,
    )
    stdout = bytearray()
    stderr = bytearray()
    try:
        if stdin_bytes is not None:
            exec_stream.write_stdin(stdin_bytes)
        while exec_stream.is_open():
            exec_stream.update(timeout=2)
            if exec_stream.peek_stdout():
                chunk = exec_stream.read_stdout()
                if isinstance(chunk, str):
                    chunk = chunk.encode()
                stdout.extend(chunk)
            if exec_stream.peek_stderr():
                chunk = exec_stream.read_stderr()
                if isinstance(chunk, str):
                    chunk = chunk.encode()
                stderr.extend(chunk)
        if stderr:
            stdout.extend(b"\n" + stderr)
    finally:
        exec_stream.close()
    return stdout.decode("utf-8", errors="replace")


def run_adb(session: Session, shell_command: str) -> str:
    command = [
        "/bin/sh",
        "-c",
        "for i in $(seq 1 60); do adb -e get-state >/dev/null 2>&1 && break; sleep 1; done; "
        f"{shell_command}",
    ]
    return exec_emulator(session, command)


def adb_result(output: str) -> tuple[bool, str]:
    marker = "__SHOPNO_RC__"
    if marker not in output:
        return False, output.strip()
    body, rc = output.rsplit(marker, 1)
    rc = rc.strip().splitlines()[0] if rc.strip() else "1"
    return rc == "0", body.strip()


def install_apk_file(session: Session, source_file: Path, original_name: str) -> dict[str, Any]:
    if source_file.stat().st_size <= 0:
        raise HTTPException(status_code=400, detail="apk_file_empty")
    if source_file.stat().st_size > MAX_APK_BYTES:
        raise HTTPException(status_code=413, detail="apk_file_too_large")

    with source_file.open("rb") as handle:
        header = handle.read(4)
        if header != b"PK\x03\x04":
            raise HTTPException(status_code=400, detail="invalid_apk_file")

        apk_path = f"/data/shopnoltd-upload-{secrets.token_hex(12)}.apk"
        upload_command = ["/bin/sh", "-c", f"cat > {apk_path}"]
        try:
            exec_stream = stream(
                core.connect_get_namespaced_pod_exec,
                session.emulator_name,
                NAMESPACE,
                command=upload_command,
                container="emulator",
                stderr=True,
                stdin=True,
                stdout=True,
                tty=False,
                _preload_content=False,
                binary=True,
            )
            try:
                while exec_stream.is_open():
                    exec_stream.update(timeout=2)
                    chunk = handle.read(1024 * 1024)
                    if chunk:
                        exec_stream.write_stdin(chunk)
                    else:
                        break
                exec_stream.close()
            finally:
                if exec_stream.is_open():
                    exec_stream.close()

            digest = hashlib.sha256()
            with source_file.open("rb") as digest_file:
                for chunk in iter(lambda: digest_file.read(1024 * 1024), b""):
                    digest.update(chunk)

            raw = run_adb(
                session,
                f"adb -e install -r -t {apk_path} 2>&1; "
                f'rc=$?; rm -f {apk_path}; printf "\\n__SHOPNO_RC__%s\\n" "$rc"',
            )
            ok, detail = adb_result(raw)
            if not ok:
                raise HTTPException(status_code=400, detail=f"apk_install_failed:{detail[-1500:]}")
            return {
                "status": "installed",
                "filename": original_name,
                "size": source_file.stat().st_size,
                "sha256": digest.hexdigest(),
                "output": detail[-1500:],
            }
        finally:
            try:
                exec_emulator(session, ["/bin/sh", "-c", f"rm -f {apk_path}"])
            except Exception:
                pass


def download_official(app_id: str) -> tuple[Path, str]:
    item = OFFICIAL_APPS.get(app_id)
    if not item:
        raise HTTPException(status_code=404, detail="official_app_not_found")
    suffix = ".apk"
    fd, name = tempfile.mkstemp(prefix="shopnoltd-android-", suffix=suffix)
    os.close(fd)
    path = Path(name)
    try:
        request = urllib.request.Request(
            item["url"],
            headers={"User-Agent": "Shopnoltd-Android-Cloud/2"},
        )
        with urllib.request.urlopen(request, timeout=60) as response, path.open("wb") as output:
            total = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_APK_BYTES:
                    raise HTTPException(status_code=413, detail="official_apk_too_large")
                output.write(chunk)
        return path, item["name"]
    except HTTPException:
        path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=502, detail=f"official_apk_download_failed:{exc}") from exc


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "android-cloud-controller"}


@app.get("/readyz")
async def readyz() -> JSONResponse:
    try:
        core.list_namespaced_pod(NAMESPACE, limit=1)
    except Exception as exc:
        return JSONResponse({"status": "not_ready", "reason": str(exc)}, status_code=503)
    return JSONResponse({"status": "ready", "capacity": MAX_SESSIONS, "kvm_required": True})


@app.get("/api/v1/android-cloud/capabilities")
async def capabilities(user_id: str = Depends(current_user)) -> dict[str, Any]:
    return {
        "product": "shopnoltd_android_cloud",
        "user": user_id,
        "browser_control": True,
        "web_rtc": True,
        "apk_install": True,
        "apk_upload": True,
        "apk_max_bytes": MAX_APK_BYTES,
        "app_launch": True,
        "app_uninstall": True,
        "installed_apps": True,
        "mock_gps": True,
        "adb_public": False,
        "max_sessions": MAX_SESSIONS,
        "turn_configured": bool(TURN_URLS),
        "official_apps": list(OFFICIAL_APPS.values()),
    }


@app.get("/api/v1/android-cloud/sessions/{session_id}/apps")
async def list_apps(session_id: str, user_id: str = Depends(current_user)) -> dict[str, Any]:
    session = get_session_for_user(session_id, user_id)
    raw = run_adb(
        session,
        "adb -e shell pm list packages -3 | sed 's/^package://' | sort; "
        "printf '\\n__SHOPNO_RC__0\\n'",
    )
    ok, detail = adb_result(raw)
    if not ok:
        raise HTTPException(status_code=503, detail=f"android_package_list_failed:{detail[-1000:]}")
    packages = [line.strip() for line in detail.splitlines() if PACKAGE_RE.fullmatch(line.strip())]
    return {"session_id": session_id, "packages": packages}


@app.post("/api/v1/android-cloud/sessions/{session_id}/apps/official/{app_id}/install")
async def install_official_app(session_id: str, app_id: str, user_id: str = Depends(current_user)) -> dict[str, Any]:
    session = get_session_for_user(session_id, user_id)
    path, name = download_official(app_id)
    try:
        return install_apk_file(session, path, name)
    finally:
        path.unlink(missing_ok=True)


@app.post("/api/v1/android-cloud/sessions/{session_id}/apps/upload")
async def upload_apk(
    session_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(current_user),
) -> dict[str, Any]:
    session = get_session_for_user(session_id, user_id)
    filename = Path(file.filename or "uploaded.apk").name
    if not filename.lower().endswith(".apk"):
        raise HTTPException(status_code=400, detail="only_apk_files_are_allowed")
    fd, name = tempfile.mkstemp(prefix="shopnoltd-upload-", suffix=".apk")
    os.close(fd)
    path = Path(name)
    total = 0
    try:
        with path.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_APK_BYTES:
                    raise HTTPException(status_code=413, detail="apk_file_too_large")
                output.write(chunk)
        return install_apk_file(session, path, filename)
    finally:
        path.unlink(missing_ok=True)
        await file.close()


@app.post("/api/v1/android-cloud/sessions/{session_id}/apps/launch")
async def launch_app(body: PackageIn, session_id: str, user_id: str = Depends(current_user)) -> dict[str, Any]:
    session = get_session_for_user(session_id, user_id)
    if not PACKAGE_RE.fullmatch(body.package_name):
        raise HTTPException(status_code=400, detail="invalid_package_name")
    raw = run_adb(
        session,
        f'adb -e shell monkey -p {body.package_name} -c android.intent.category.LAUNCHER 1 2>&1; '
        'rc=$?; printf "\\n__SHOPNO_RC__%s\\n" "$rc"',
    )
    ok, detail = adb_result(raw)
    if not ok:
        raise HTTPException(status_code=400, detail=f"app_launch_failed:{detail[-1000:]}")
    return {"status": "launched", "package_name": body.package_name, "output": detail[-1000:]}


@app.post("/api/v1/android-cloud/sessions/{session_id}/apps/uninstall")
async def uninstall_app(body: PackageIn, session_id: str, user_id: str = Depends(current_user)) -> dict[str, Any]:
    session = get_session_for_user(session_id, user_id)
    if not PACKAGE_RE.fullmatch(body.package_name):
        raise HTTPException(status_code=400, detail="invalid_package_name")
    raw = run_adb(
        session,
        f'adb -e uninstall {body.package_name} 2>&1; '
        "rc=$?; printf '\\n__SHOPNO_RC__%s\\n' "$rc"",
    )
    ok, detail = adb_result(raw)
    if not ok:
        raise HTTPException(status_code=400, detail=f"app_uninstall_failed:{detail[-1000:]}")
    return {"status": "uninstalled", "package_name": body.package_name, "output": detail[-1000:]}


@app.post("/api/v1/android-cloud/sessions")
async def create_session(body: CreateSessionIn, user_id: str = Depends(current_user)) -> dict[str, Any]:
    del body
    cleanup_expired()
    existing = next((item for item in sessions.values() if item.user_id == user_id), None)
    if existing:
        existing.last_seen = time.time()
        return response_for(existing)
    if len(sessions) >= MAX_SESSIONS:
        raise HTTPException(status_code=429, detail="android_cloud_capacity_exhausted")
    session_id = secrets.token_urlsafe(24).replace("-", "").replace("_", "")
    session = Session(
        session_id=session_id,
        user_id=user_id,
        emulator_name=name_for("aemu", session_id),
        gateway_name=name_for("agw", session_id),
        created_at=time.time(),
        last_seen=time.time(),
    )
    try:
        create_resources(session)
    except ApiException as exc:
        raise HTTPException(status_code=503, detail=f"android_cloud_provision_failed:{exc.reason}") from exc
    sessions[session_id] = session
    return response_for(session)


@app.get("/api/v1/android-cloud/sessions/{session_id}")
async def get_session(session_id: str, user_id: str = Depends(current_user)) -> dict[str, Any]:
    session = get_session_for_user(session_id, user_id)
    return response_for(session)


@app.delete("/api/v1/android-cloud/sessions/{session_id}")
async def stop_session(session_id: str, user_id: str = Depends(current_user)) -> dict[str, str]:
    session = get_session_for_user(session_id, user_id)
    delete_resources(session)
    sessions.pop(session_id, None)
    return {"status": "stopped", "session_id": session_id}
