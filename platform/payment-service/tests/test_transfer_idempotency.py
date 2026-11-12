from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.transfers import _validate_existing_transfer
from app.schemas.schemas import TransferIn


def existing_transfer(*, to="platform-wallet", currency="USD", amount=Decimal("12.00"), note="Domain registration: example.com (1yr)"):
    return SimpleNamespace(
        meta={"to": to, "note": note},
        currency=currency,
        amount=-amount,
    )


def request(*, to="platform-wallet", currency="USD", amount="12.00", note="Domain registration: example.com (1yr)"):
    return TransferIn(
        to_user_id=to,
        currency=currency,
        amount=Decimal(amount),
        note=note,
        idempotency_key="request-key-0001",
    )


def test_same_key_and_same_payload_can_be_retried():
    _validate_existing_transfer(existing_transfer(), request(), "USD", Decimal("12.00"))


@pytest.mark.parametrize(
    "body,currency,amount",
    [
        (request(to="different-wallet"), "USD", Decimal("12.00")),
        (request(currency="EUR"), "EUR", Decimal("12.00")),
        (request(amount="24.00"), "USD", Decimal("24.00")),
        (request(note="Domain renewal: example.com (1yr)"), "USD", Decimal("12.00")),
    ],
)
def test_same_key_with_changed_payload_is_rejected(body, currency, amount):
    with pytest.raises(HTTPException) as exc:
        _validate_existing_transfer(existing_transfer(), body, currency, amount)
    assert exc.value.status_code == 409


def test_money_movement_wallet_queries_are_tenant_scoped():
    """Every user-facing wallet lookup must include the signed tenant claim."""
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app" / "api"
    modules = ("deposits.py", "withdrawals.py", "transfers.py", "exchanges.py")
    for module in modules:
        tree = ast.parse((root / module).read_text(encoding="utf-8"))
        wallet_selects = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "where"
            and "select(Wallet)" in ast.unparse(node.func.value)
        ]
        assert wallet_selects, f"{module} should contain wallet lookups"
        for query in wallet_selects:
            assert "Wallet.tenant_id" in ast.unparse(query), (
                f"{module} contains a wallet lookup without tenant isolation: "
                f"{ast.unparse(query)}"
            )


def test_transfer_transaction_lookups_are_tenant_scoped():
    import ast
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "app" / "api" / "transfers.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    transaction_queries = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "where"
        and "select(Transaction)" in ast.unparse(node.func.value)
    ]
    assert transaction_queries
    for query in transaction_queries:
        assert "Transaction.tenant_id" in ast.unparse(query)


def test_payment_tenant_claim_is_required_not_defaulted():
    from app.core.tenant import require_tenant_id

    assert require_tenant_id({"tenant_id": "tenant-a"}) == "tenant-a"
    for claims in ({}, {"tenant_id": ""}, {"tenant_id": "   "}, {"tenant_id": None}):
        with pytest.raises(HTTPException) as exc:
            require_tenant_id(claims)
        assert exc.value.status_code == 403


def test_customer_payment_routes_do_not_fall_back_to_default_tenant():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app" / "api"
    for module in ("wallets.py", "deposits.py", "withdrawals.py", "transfers.py",
                   "exchanges.py", "direct_payments.py"):
        source = (root / module).read_text(encoding="utf-8")
        assert 'user.get("tenant_id", "default")' not in source, (
            f"{module} must not silently assign an unscoped token to the default tenant"
        )


def test_payment_tenant_claim_is_required_not_defaulted():
    from app.core.tenant import require_tenant_id

    assert require_tenant_id({"tenant_id": "tenant-a"}) == "tenant-a"
    for claims in ({}, {"tenant_id": ""}, {"tenant_id": "   "}, {"tenant_id": None}):
        with pytest.raises(HTTPException) as exc:
            require_tenant_id(claims)
        assert exc.value.status_code == 403


def test_customer_payment_routes_do_not_fall_back_to_default_tenant():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app" / "api"
    modules = ("wallets.py", "deposits.py", "withdrawals.py", "transfers.py",
               "exchanges.py", "direct_payments.py", "transactions.py")
    for module in modules:
        source = (root / module).read_text(encoding="utf-8")
        assert 'user.get("tenant_id", "default")' not in source, (
            f"{module} must not silently assign an unscoped token to the default tenant"
        )


def test_history_requires_tenant_claim_before_querying():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "app" / "api" / "transactions.py").read_text(encoding="utf-8")
    assert "tenant_id = require_tenant_id(user)" in source
    assert "Transaction.tenant_id == tenant_id" in source
