#!/usr/bin/env python3

"""
Shopnoltd-PC-1 outbound-only executor.

Security model:
- no inbound listener
- no arbitrary shell endpoint
- fixed operation allowlist
- one job at a time
- bounded execution time
- HTTPS gateway communication
- HMAC authenticated requests
- timestamp + nonce replay protection
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import platform
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


CONFIG_PATH = Path(
    os.getenv(
        "SHOPNOLTD_EXECUTOR_CONFIG",
        r"C:\ProgramData\Shopnoltd\executor.json",
    )
)

DEFAULT_GATEWAY = "https://remote.shopnoltd.dpdns.org"

POLL_SECONDS = 5
HEARTBEAT_SECONDS = 30
HTTP_TIMEOUT = 30
COMMAND_TIMEOUT = 60


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise RuntimeError(f"Missing executor configuration: {CONFIG_PATH}")

    value = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    required = ("gateway_url", "device_id")

    for key in required:
        if not value.get(key):
            raise RuntimeError(f"Missing configuration field: {key}")

    # Initial provisioning may contain only an enrollment token.
    # Normal runtime requires the enrolled agent_id + secret.
    has_enrollment = bool(value.get("enrollment_token"))
    has_runtime_credentials = bool(
        value.get("agent_id") and value.get("secret")
    )

    if not has_enrollment and not has_runtime_credentials:
        raise RuntimeError(
            "Configuration must contain either enrollment_token "
            "for initial provisioning or agent_id + secret "
            "for normal runtime"
        )

    return value


def canonical_json(value) -> str:
    return json.dumps(
        value,
        separators=(",", ":"),
        sort_keys=True,
    )


def sign(secret: str, timestamp: str, nonce: str, method: str, path: str, body: str) -> str:
    message = "\n".join(
        [
            timestamp,
            nonce,
            method.upper(),
            path,
            body,
        ]
    ).encode()

    raw_secret = base64.b64decode(secret)

    # Must exactly match the registry-side derivation.
    auth_key = hashlib.sha256(
        b"shopnoltd-executor-hmac-v1:" + raw_secret
    ).digest()

    return hmac.new(
        auth_key,
        message,
        hashlib.sha256,
    ).hexdigest()


def request(
    config: dict,
    method: str,
    path: str,
    payload=None,
    signed_path: str | None = None,
):
    gateway = config["gateway_url"].rstrip("/")
    body = canonical_json(payload) if payload is not None else ""

    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex

    signature_path = signed_path or path

    signature = sign(
        config["secret"],
        timestamp,
        nonce,
        method,
        signature_path,
        body,
    )

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Shopnoltd-Device": config["device_id"],
        "X-Shopnoltd-Agent": config["agent_id"],
        "X-Shopnoltd-Timestamp": timestamp,
        "X-Shopnoltd-Nonce": nonce,
        "X-Shopnoltd-Signature": signature,
        "User-Agent": "Shopnoltd-PC-Executor/1.0",
    }

    req = Request(
        gateway + path,
        data=body.encode() if body else None,
        headers=headers,
        method=method.upper(),
    )

    with urlopen(req, timeout=HTTP_TIMEOUT) as response:
        raw = response.read().decode("utf-8")

    return json.loads(raw) if raw else {}


def run(command: list[str], timeout: int = COMMAND_TIMEOUT) -> dict:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            check=False,
        )

        return {
            "returncode": result.returncode,
            "stdout": result.stdout[-20000:],
            "stderr": result.stderr[-10000:],
        }

    except subprocess.TimeoutExpired:
        return {
            "returncode": 124,
            "stdout": "",
            "stderr": "command timed out",
        }

    except Exception as exc:
        return {
            "returncode": 1,
            "stdout": "",
            "stderr": str(exc),
        }


def operation_system_info():
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "time": time.time(),
    }


def operation_windows_info():
    return run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            (
                "$ErrorActionPreference='Stop'; "
                "$o=[ordered]@{"
                "ComputerName=$env:COMPUTERNAME;"
                "OS=(Get-CimInstance Win32_OperatingSystem).Caption;"
                "Version=(Get-CimInstance Win32_OperatingSystem).Version;"
                "Architecture=(Get-CimInstance Win32_OperatingSystem).OSArchitecture"
                "}; "
                "$o | ConvertTo-Json -Compress"
            ),
        ]
    )


def operation_wsl_info():
    return run(
        [
            "wsl.exe",
            "--status",
        ]
    )


def operation_k3s_info():
    return run(
        [
            "wsl.exe",
            "-e",
            "bash",
            "-lc",
            (
                "export KUBECONFIG=/home/shopno/k3s.yaml; "
                "kubectl get nodes -o wide"
            ),
        ]
    )


def operation_k8s_pods():
    return run(
        [
            "wsl.exe",
            "-e",
            "bash",
            "-lc",
            (
                "export KUBECONFIG=/home/shopno/k3s.yaml; "
                "kubectl get pods -A -o wide"
            ),
        ],
        timeout=90,
    )


def operation_k8s_services():
    return run(
        [
            "wsl.exe",
            "-e",
            "bash",
            "-lc",
            (
                "export KUBECONFIG=/home/shopno/k3s.yaml; "
                "kubectl get svc -A -o wide"
            ),
        ],
        timeout=90,
    )


def operation_git_status():
    return run(
        [
            "wsl.exe",
            "-e",
            "bash",
            "-lc",
            (
                "cd /mnt/c/Users/asadu/PROJECTS/shopnoltd && "
                "git status --short --branch"
            ),
        ]
    )


def operation_shopnoltd_health():
    return run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            (
                "$ErrorActionPreference='Stop'; "
                "$urls=@("
                "'https://api.shopnoltd.dpdns.org/healthz',"
                "'https://api.shopnoltd.dpdns.org/readyz',"
                "'https://remote.shopnoltd.dpdns.org/healthz'"
                "); "
                "$urls | ForEach-Object { "
                "$r=Invoke-WebRequest -UseBasicParsing -Uri $_ -TimeoutSec 15; "
                "$_.ToString() + ' ' + $r.StatusCode + ' ' + $r.Content "
                "}"
            ),
        ],
        timeout=60,
    )


def operation_disk_status():
    return run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            (
                "Get-PSDrive -PSProvider FileSystem | "
                "Select-Object Name,Used,Free | "
                "ConvertTo-Json -Compress"
            ),
        ]
    )


def operation_memory_status():
    return run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            (
                "$o=[ordered]@{"
                "TotalPhysicalMemory=(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory;"
                "FreePhysicalMemory=(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"
                "}; "
                "$o | ConvertTo-Json -Compress"
            ),
        ]
    )


def operation_remote_device_status():
    return run(
        [
            "wsl.exe",
            "-e",
            "bash",
            "-lc",
            (
                "export KUBECONFIG=/home/shopno/k3s.yaml; "
                "kubectl -n shopno-tools get pods,svc -l app=remote-device-gateway -o wide; "
                "kubectl -n shopno-tools get pods,svc -l app=remote-device-registry -o wide; "
                "kubectl -n shopno-tools get pods,svc -l app=remote-device-ui -o wide"
            ),
        ],
        timeout=90,
    )


OPERATIONS = {
    "system.info": operation_system_info,
    "windows.info": operation_windows_info,
    "wsl.info": operation_wsl_info,
    "k3s.info": operation_k3s_info,
    "k8s.pods": operation_k8s_pods,
    "k8s.services": operation_k8s_services,
    "git.status": operation_git_status,
    "shopnoltd.health": operation_shopnoltd_health,
    "disk.status": operation_disk_status,
    "memory.status": operation_memory_status,
    "remote-device.status": operation_remote_device_status,
}


def execute(job: dict) -> dict:
    operation = job.get("operation")

    if operation not in OPERATIONS:
        return {
            "ok": False,
            "error": f"operation_not_allowed: {operation}",
        }

    started = time.time()

    try:
        result = OPERATIONS[operation]()

        if isinstance(result, dict):
            payload = result
        else:
            payload = {"result": result}

        return {
            "ok": True,
            "operation": operation,
            "duration_seconds": round(time.time() - started, 3),
            "result": payload,
        }

    except Exception as exc:
        return {
            "ok": False,
            "operation": operation,
            "error": str(exc),
            "duration_seconds": round(time.time() - started, 3),
        }


def enroll(config: dict):
    """
    One-time bootstrap enrollment.

    Enrollment is intentionally NOT HMAC signed because the executor
    does not possess its runtime secret yet. The one-time enrollment
    token is the bootstrap credential.

    The returned secret must be persisted securely by the installer
    or provisioning process.
    """
    gateway = config["gateway_url"].rstrip("/")
    path = f"/api/executor/enroll/{config['device_id']}"

    payload = {
        "enrollment_token": config["enrollment_token"],
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "agent_version": "1.0",
    }

    body = canonical_json(payload).encode()

    req = Request(
        gateway + path,
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Shopnoltd-PC-Executor/1.0",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=HTTP_TIMEOUT) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"executor enrollment HTTP {exc.code}: {detail}"
        ) from exc
    except URLError as exc:
        raise RuntimeError(
            f"executor enrollment connection failed: {exc}"
        ) from exc

    return json.loads(raw) if raw else {}


def heartbeat(config: dict):
    return request(
        config,
        "POST",
        f"/api/executor/heartbeat/{config['device_id']}",
        {
            "agent_id": config["agent_id"],
            "version": "1.0",
            "platform": platform.system(),
            "hostname": socket.gethostname(),
        },
    )


def poll(config: dict):
    return request(
        config,
        "GET",
        f"/api/executor/jobs/{config['device_id']}",
    )


def submit_result(config: dict, job_id: str, result: dict):
    return request(
        config,
        "POST",
        f"/api/executor/jobs/{job_id}/result",
        result,
    )


def main():
    config = load_config()

    # Initial provisioning only.
    #
    # If an enrollment token exists and the agent does not yet have
    # an agent_id/secret, enrollment can be performed by the
    # provisioning process. The normal runtime never sends the
    # bootstrap token.
    if config.get("enrollment_token") and (
        not config.get("agent_id")
        or not config.get("secret")
    ):
        response = enroll(config)

        if not response.get("ok"):
            raise RuntimeError(
                f"executor enrollment failed: {response}"
            )

        raise RuntimeError(
            "Enrollment succeeded. Persist returned agent_id and "
            "secret securely, remove enrollment_token, then restart."
        )

    last_heartbeat = 0.0

    while True:
        try:
            now = time.time()

            if now - last_heartbeat >= HEARTBEAT_SECONDS:
                heartbeat(config)
                last_heartbeat = now

            response = poll(config)

            jobs = response.get("jobs", [])

            if jobs:
                job = jobs[0]
                job_id = job.get("id")

                if not job_id:
                    time.sleep(POLL_SECONDS)
                    continue

                result = execute(job)
                submit_result(config, job_id, result)

            time.sleep(POLL_SECONDS)

        except KeyboardInterrupt:
            return

        except (HTTPError, URLError, TimeoutError, OSError, RuntimeError) as exc:
            print(f"executor communication error: {exc}", file=sys.stderr)
            time.sleep(min(POLL_SECONDS * 4, 30))

        except Exception as exc:
            print(f"executor error: {exc}", file=sys.stderr)
            time.sleep(10)


if __name__ == "__main__":
    main()
