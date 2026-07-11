import argparse
import hashlib
import hmac
import json
import os
import time
import requests


def compute_stripe_signature(payload: str, secret: str, timestamp: int) -> str:
    signed_payload = f"{timestamp}.{payload}"
    signature = hmac.new(secret.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


def main():
    parser = argparse.ArgumentParser(description="Send a signed Stripe webhook event to a Shopnoltd billing webhook endpoint.")
    parser.add_argument("--url", default=os.getenv("SHOPNOLTD_WEBHOOK_URL", "https://billing.shopnoltd.dpdns.org/billing/webhook"))
    parser.add_argument("--secret", default=os.getenv("STRIPE_WEBHOOK_SECRET"))
    args = parser.parse_args()

    if not args.secret:
        raise SystemExit("Missing STRIPE_WEBHOOK_SECRET environment variable or --secret argument")

    event = {
        "id": "evt_test_webhook",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "amount_total": 4999,
                "currency": "usd",
                "customer_email": "test@example.com",
                "payment_status": "paid"
            }
        },
        "created": int(time.time())
    }
    payload = json.dumps(event)
    signature = compute_stripe_signature(payload, args.secret, int(time.time()))

    headers = {
        "Content-Type": "application/json",
        "Stripe-Signature": signature
    }

    response = requests.post(args.url, headers=headers, data=payload)
    print(f"POST {args.url} -> {response.status_code}")
    print(response.text)


if __name__ == "__main__":
    main()
