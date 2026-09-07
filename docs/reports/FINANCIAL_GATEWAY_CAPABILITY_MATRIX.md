# Shopnoltd Financial Gateway Capability Matrix

This is the canonical distinction between **implemented**, **credential-configured**, and **live/E2E-verified**. A gateway must never be presented as live merely because an adapter exists.

| Provider | Customer checkout/deposit | Customer payout/withdrawal | Webhook/verification | Currency scope | Activation rule |
|---|---|---|---|---|---|
| Stripe | Implemented | Implemented via transfer path where account capability permits | Implemented/signed | Gateway/account supported currencies | Require credentials + webhook secret + sandbox E2E |
| PayPal | Implemented | Provider/account dependent | Implemented | Provider/account supported currencies | Require credentials + webhook verification E2E |
| Binance Pay | Implemented | Provider capability must be verified separately | Implemented | Crypto/provider supported currencies | Require merchant credentials + sandbox E2E |
| Razorpay | Implemented | Provider/account dependent | Implemented | Primarily INR plus account-supported currencies | Require credentials + webhook E2E |
| SSLCommerz | Implemented | Not a customer payout rail | Implemented via gateway validation/callback | BDT | Require store credentials + sandbox E2E |
| bKash | Implemented | Not treated as generic customer payout | Implemented via callback + server execution | BDT | Require merchant credentials + sandbox E2E |
| Nagad | Implemented | Not treated as generic customer payout | Implemented | BDT | Require merchant credentials + sandbox E2E |
| Moneybag | Hosted checkout/deposit implemented | **Not supported by current public integration** | Signed HMAC + server-side verify implemented | BDT in current integration | Require fresh sandbox credentials + exact webhook endpoint + duplicate/failed/cancelled tests |
| Crypto / NOWPayments | Implemented | Provider/asset dependent | Implemented | BTC/ETH/USDT and provider-supported assets | Require API/IPN credentials + asset E2E |
| Payoneer | **No customer checkout** | Payout-only adapter implemented | Status/webhook surface requires provider contract verification | Provider/program supported payout currencies | Never demo; require program/API credentials before payout |
| Payeer | Manual adapter | Manual workflow | No native automated provider contract claimed | Manual workflow | Keep explicitly manual until a supported native API is implemented |
| Rocket | Manual adapter | Manual workflow | No native automated provider contract claimed | BDT/manual workflow | Keep explicitly manual until a supported native API is implemented |
| Bank transfer | Manual | Manual | Manual/admin | Account-supported | Explicit manual reconciliation |
| Manual | Manual | Manual | Manual/admin | Configured | Explicit manual reconciliation |

## Wallet / currency rules

1. Wallet balance is currency-specific; changing `currency` must select/create the corresponding wallet rather than reinterpret an existing balance.
2. Amount changes must flow through Decimal/Numeric arithmetic and must be reflected consistently in transaction, wallet, and ledger records.
3. FX conversion must return source currency, destination currency, amount, converted amount, rate, and whether the rate is live.
4. Gateway checkout currency must be validated against that gateway's actual configured capability before payment creation.
5. Unsupported payout/refund operations return an explicit unavailable/not-supported result; they are never simulated as successful.
6. Every successful webhook fulfillment is idempotent and must produce one durable ledger effect.

## Google Pay

Google Pay is not treated as a fake independent processor. It is exposed through the Stripe payment-method layer where the Stripe account, merchant domain, browser/device, and Payment Element configuration make Google Pay eligible. The platform should advertise it only when runtime Stripe/payment-method eligibility is confirmed.

## Moneybag sandbox

Moneybag is currently integrated against the sandbox hosted-checkout and verification APIs. The public webhook relay is:

`https://api.shopnoltd.dpdns.org/api/v1/webhook/moneybag/ipn`

The external Moneybag dashboard must use this secure relay (or another explicitly implemented secure relay). Merchant secrets are Kubernetes runtime secrets only and must never be committed.

## Release gate

A provider moves from **implemented** to **active** only after:

- credentials are present in the target environment;
- gateway/admin enablement is on;
- checkout/deposit succeeds in sandbox;
- webhook signature is accepted;
- server-side status is verified;
- amount and currency are compared with the original transaction;
- duplicate webhook delivery produces no second ledger credit;
- failed/cancelled/expired events do not credit the wallet;
- restart/retry behavior preserves the same final financial state.
