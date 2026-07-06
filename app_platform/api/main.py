from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import secrets
import hashlib
import json

app = FastAPI(title="Shopnoltd Complete Platform", description="Multi-currency payment platform with exchange", version="5.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ==================== DATABASES ====================
wallets_db = {}
transactions_db = {}
users_db = {}
payment_methods_db = {}
audit_log_db = []
exchange_orders_db = {}

# ==================== EXCHANGE RATES (Updated) ====================
EXCHANGE_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "BDT": 109.5,
    "INR": 83.2,
    "JPY": 149.5,
    "CNY": 7.24,
    "AUD": 1.52,
    "CAD": 1.37,
    "SGD": 1.34,
    "MYR": 4.72,
    "PKR": 278.5,
    "LKR": 308.0,
    "NPR": 133.0,
    "AED": 3.67,
    "SAR": 3.75
}

CURRENCY_INFO = {
    "USD": {"name": "US Dollar", "symbol": "$", "flag": "🇺🇸"},
    "EUR": {"name": "Euro", "symbol": "€", "flag": "🇪🇺"},
    "GBP": {"name": "British Pound", "symbol": "£", "flag": "🇬🇧"},
    "BDT": {"name": "Bangladeshi Taka", "symbol": "৳", "flag": "🇧🇩"},
    "INR": {"name": "Indian Rupee", "symbol": "₹", "flag": "🇮🇳"},
    "JPY": {"name": "Japanese Yen", "symbol": "¥", "flag": "🇯🇵"},
    "CNY": {"name": "Chinese Yuan", "symbol": "¥", "flag": "🇨🇳"},
    "AUD": {"name": "Australian Dollar", "symbol": "A$", "flag": "🇦🇺"},
    "CAD": {"name": "Canadian Dollar", "symbol": "C$", "flag": "🇨🇦"},
    "SGD": {"name": "Singapore Dollar", "symbol": "S$", "flag": "🇸🇬"}
}

# ==================== HELPER FUNCTIONS ====================
def new_id(prefix):
    return f"{prefix}_{secrets.token_hex(8)}"

def log_action(action, user_id, details):
    audit_log_db.append({
        "id": new_id("log"),
        "action": action,
        "user_id": user_id,
        "details": details,
        "timestamp": datetime.utcnow().isoformat()
    })

def convert_currency(amount, from_curr, to_curr):
    """Convert amount from one currency to another"""
    if from_curr == to_curr:
        return amount, 1.0
    if from_curr not in EXCHANGE_RATES or to_curr not in EXCHANGE_RATES:
        raise HTTPException(400, f"Unsupported currency: {from_curr} or {to_curr}")
    
    # Convert via USD (base currency)
    usd_amount = amount / EXCHANGE_RATES[from_curr]
    converted = usd_amount * EXCHANGE_RATES[to_curr]
    rate = EXCHANGE_RATES[to_curr] / EXCHANGE_RATES[from_curr]
    return round(converted, 2), round(rate, 6)

# ==================== ROOT ENDPOINTS ====================
@app.get("/")
def root():
    return {
        "brand": "Shopnoltd",
        "company": "Shopno Database Firm",
        "platform": "Complete Multi-Currency Payment Platform",
        "version": "5.0.0",
        "status": "running",
        "features": ["Wallets", "Transfers", "Currency Exchange", "Multi-currency", "KYC", "Fraud Detection", "Payment Gateways"],
        "supported_currencies": list(EXCHANGE_RATES.keys()),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "shopnoltd-platform",
        "wallets": len(wallets_db),
        "transactions": len(transactions_db),
        "users": len(users_db),
        "exchange_orders": len(exchange_orders_db),
        "audit_logs": len(audit_log_db)
    }

