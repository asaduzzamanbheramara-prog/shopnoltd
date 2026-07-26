from app.gateways.bkash_gateway import BkashGateway
from app.gateways.crypto_gateway import CryptoGateway
from app.gateways.nagad_gateway import NagadGateway
from app.gateways.payoneer_payouts import PayoneerPayouts
from app.gateways.paypal_gateway import PayPalGateway
from app.gateways.razorpay_gateway import RazorpayGateway
from app.gateways.sslcommerz_gateway import SSLCommerzGateway
from app.gateways.stripe_gateway import StripeGateway

REGISTRY = {
    "stripe": StripeGateway(),
    "paypal": PayPalGateway(),
    "razorpay": RazorpayGateway(),
    "sslcommerz": SSLCommerzGateway(),
    "bkash": BkashGateway(),
    "nagad": NagadGateway(),
    "crypto": CryptoGateway(),
}

# Not a checkout gateway - kept separate since it's payouts, not "customer pays us".
payoneer_payouts = PayoneerPayouts()


def get_gateway(name: str):
    gw = REGISTRY.get(name.lower())
    if gw is None:
        raise KeyError(f"Unknown gateway '{name}'. Available: {list(REGISTRY)}")
    return gw
