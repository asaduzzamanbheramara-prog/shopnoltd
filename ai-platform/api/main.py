from fastapi import FastAPI

api = FastAPI(title="Shopnoltd AI API")


@api.get("/health")
def health():
    return {"status": "ok"}
