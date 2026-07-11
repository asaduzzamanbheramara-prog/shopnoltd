from fastapi import FastAPI

app=FastAPI()


@app.get("/health")
def health():
    return {
        "status":"ok",
        "service":"billing-engine"
    }


@app.post("/billing/checkout")
def checkout():

    return {
        "status":"created",
        "checkout":"demo"
    }


@app.get("/billing/status")
def status():

    return {
        "subscription":"active"
    }