# ==================== STATS (must come first) ====================
@app.get("/api/stats")
def get_stats():
    total_usd = sum(w["balance"] / EXCHANGE_RATES.get(w["currency"], 1.0) for w in wallets_db.values())
    return {
        "wallets": len(wallets_db),
        "transactions": len(transactions_db),
        "users": len(users_db),
        "exchange_orders": len(exchange_orders_db),
        "total_money_usd": round(total_usd, 2),
        "audit_logs": len(audit_log_db),
        "currencies_supported": len(EXCHANGE_RATES),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/audit-log")
def get_audit_log(limit: int = 100, user_id: str = None):
    logs = audit_log_db
    if user_id:
        logs = [l for l in logs if l["user_id"] == user_id]
    logs = sorted(logs, key=lambda x: x["timestamp"], reverse=True)[:limit]
    return {"total": len(logs), "logs": logs}

# ==================== CURRENCY EXCHANGE SYSTEM ====================
@app.get("/api/exchange/rates")
def get_exchange_rates():
    """Get all current exchange rates"""
    rates = []
    for curr, rate in EXCHANGE_RATES.items():
        info = CURRENCY_INFO.get(curr, {})
        rates.append({
            "currency": curr,
            "name": info.get("name", curr),
            "symbol": info.get("symbol", ""),
            "flag": info.get("flag", ""),
            "rate_to_usd": 1.0 / rate,  # How many of this = 1 USD
            "rate_from_usd": rate,  # How many USD = 1 of this
            "updated_at": datetime.utcnow().isoformat()
        })
    return {
        "base": "USD",
        "rates": rates,
        "total_currencies": len(rates),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/exchange/rate/{from_curr}/{to_curr}")
def get_specific_rate(from_curr: str, to_curr: str):
    """Get exchange rate between two currencies"""
    converted, rate = convert_currency(1.0, from_curr, to_curr)
    return {
        "from": from_curr,
        "to": to_curr,
        "rate": rate,
        "inverse_rate": round(1.0 / rate, 6) if rate else 0,
        "example_100": convert_currency(100, from_curr, to_curr)[0],
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/exchange/convert")
def convert(amount: float, from_currency: str, to_currency: str):
    """Convert amount between currencies"""
    converted, rate = convert_currency(amount, from_currency, to_currency)
    return {
        "from": {"currency": from_currency, "amount": amount},
        "to": {"currency": to_currency, "amount": converted},
        "exchange_rate": rate,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/exchange/order")
def create_exchange_order(from_currency: str, to_currency: str, amount: float, wallet_id: str):
    """Create a currency exchange order"""
    if wallet_id not in wallets_db:
        raise HTTPException(404, "Wallet not found")
    
    w = wallets_db[wallet_id]
    if w["currency"] != from_currency:
        raise HTTPException(400, f"Wallet is in {w['currency']}, not {from_currency}")
    
    if w["available_balance"] < amount:
        raise HTTPException(400, "Insufficient funds")
    
    converted, rate = convert_currency(amount, from_currency, to_currency)
    fee = converted * 0.005  # 0.5% exchange fee
    net = round(converted - fee, 2)
    
    # Deduct from source wallet
    w["balance"] -= amount
    w["available_balance"] -= amount
    
    # Create destination wallet or use existing
    target_wallet_id = None
    for wid, wdata in wallets_db.items():
        if wdata["owner_id"] == w["owner_id"] and wdata["currency"] == to_currency:
            target_wallet_id = wid
            wdata["balance"] += net
            wdata["available_balance"] += net
            break
    
    if not target_wallet_id:
        target_wallet_id = new_id("wal")
        wallets_db[target_wallet_id] = {
            "wallet_id": target_wallet_id,
            "owner_id": w["owner_id"],
            "owner_type": w["owner_type"],
            "currency": to_currency,
            "balance": net,
            "available_balance": net,
            "pending_balance": 0,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
    
    order_id = new_id("ex")
    exchange_orders_db[order_id] = {
        "order_id": order_id,
        "wallet_id": wallet_id,
        "target_wallet_id": target_wallet_id,
        "from_currency": from_currency,
        "to_currency": to_currency,
        "from_amount": amount,
        "to_amount": net,
        "exchange_rate": rate,
        "fee": round(fee, 2),
        "status": "completed",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    log_action("exchange", w["owner_id"], {"order_id": order_id, "from": from_currency, "to": to_currency, "amount": amount})
    
    return exchange_orders_db[order_id]

@app.get("/api/exchange/orders/{wallet_id}")
def get_exchange_orders(wallet_id: str):
    """Get exchange order history"""
    orders = [o for o in exchange_orders_db.values() if o["wallet_id"] == wallet_id]
    return {"wallet_id": wallet_id, "total": len(orders), "orders": orders}

@app.get("/api/exchange/popular")
def popular_exchanges():
    """Get popular currency exchange pairs"""
    popular = [
        {"from": "USD", "to": "BDT", "reason": "Most remittance"},
        {"from": "USD", "to": "EUR", "reason": "Business"},
        {"from": "BDT", "to": "USD", "reason": "Freelancers"},
        {"from": "USD", "to": "INR", "reason": "IT services"},
        {"from": "EUR", "to": "USD", "reason": "Tourism"}
    ]
    result = []
    for p in popular:
        try:
            _, rate = convert_currency(1.0, p["from"], p["to"])
            result.append({**p, "current_rate": rate})
        except:
            pass
    return {"popular_pairs": result}

# ==================== WALLET SYSTEM ====================
@app.post("/api/wallet/create")
def create_wallet(owner_id: str, currency: str = "USD", initial_balance: float = 0):
    wallet_id = new_id("wal")
    wallets_db[wallet_id] = {
        "wallet_id": wallet_id,
        "owner_id": owner_id,
        "owner_type": "user",
        "currency": currency,
        "balance": initial_balance,
        "available_balance": initial_balance,
        "pending_balance": 0,
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    log_action("wallet_created", owner_id, {"wallet_id": wallet_id, "currency": currency})
    return wallets_db[wallet_id]

@app.post("/api/wallet/add-funds")
def add_funds(wallet_id: str, amount: float, source: str = "bank_transfer"):
    if wallet_id not in wallets_db:
        raise HTTPException(404, "Wallet not found")
    w = wallets_db[wallet_id]
    w["balance"] += amount
    w["available_balance"] += amount
    tx_id = new_id("tx")
    transactions_db[tx_id] = {
        "transaction_id": tx_id,
        "type": "credit",
        "wallet_id": wallet_id,
        "amount": amount,
        "currency": w["currency"],
        "source": source,
        "timestamp": datetime.utcnow().isoformat()
    }
    log_action("funds_added", w["owner_id"], {"wallet_id": wallet_id, "amount": amount})
    return {"transaction_id": tx_id, "new_balance": w["balance"], "amount_added": amount}

@app.post("/api/wallet/subtract-funds")
def subtract_funds(wallet_id: str, amount: float, destination: str = "withdrawal"):
    if wallet_id not in wallets_db:
        raise HTTPException(404, "Wallet not found")
    w = wallets_db[wallet_id]
    if w["available_balance"] < amount:
        raise HTTPException(400, "Insufficient funds")
    w["balance"] -= amount
    w["available_balance"] -= amount
    tx_id = new_id("tx")
    transactions_db[tx_id] = {
        "transaction_id": tx_id,
        "type": "debit",
        "wallet_id": wallet_id,
        "amount": amount,
        "currency": w["currency"],
        "destination": destination,
        "timestamp": datetime.utcnow().isoformat()
    }
    return {"transaction_id": tx_id, "new_balance": w["balance"]}

@app.get("/api/wallet/{wallet_id}")
def get_wallet(wallet_id: str):
    if wallet_id not in wallets_db:
        raise HTTPException(404, "Wallet not found")
    return wallets_db[wallet_id]

@app.get("/api/wallet/{wallet_id}/balance")
def get_balance(wallet_id: str):
    if wallet_id not in wallets_db:
        raise HTTPException(404, "Wallet not found")
    w = wallets_db[wallet_id]
    # Also show USD equivalent
    usd_equiv = round(w["balance"] / EXCHANGE_RATES.get(w["currency"], 1.0), 2)
    return {
        "wallet_id": wallet_id,
        "currency": w["currency"],
        "balance": w["balance"],
        "available": w["available_balance"],
        "pending": w["pending_balance"],
        "balance_usd": usd_equiv,
        "as_of": datetime.utcnow().isoformat()
    }

# ==================== TRANSFERS ====================
@app.post("/api/transfer")
def transfer_funds(from_wallet: str, to_wallet: str, amount: float, description: str = "Transfer"):
    if from_wallet not in wallets_db:
        raise HTTPException(404, "Source wallet not found")
    if to_wallet not in wallets_db:
        raise HTTPException(404, "Destination wallet not found")
    
    from_w = wallets_db[from_wallet]
    to_w = wallets_db[to_wallet]
    
    if from_w["available_balance"] < amount:
        raise HTTPException(400, "Insufficient funds")
    
    # Auto currency conversion
    converted, rate = convert_currency(amount, from_w["currency"], to_w["currency"])
    
    from_w["balance"] -= amount
    from_w["available_balance"] -= amount
    to_w["balance"] += converted
    to_w["available_balance"] += converted
    
    tx_id = new_id("tx")
    transactions_db[tx_id] = {
        "transaction_id": tx_id,
        "type": "transfer",
        "from_wallet": from_wallet,
        "to_wallet": to_wallet,
        "amount": amount,
        "converted_amount": converted if from_w["currency"] != to_w["currency"] else None,
        "from_currency": from_w["currency"],
        "to_currency": to_w["currency"],
        "exchange_rate": rate if from_w["currency"] != to_w["currency"] else None,
        "description": description,
        "timestamp": datetime.utcnow().isoformat()
    }
    log_action("transfer", from_w["owner_id"], {"from": from_wallet, "to": to_wallet, "amount": amount})
    return {
        "transaction_id": tx_id,
        "amount": amount,
        "converted_amount": converted if from_w["currency"] != to_w["currency"] else None,
        "exchange_rate": rate if from_w["currency"] != to_w["currency"] else None,
        "status": "completed"
    }

@app.get("/api/transactions/{wallet_id}")
def get_transactions(wallet_id: str, limit: int = 50):
    if wallet_id not in wallets_db:
        raise HTTPException(404, "Wallet not found")
    txs = [tx for tx in transactions_db.values() if tx.get("wallet_id") == wallet_id or tx.get("from_wallet") == wallet_id or tx.get("to_wallet") == wallet_id]
    txs.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"wallet_id": wallet_id, "total": len(txs[:limit]), "transactions": txs[:limit]}

# ==================== GATEWAY ROUTING ====================
@app.post("/api/gateway/route-payment")
def route_payment(amount: float, currency: str, country: str, method_type: str):
    gateways = [
        {"name": "stripe", "fee": 2.9, "success_rate": 0.98, "supported_methods": ["card"], "supported_currencies": ["USD", "EUR", "GBP", "AUD", "CAD", "SGD"]},
        {"name": "bkash", "fee": 1.5, "success_rate": 0.95, "supported_methods": ["mobile_money"], "supported_currencies": ["BDT"]},
        {"name": "paypal", "fee": 3.5, "success_rate": 0.97, "supported_methods": ["card"], "supported_currencies": ["USD", "EUR", "GBP", "AUD", "CAD"]},
        {"name": "razorpay", "fee": 2.0, "success_rate": 0.96, "supported_methods": ["card"], "supported_currencies": ["INR", "USD"]},
        {"name": "sslcommerz", "fee": 2.5, "success_rate": 0.94, "supported_methods": ["card"], "supported_currencies": ["BDT"]},
        {"name": "alipay", "fee": 1.2, "success_rate": 0.97, "supported_methods": ["mobile_money"], "supported_currencies": ["CNY"]}
    ]
    
    best_gateway = None
    best_score = -1
    
    for gw in gateways:
        if method_type in gw["supported_methods"] and currency in gw["supported_currencies"]:
            score = gw["success_rate"] * 100 - gw["fee"]
            if score > best_score:
                best_score = score
                best_gateway = gw
    
    if not best_gateway:
        return {"error": "No gateway found", "amount": amount}
    
    fee = (amount * best_gateway["fee"]) / 100
    return {
        "gateway": best_gateway["name"],
        "fee_percent": best_gateway["fee"],
        "fee_amount": round(fee, 2),
        "net_amount": round(amount - fee, 2),
        "success_rate": best_gateway["success_rate"],
        "currency": currency,
        "method": method_type,
        "country": country
    }

# ==================== KYC / AML ====================
@app.post("/api/kyc/submit")
def submit_kyc(user_id: str, full_name: str, document_type: str, document_number: str, country: str = "US"):
    kyc_id = new_id("kyc")
    users_db[user_id] = {
        "user_id": user_id,
        "full_name": full_name,
        "kyc_status": "pending",
        "kyc_id": kyc_id,
        "document_type": document_type,
        "country": country,
        "submitted_at": datetime.utcnow().isoformat()
    }
    log_action("kyc_submitted", user_id, {"kyc_id": kyc_id})
    return {"kyc_id": kyc_id, "user_id": user_id, "status": "pending"}

@app.post("/api/kyc/approve")
def approve_kyc(user_id: str, reviewer: str = "system"):
    if user_id not in users_db:
        users_db[user_id] = {"user_id": user_id}
    users_db[user_id]["kyc_status"] = "approved"
    return {"user_id": user_id, "kyc_status": "approved"}

# ==================== FRAUD DETECTION ====================
@app.post("/api/fraud/check")
def check_fraud(transaction_id: str, amount: float, user_id: str, country: str = "US"):
    risk_score = 0
    flags = []
    if amount > 10000:
        risk_score += 30
        flags.append("large_amount")
    if country in ["XX", "ZZ"]:
        risk_score += 50
        flags.append("high_risk_country")
    risk_level = "low" if risk_score < 30 else "medium" if risk_score < 60 else "high"
    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "flags": flags,
        "recommendation": "approve" if risk_level == "low" else "review" if risk_level == "medium" else "block"
    }

# ==================== BILLING ====================
PLANS = [
    {"id":"starter","name":"Starter","price":9.99,"currency":"USD","features":["5 Users","10GB Storage"],"trial_days":14},
    {"id":"pro","name":"Professional","price":29.99,"currency":"USD","features":["25 Users","100GB Storage","Custom Branding"],"trial_days":14,"popular":True},
    {"id":"enterprise","name":"Enterprise","price":99.99,"currency":"USD","features":["Unlimited Users","1TB Storage","SLA"],"trial_days":30}
]

@app.get("/api/billing/plans")
def get_plans():
    return {"plans": PLANS}

@app.get("/api/billing/plans/{plan_id}")
def get_plan(plan_id: str):
    plan = next((p for p in PLANS if p["id"] == plan_id), None)
    if not plan:
        return {"detail": "Plan not found"}
    return plan

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
