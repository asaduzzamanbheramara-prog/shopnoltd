from fastapi import FastAPI
from fastapi.responses import RedirectResponse
import os

app = FastAPI(
    title="Shopnoltd Remote Device Gateway",
    version="2.0.0",
)

MESH_URL = os.getenv(
    "MESH_URL",
    "https://remote-engine.shopnoltd.dpdns.org",
).rstrip("/")


@app.get("/")
def root():
    return RedirectResponse(
        url=f"{MESH_URL}/",
        status_code=307,
    )


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "service": "remote-device-gateway",
        "engine": "meshcentral",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "remote-device-gateway",
        "engine": "meshcentral",
    }


@app.get("/api/healthz")
def api_healthz():
    return {
        "status": "ok",
        "service": "remote-device-gateway",
        "engine": "meshcentral",
    }


@app.get("/api/connect/{device_id}")
def connect(device_id: str):
    return {
        "device_id": device_id,
        "engine": "meshcentral",
        "connect_url": f"{MESH_URL}/",
    }


@app.get("/connect/{device_id}")
def browser_connect(device_id: str):
    return RedirectResponse(
        url=f"{MESH_URL}/",
        status_code=307,
    )
