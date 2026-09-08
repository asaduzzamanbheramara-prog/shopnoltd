"""Provider registry and runtime deposit capabilities."""

from app.models.models import PaymentMethod
from app.providers.binance_pay import BinancePayProvider
from app.providers.bkash import BkashProvider
from app.providers.crypto import CryptoProvider
from app.providers.manual import ManualProvider
from app.providers.moneybag import MoneybagProvider
from app.providers.nagad import NagadProvider
from app.providers.payoneer import PayoneerProvider
from app.providers.paypal import PayPalProvider
from app.providers.razorpay import RazorpayProvider
from app.providers.sslcommerz import SSLCommerzProvider
from app.providers.stripe_provider import StripeProvider

_REG = {
    PaymentMethod.stripe: StripeProvider(),
    PaymentMethod.binance: BinancePayProvider(),
    PaymentMethod.bkash: BkashProvider(),
    PaymentMethod.nagad: NagadProvider(),
    PaymentMethod.razorpay: RazorpayProvider(),
    PaymentMethod.sslcommerz: SSLCommerzProvider(),
    PaymentMethod.moneybag: MoneybagProvider(),
    PaymentMethod.btc: CryptoProvider("btc"),
    PaymentMethod.eth: CryptoProvider("eth"),
    PaymentMethod.usdt: CryptoProvider("usdt"),
    PaymentMethod.bnb: CryptoProvider("bnb"),
    PaymentMethod.sol: CryptoProvider("sol"),
    PaymentMethod.trx: CryptoProvider("trx"),
    PaymentMethod.bank: ManualProvider("bank"),
    PaymentMethod.manual: ManualProvider("manual"),
    PaymentMethod.payeer: ManualProvider("payeer"),
    PaymentMethod.rocket: ManualProvider("rocket"),
    PaymentMethod.paypal: PayPalProvider(),
    PaymentMethod.payoneer: PayoneerProvider(),
}

# Deposit currencies are deliberately explicit at the payment boundary.  This
# prevents a provider from receiving a currency it cannot actually settle and
# keeps payout-only integrations out of customer checkout.
_DEPOSIT_CURRENCIES = {
    PaymentMethod.stripe: {"USD", "EUR", "GBP", "AUD", "CAD", "SGD", "JPY", "HKD", "NZD", "CHF"},
    PaymentMethod.paypal: {"USD", "EUR", "GBP", "AUD", "CAD", "JPY", "HKD", "SGD"},
    PaymentMethod.binance: {"USDT", "USDC", "BTC", "ETH", "BNB", "BUSD"},
    PaymentMethod.razorpay: {"INR", "USD"},
    PaymentMethod.sslcommerz: {"BDT"},
    PaymentMethod.bkash: {"BDT"},
    PaymentMethod.nagad: {"BDT"},
    PaymentMethod.moneybag: {"BDT"},
    PaymentMethod.btc: {"BTC"},
    PaymentMethod.eth: {"ETH"},
    PaymentMethod.usdt: {"USDT"},
    PaymentMethod.bnb: {"BNB"},
    PaymentMethod.sol: {"SOL"},
    PaymentMethod.trx: {"TRX"},
    PaymentMethod.bank: {"BDT", "USD", "EUR", "GBP", "INR"},
    PaymentMethod.manual: {"BDT", "USD", "EUR", "GBP", "INR"},
    PaymentMethod.payeer: {"USD", "EUR", "RUB"},
    PaymentMethod.rocket: {"BDT"},
}


class UnsupportedProvider(ValueError):
    """Raised when a method is registered but not valid for the requested operation."""


def get_provider(method: PaymentMethod):
    try:
        return _REG[method]
    except KeyError as exc:
        raise UnsupportedProvider(f"unsupported payment method: {method}") from exc


def supported_deposit_currencies(method: PaymentMethod) -> frozenset[str]:
    """Return currencies accepted for customer deposits by this method."""
    return frozenset(_DEPOSIT_CURRENCIES.get(method, set()))


def supports_deposit(method: PaymentMethod, currency: str) -> bool:
    return currency.upper() in supported_deposit_currencies(method)
