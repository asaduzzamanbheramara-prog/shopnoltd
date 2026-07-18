from fastapi import FastAPI

app = FastAPI(title="Shopnoltd AI Platform", version="1.0.0")


@app.get("/")
def home():
    return {"status": "running", "platform": "Shopnoltd AI", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
