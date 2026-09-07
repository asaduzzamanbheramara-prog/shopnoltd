"""Safe automation policy: no arbitrary shell, URLs, or gateway secrets."""

ALLOWED_TRIGGERS = {
    "schedule", "webhook", "payment.success", "payment.failed", "domain.renewal_due",
    "wallet.threshold", "device.online", "device.offline", "collect.submission", "exchange.rate_changed",
}

ALLOWED_ACTIONS = {
    "notify", "device.request_sync", "device.collect_refresh", "service.fulfill", "billing.retry_payment",
    "domain.prepare_renewal", "wallet.check", "webhook.emit",
}

SECRET_KEYS = {"password", "secret", "token", "api_key", "api_secret", "merchant_key", "private_key"}


def validate_definition(trigger_type: str, action_type: str, max_retries: int) -> None:
    if trigger_type not in ALLOWED_TRIGGERS:
        raise ValueError("unsupported automation trigger")
    if action_type not in ALLOWED_ACTIONS:
        raise ValueError("unsupported automation action")
    if max_retries < 0 or max_retries > 10:
        raise ValueError("max_retries must be between 0 and 10")


def reject_secrets(value):
    """Reject secret-bearing automation configuration recursively."""
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in SECRET_KEYS:
                raise ValueError("automation configuration cannot contain credentials or secrets")
            reject_secrets(child)
    elif isinstance(value, list):
        for child in value:
            reject_secrets(child)
