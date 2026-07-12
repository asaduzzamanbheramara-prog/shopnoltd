# Shopnoltd Billing Engine v6 — Real, Persistent, Multi-Gateway

## What changed from the old `app_platform/api/main.py`

| Before | Now |
|---|---|
| Wallets/transactions/users stored in Python `dict = {}` — wiped on every restart | Real SQLAlchemy models, persisted to Postgres (or SQLite locally) |
| Only Stripe had real code | Stripe, PayPal, Razorpay, SSLCommerz, bKash, Nagad all have real API integrations |
| bKash/PayPal/Razorpay/SSLCommerz were hardcoded fake `"fee"` and `"success_rate"` numbers | `/gateways` reports the *actual* configured status: `"live": true/false` |
| No way to tell demo data from real payments | Every transaction has `is_demo: true/false`, and API responses say so explicitly |
| No crypto, no Payoneer | Crypto (Bitcoin + ~200 coins via NOWPayments) added as a checkout gateway; Payoneer added as a **payout** helper (see note below) |
| Hardcoded, ever-staling exchange rates | `/exchange-rates` pulls live rates when `EXCHANGE_RATE_API_KEY` is set, otherwise honestly says `"live": false` |

**Nothing here pretends to be live when it isn't.** Any gateway without real credentials in the
environment automatically runs in demo mode and says so in its response (`note` field) — this was
the biggest gap in the old code, which silently presented made-up numbers as if they were real.

## Getting real credentials (you'll need to do this yourself — I can't sign up on your behalf)

- **Stripe**: https://dashboard.stripe.com/register — instant, has a sandbox/test mode.
- **PayPal**: https://developer.paypal.com/dashboard/applications — instant sandbox app.
- **Razorpay**: https://dashboard.razorpay.com/signup — instant sandbox; full KYC needed for live mode.
- **SSLCommerz** (Bangladesh): https://developer.sslcommerz.com/registration/ — instant sandbox store ID/password.
- **bKash** (Bangladesh): https://developer.bka.sh/ — sandbox is self-serve; live requires bKash merchant approval (registered business + bank account).
- **Nagad** (Bangladesh): merchant onboarding is done directly with Nagad's business team — they issue your merchant ID and exchange RSA keypairs with you. There's no public self-serve sandbox signup like the others.
- **Crypto / Bitcoin**: https://nowpayments.io — instant signup, sandbox available, non-custodial (coins go straight to your own wallet address).
- **Payoneer**: onboarding is via Payoneer's partner/marketplace program, not instant self-serve. Note: this is **payouts only** (paying sellers/affiliates), not a customer checkout method — see the warning below.
- **Live exchange rates**: https://openexchangerates.org/signup/free — free tier key, instant.

## Important: Payoneer is not a customer checkout option

I implemented `/payouts/payoneer` because that's what Payoneer's actual API supports: your business
sending money out to a seller, affiliate, or supplier who has a Payoneer account. There is no public
Payoneer API for a customer to click "Pay with Payoneer" at your checkout the way they can with
Stripe/PayPal/crypto. If customers specifically need to pay you via Payoneer, the accurate options
are: (a) they pay via card/PayPal and you don't touch Payoneer at all, or (b) you accept a manual
bank-style transfer to your Payoneer account and reconcile it by hand — neither of which I've wired
up automatically since both need a judgment call from you on the flow.

Put whichever you have into a `.env` file locally (see `.env.example`) or into the
`stripe-secret` / a new `bkash-secret`, `nagad-secret`, `sslcommerz-secret`, `paypal-secret`,
`razorpay-secret` Kubernetes Secrets in your cluster. Anything you leave out just runs in demo mode
— nothing breaks.

## Running locally

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in whatever keys you have
uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload
```

Check status: `curl http://localhost:5000/gateways`

## Deploying to your cluster (I don't have access to do this part — here's exactly what to run)

```bash
# 1. Build and push (your GitHub Actions can do this too, matching your other services)
docker build -t ghcr.io/asaduzzamanbheramara-prog/shopnoltd-billing-engine:v6 .
docker push ghcr.io/asaduzzamanbheramara-prog/shopnoltd-billing-engine:v6

# 2. Create/update secrets with whatever real keys you have (example for bKash sandbox):
kubectl create secret generic bkash-secret \
  --from-literal=BKASH_APP_KEY=xxx \
  --from-literal=BKASH_APP_SECRET=xxx \
  --from-literal=BKASH_USERNAME=xxx \
  --from-literal=BKASH_PASSWORD=xxx \
  --from-literal=BKASH_SANDBOX=true \
  --dry-run=client -o yaml | kubectl apply -f -
# repeat for sslcommerz-secret, paypal-secret, razorpay-secret, nagad-secret

# 3. Update deployment-billing-engine.yaml:
#    - bump the image tag to :v6
#    - add envFrom: secretRef entries for each new secret (stripe-secret is already there)
#    - add DATABASE_URL pointing at your existing postgres deployment

kubectl apply -f deployment-billing-engine.yaml
kubectl rollout status deployment/billing-engine
```

## Why some things are marked TODO instead of finished

- **Nagad** needs your actual RSA private key + Nagad's public key (exchanged during merchant
  onboarding) — I built the real signing/encryption flow, but it's mechanically untestable without
  your specific merchant keys.
- **PayPal webhook signature verification** needs a `PAYPAL_WEBHOOK_ID` from your PayPal app
  dashboard once you register a webhook URL — add it to `.env` and I can wire the verification call
  the same way Stripe's is done.
- The old currency exchange rates (`EXCHANGE_RATES` dict) were hardcoded and go stale immediately.
  If you want live FX, tell me and I'll wire in a live rates API (e.g. exchangerate.host) instead of
  static numbers — didn't want to add another silent "fake data" spot without you confirming.
