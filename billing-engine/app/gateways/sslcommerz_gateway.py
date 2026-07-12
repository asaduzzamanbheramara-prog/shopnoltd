import uuid
import requests
from app import config
from app.gateways.base import PaymentGateway, GatewayResult

API_URLS = {
    True: "https://sandbox.sslcommerz.com/gwprocess/v4/api.php",
    False: "https://securepay.sslcommerz.com/gwprocess/v4/api.php",
}
VALIDATE_URLS = {
    True: "https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php",
    False: "https://securepay.sslcommerz.com/validator/api/validationserverAPI.php",
}


class SSLCommerzGateway(PaymentGateway):
    name = "sslcommerz"

    def __init__(self):
        self.enabled = config.SSLCOMMERZ_ENABLED
        self.sandbox = config.SSLCOMMERZ_SANDBOX

    def create_payment(self, amount: float, currency: str, reference: str, **kwargs) -> GatewayResult:
        if not self.enabled:
            return GatewayResult(
                gateway=self.name, is_demo=True, status="pending",
                gateway_reference=f"demo_ssl_{uuid.uuid4().hex[:12]}",
                redirect_url=None,
                note="SSLCommerz not configured (missing store id/password) - running in demo mode.",
            )
        payload = {
            "store_id": config.SSLCOMMERZ_STORE_ID,
            "store_passwd": config.SSLCOMMERZ_STORE_PASSWORD,
            "total_amount": f"{amount:.2f}",
            "currency": currency.upper(),
            "tran_id": reference,
            "success_url": kwargs.get("success_url", f"{config.BASE_CALLBACK_URL}/webhook/sslcommerz/success"),
            "fail_url": kwargs.get("fail_url", f"{config.BASE_CALLBACK_URL}/webhook/sslcommerz/fail"),
            "cancel_url": kwargs.get("cancel_url", f"{config.BASE_CALLBACK_URL}/webhook/sslcommerz/cancel"),
            "cus_name": kwargs.get("customer_name", "Shopnoltd Customer"),
            "cus_email": kwargs.get("customer_email", "customer@example.com"),
            "cus_add1": kwargs.get("customer_address", "N/A"),
            "cus_phone": kwargs.get("customer_phone", "01700000000"),
            "shipping_method": "NO",
            "product_name": kwargs.get("product_name", "Shopnoltd Order"),
            "product_category": "General",
            "product_profile": "general",
        }
        resp = requests.post(API_URLS[self.sandbox], data=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return GatewayResult(
            gateway=self.name, is_demo=False,
            status="pending" if data.get("status") == "SUCCESS" else "failed",
            gateway_reference=reference, redirect_url=data.get("GatewayPageURL"),
            raw=data,
        )

    def validate_transaction(self, val_id: str) -> dict:
        resp = requests.get(
            VALIDATE_URLS[self.sandbox],
            params={
                "val_id": val_id,
                "store_id": config.SSLCOMMERZ_STORE_ID,
                "store_passwd": config.SSLCOMMERZ_STORE_PASSWORD,
                "format": "json",
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def verify_webhook(self, payload: bytes, headers: dict) -> dict:
        # SSLCommerz posts form-encoded IPN data and additionally requires a server-side
        # validate_transaction() call using val_id before trusting the payment. Handled in main.py.
        raise NotImplementedError
