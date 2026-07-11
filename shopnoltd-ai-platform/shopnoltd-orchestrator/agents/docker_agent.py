"""
Build & push agent. Talks to the Docker daemon via docker-py.

NOTE: this requires access to a Docker socket (/var/run/docker.sock) or a
remote DOCKER_HOST. If the orchestrator itself runs inside Kubernetes
without a Docker daemon available, swap this module's build_image() for
a Kaniko Job instead (see README "Running builds inside the cluster").
"""
import os
import docker
from docker.errors import BuildError, APIError
import config


def _dockerfile_relative_to_context(dockerfile_rel: str, context_rel: str) -> str:
    """docker-py wants the Dockerfile path relative to the build context dir."""
    dockerfile_abs = config.REPO_ROOT / dockerfile_rel
    context_abs = config.REPO_ROOT / context_rel
    return os.path.relpath(dockerfile_abs, context_abs)


def _client() -> docker.DockerClient:
    return docker.from_env()


def login() -> None:
    if not (config.GHCR_USERNAME and config.GHCR_TOKEN):
        raise RuntimeError(
            "GHCR_USERNAME / GHCR_TOKEN not set — cannot push images. "
            "Set them as env vars (a PAT with write:packages scope)."
        )
    client = _client()
    client.login(
        username=config.GHCR_USERNAME,
        password=config.GHCR_TOKEN,
        registry=config.GHCR_REGISTRY,
    )


def build_image(dockerfile_rel: str, context_rel: str, tag: str) -> tuple[bool, str]:
    """Build an image. Returns (success, log_or_error)."""
    client = _client()
    context_path = str(config.REPO_ROOT / context_rel)
    dockerfile_name = _dockerfile_relative_to_context(dockerfile_rel, context_rel)
    log_lines = []
    try:
        _, build_logs = client.images.build(
            path=context_path,
            dockerfile=dockerfile_name,
            tag=tag,
            rm=True,
        )
        for chunk in build_logs:
            if "stream" in chunk:
                log_lines.append(chunk["stream"].strip())
        return True, "\n".join(l for l in log_lines if l)
    except BuildError as e:
        for chunk in e.build_log:
            if "stream" in chunk:
                log_lines.append(chunk["stream"].strip())
        return False, f"BuildError: {e}\n" + "\n".join(log_lines)
    except APIError as e:
        return False, f"Docker API error: {e}"


def push_image(tag: str) -> tuple[bool, str]:
    client = _client()
    try:
        result = client.images.push(tag, stream=True, decode=True)
        errors = []
        for chunk in result:
            if "error" in chunk:
                errors.append(chunk["error"])
        if errors:
            return False, "\n".join(errors)
        return True, "pushed"
    except APIError as e:
        return False, f"Push failed: {e}"
