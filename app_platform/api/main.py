from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import datetime
import hashlib
import secrets

app = FastAPI(title="Shopnoltd API", description="Shopno Database Firm - Multi-tenant SaaS", version="3.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

tenants_db = {}
users_db = {}
domains_db = {}
active_tokens = {}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_token(user_id):
    token = secrets.token_hex(32)
    active_tokens[token] = user_id
    return token

@app.get("/")
def root():
    return {"brand": "Shopnoltd", "company": "Shopno Database Firm", "platform": "Multi-tenant SaaS", "status": "running", "version": "3.0.0", "timestamp": datetime.datetime.utcnow().isoformat()}

@app.get("/health")
def health():
    return {"status": "healthy", "service": "shopnoltd-api", "tenants": len(tenants_db), "users": len(users_db), "domains": len(domains_db)}

@app.get("/api/info")
def info():
    return {"tenant": "shopnoltd", "domain": "shopnoltd.dpdns.org", "features": ["Domain Management", "Billing System", "OAuth", "Multi-tenancy", "Live Chat", "Video Meetings", "Kobo Toolbox", "Mail Server", "Custom Branding"]}

@app.get("/api/tenants")
def list_tenants():
    return {"total": len(tenants_db), "active": 0, "tenants": list(tenants_db.values())}

@app.post("/api/tenants")
def create_tenant(name: str, domain: str, owner_email: str, plan: str = "basic"):
    tenant_id = "tenant_" + secrets.token_hex(4)
    tenants_db[tenant_id] = {"id": tenant_id, "name": name, "domain": domain, "plan": plan, "owner_email": owner_email, "status": "provisioning"}
    return tenants_db[tenant_id]

@app.get("/api/tenants/{tenant_id}")
def get_tenant(tenant_id: str):
    if tenant_id in tenants_db:
        return tenants_db[tenant_id]
    raise HTTPException(status_code=404, detail="Tenant not found")

@app.post("/api/users/register")
def register_user(username: str, email: str, password: str, full_name: Optional[str] = None, tenant_id: Optional[str] = None):
    for u in users_db.values():
        if u["username"] == username:
            raise HTTPException(status_code=400, detail="Username exists")
    user_id = "user_" + secrets.token_hex(4)
    users_db[user_id] = {"id": user_id, "username": username, "email": email, "full_name": full_name, "tenant_id": tenant_id or "default", "password_hash": hash_password(password)}
    token = create_token(user_id)
    safe_user = {k: v for k, v in users_db[user_id].items() if k != "password_hash"}
    safe_user["token"] = token
    return safe_user

@app.post("/api/users/login")
def login_user(username: str, password: str):
    if username == "admin" and password == "shopnoltd2026":
        token = create_token("user_admin")
        return {"status": "success", "token": token, "user": {"id": "user_admin", "username": "admin", "tenant_id": "default"}}
    for user_id, user in users_db.items():
        if user["username"] == username and user["password_hash"] == hash_password(password):
            token = create_token(user_id)
            return {"status": "success", "token": token, "user": {"id": user_id, "username": user["username"], "email": user["email"], "tenant_id": user["tenant_id"]}}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/api/users/me")
def get_me(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.replace("Bearer ", "")
    if token in active_tokens:
        user_id = active_tokens[token]
        if user_id in users_db:
            user = users_db[user_id]
            return {"id": user["id"], "username": user["username"], "email": user["email"], "tenant_id": user["tenant_id"]}
    raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/billing/checkout")
def checkout(tenant_id: str, plan: str, amount: float):
    return {"checkout_url": f"https://billing.shopnoltd.dpdns.org/checkout/{tenant_id}", "session_id": "sub_" + secrets.token_hex(6), "amount": amount, "plan": plan}

@app.get("/api/billing/plans")
def list_plans():
    return {"plans": [
        {"id": "basic", "name": "Basic", "price": 9.99},
        {"id": "pro", "name": "Pro", "price": 29.99},
        {"id": "enterprise", "name": "Enterprise", "price": 99.99}
    ]}

@app.post("/api/domains")
def add_domain(domain: str, tenant_id: str):
    domain_id = "domain_" + secrets.token_hex(4)
    domains_db[domain_id] = {"id": domain_id, "tenant_id": tenant_id, "domain": domain, "status": "pending"}
    return {**domains_db[domain_id], "dns_records": [{"type": "A", "name": "@", "value": "YOUR_IP"}, {"type": "CNAME", "name": "www", "value": "shopnoltd.dpdns.org"}]}

@app.get("/api/domains")
def list_domains(tenant_id: Optional[str] = None):
    filtered = [d for d in domains_db.values() if not tenant_id or d["tenant_id"] == tenant_id]
    return {"total": len(filtered), "domains": filtered}

@app.post("/api/meetings/create")
def create_meeting():
    meeting_id = "meet_" + datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return {"meeting_id": meeting_id, "join_url": f"https://meet.shopnoltd.dpdns.org/{meeting_id}"}

@app.get("/api/branding")
def get_branding():
    return {"company_name": "Shopno Database Firm", "brand_name": "Shopnoltd", "primary_color": "#2563eb", "secondary_color": "#1e40af", "domain": "shopnoltd.dpdns.org", "tagline": "Multi-tenant SaaS Platform"}

@app.get("/api/stats")
def get_stats():
    return {"tenants": len(tenants_db), "users": len(users_db), "domains": len(domains_db), "subscriptions": 0}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
