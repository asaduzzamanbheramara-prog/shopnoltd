"""Manual + bank + Payeer + Nagad + Rocket providers. All use admin approval."""
from app.providers.base import BaseProvider
class ManualProvider(BaseProvider):
    def __init__(self, name: str = "manual"): super().__init__(name)
    async def create_deposit(self, tx, **kwargs):
        return {"approval_url": f"https://shopnoltd.dpdns.org/admin/approve/{tx.id}", "instructions": f"Send {tx.amount} {tx.currency} and reference {tx.id}."}
    async def create_withdrawal(self, tx, **kwargs):
        return {"external_id": f"manual-wd-{tx.id}", "status": "requires_approval"}
    async def verify_webhook(self, body, headers): return {"raw": body.decode("utf-8", "ignore")}
    async def get_status(self, external_id): return "requires_approval"

