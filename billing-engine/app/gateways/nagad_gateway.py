import base64
import datetime
import uuid

import requests

from app import config
from app.gateways.base import GatewayResult, PaymentGateway

BASE_URLS = {
    True: "http://sandbox.mynagad.com:10080/remote-payment-gateway-1.0/api/dfs",
    False: "https://api.mynagad.com/api/dfs",
}


class NagadGateway(PaymentGateway):
    """
    Nagad's Merchant API signs/encrypts every request with RSA keypairs exchanged with
    Nagad during merchant onboarding (your private key + Nagad's public key). The
    cryptography package is required for the real flow: pip install cryptography
    """

    name = "nagad"

    def __init__(self):
        self.enabled = config.NAGAD_ENABLED
        self.sandbox = config.NAGAD_SANDBOX
        self.base_url = BASE_URLS[self.sandbox]

    def _sign(self, data: str) -> str:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding

        private_key = serialization.load_pem_private_key(
            config.NAGAD_MERCHANT_PRIVATE_KEY.encode(),
            password=None,
        )
        signature = private_key.sign(data.encode(), padding.PKCS1v15(), hashes.SHA256())
        return base64.b64encode(signature).decode()

    def _encrypt(self, data: str) -> str:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import padding

        public_key = serialization.load_pem_public_key(config.NAGAD_PG_PUBLIC_KEY.encode())
        encrypted = public_key.encrypt(data.encode(), padding.PKCS1v15())
        return base64.b64encode(encrypted).decode()

    def create_payment(
        self, amount: float, currency: str, reference: str, **kwargs
    ) -> GatewayResult:
        if not self.enabled:
            return GatewayResult(
                gateway=self.name,
                is_demo=True,
                status="pending",
                gateway_reference=f"demo_nagad_{uuid.uuid4().hex[:12]}",
                redirect_url=None,
                note="Nagad not configured (missing merchant id/RSA keys) - running in demo mode.",
            )
        if currency.upper() != "BDT":
            raise ValueError("Nagad only supports BDT")

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        order_id = reference
        customer_ip = kwargs.get("customer_ip", "127.0.0.1")

        # Step 1: Initialize payment
        sensitive = f"merchantId={config.NAGAD_MERCHANT_ID}&datetime={timestamp}&orderId={order_id}&challenge={uuid.uuid4().hex}"
        init_payload = {
            "accountNumber": config.NAGAD_MERCHANT_ID,
            "dateTime": timestamp,
            "sensitiveData": self._encrypt(sensitive),
            "signature": self._sign(sensitive),
        }
        init_resp = requests.post(
            f"{self.base_url}/check-out/initialize/{config.NAGAD_MERCHANT_ID}/{order_id}",
            json=init_payload,
            headers={"X-KM-IP-V4": customer_ip, "X-KM-Client-Type": "PC_WEB"},
            timeout=15,
        )
        init_resp.raise_for_status()
        init_data = init_resp.json()
        payment_ref_id = init_data.get("paymentReferenceId")
        challenge = init_data.get("challenge")

        # Step 2: Complete payment (creates redirect URL)
        complete_sensitive = (
            f"merchantId={config.NAGAD_MERCHANT_ID}&orderId={order_id}&currencyCode=050"
            f"&amount={amount:.2f}&challenge={challenge}"
        )
        complete_payload = {
            "sensitiveData": self._encrypt(complete_sensitive),
            "signature": self._sign(complete_sensitive),
            "merchantCallbackURL": f"{config.BASE_CALLBACK_URL}/webhook/nagad/callback",
        }
        complete_resp = requests.post(
            f"{self.base_url}/check-out/complete/{payment_ref_id}",
            json=complete_payload,
            headers={"X-KM-IP-V4": customer_ip, "X-KM-Client-Type": "PC_WEB"},
            timeout=15,
        )
        complete_resp.raise_for_status()
        complete_data = complete_resp.json()
        return GatewayResult(
            gateway=self.name,
            is_demo=False,
            status="pending",
            gateway_reference=payment_ref_id,
            redirect_url=complete_data.get("callBackUrl"),
            raw=complete_data,
        )

    def verify_webhook(self, payload: bytes, headers: dict) -> dict:
        # Nagad redirects to merchantCallbackURL with payment_ref_id & status query params;
        # the server should then call the "verify payment" endpoint to confirm. Handled in main.py.
        raise NotImplementedError
