from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(
    title="Shopnoltd API",
    description="Shopno Database Firm - Multi-tenant SaaS Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "brand": "Shopnoltd",
        "company": "Shopno Database Firm",
        "platform": "Multi-tenant SaaS",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
def health():
    return {"status": "healthy", "service": "shopnoltd-api"}

@app.get("/api/info")
def info():
    return {
        "tenant": "shopnoltd",
        "domain": "shopnoltd.dpdns.org",
        "features": [
            "Domain Management",
            "Billing System",
            "OAuth Authentication",
            "Multi-tenancy",
            "Live Chat",
            "Video Meetings",
            "Kobo Toolbox",
            "Mail Server",
            "Custom Branding"
        ]
    }

@app.get("/api/tenants")
def tenants():
    return {
        "total": 0,
        "active": 0,
        "platform": "shopnoltd"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
