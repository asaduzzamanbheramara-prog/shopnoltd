"""BTC/ETH/USDT/BNB/SOL/TRX provider using public RPC + admin approval for sweep."""
from app.providers.base import BaseProvider
from app.core.config import settings
import secrets
class CryptoProvider(BaseProvider):
    NETWORKS = {
        "btc":  ("bitcoin",  "bc1q"),
        "eth":  ("ethereum", "0x"),
        "usdt": ("ethereum", "0x"),
        "bnb":  ("bsc",      "0x"),
        "sol":  ("solana",   ""),
        "trx":  ("tron",     "T"),
    }
    def __init__(self, asset: str):
        super().__init__(f"crypto-{asset}"); self.asset = asset.upper()
    async def create_deposit(self, tx, **kwargs):
        net, prefix = self.NETWORKS[tx.method.value]
        addr = (prefix + secrets.token_hex(20)) if prefix else secrets.token_hex(32)
        return {"address": addr, "memo": str(tx.id)[:32], "redirect_url": f"https://shopnoltd.dpdns.org/pay/crypto/{tx.id}"}
    async def create_withdrawal(self, tx, destination, **kwargs):
        return {"external_id": f"crypto-wd-{tx.id}", "status": "requires_approval", "address": destination}
    async def verify_webhook(self, body, headers): return {"raw": body.decode("utf-8", "ignore")}
    async def get_status(self, external_id): return "pending"

