from app.services.billing_service import BillingService


def key(user_id="user-1", operation="renew", request_key="request-0001"):
    return BillingService._idempotency_key(user_id, operation, request_key)


def test_same_request_reuses_same_charge_key():
    assert key() == key()


def test_distinct_renewal_requests_do_not_reuse_old_charge_key():
    assert key(request_key="renew-0001") != key(request_key="renew-0002")


def test_registration_and_renewal_are_separate_operations():
    assert key(operation="register") != key(operation="renew")


def test_idempotency_is_scoped_to_the_authenticated_user():
    assert key(user_id="user-1") != key(user_id="user-2")

def test_payment_service_endpoint_is_configured():
    import ast
    from pathlib import Path

    config_path = Path(__file__).parents[1] / "app" / "core" / "config.py"
    tree = ast.parse(config_path.read_text(encoding="utf-8"))
    settings_class = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "Settings"
    )
    fields = {
        node.target.id: ast.literal_eval(node.value)
        for node in settings_class.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.value is not None
    }
    assert fields["payment_service_url"] == (
        "http://payment-service.shopno-payments.svc.cluster.local:80"
    )

