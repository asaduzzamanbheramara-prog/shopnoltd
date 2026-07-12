"""Provider registry."""
from app.providers.stripe_provider import StripeProvider
from app.providers.binance_pay import BinancePayProvider
from app.providers.bkash import BkashProvider
from app.providers.crypto import CryptoProvider
from app.providers.manual import ManualProvider
from app.models.models import PaymentMethod
_REG = {
    PaymentMethod.stripe:  StripeProvider(),
    PaymentMethod.binance: BinancePayProvider(),
    PaymentMethod.bkash:   BkashProvider(),
    PaymentMethod.btc:     CryptoProvider("btc"),
    PaymentMethod.eth:     CryptoProvider("eth"),
    PaymentMethod.usdt:    CryptoProvider("usdt"),
    PaymentMethod.bnb:     CryptoProvider("bnb"),
    PaymentMethod.sol:     CryptoProvider("sol"),
    PaymentMethod.trx:     CryptoProvider("trx"),
    PaymentMethod.bank:    ManualProvider("bank"),
    PaymentMethod.manual:  ManualProvider("manual"),
    PaymentMethod.payeer:  ManualProvider("payeer"),
    PaymentMethod.nagad:   ManualProvider("nagad"),
    PaymentMethod.rocket:  ManualProvider("rocket"),
    PaymentMethod.paypal:  ManualProvider("paypal"),
}
def get_provider(method: PaymentMethod):
    if method not in _REG: raise ValueError(f"unsupported method: {method}")
    return _REG[method]

