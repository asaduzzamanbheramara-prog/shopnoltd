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

def test_direct_payment_admin_reads_and_verification_are_tenant_scoped():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "app" / "api" / "direct_payments.py").read_text(encoding="utf-8")
    assert ".join(DirectPaymentIntent, DirectPaymentSubmission.intent_id == DirectPaymentIntent.id)" in source
    assert "query = query.where(DirectPaymentIntent.tenant_id == tenant_id)" in source
    assert "submission_query = submission_query.where(DirectPaymentIntent.tenant_id == tenant_id)" in source
    assert "Transaction.tenant_id == intent.tenant_id" in source
    assert "DirectPaymentAccount.tenant_id == intent.tenant_id" in source


def test_tenant_admin_receiving_account_creation_requires_signed_tenant():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "app" / "api" / "direct_payments.py").read_text(encoding="utf-8")
    assert "tenant_id = require_tenant_id(user)" in source
    assert 'tenant_id = str(user.get("tenant_id") or "default").strip()' in source

def test_admin_approval_and_rejection_are_tenant_scoped():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "app" / "api" / "admin.py").read_text(encoding="utf-8")
    assert source.count("Transaction.tenant_id == require_tenant_id(user)") == 3
    assert source.count("Wallet.tenant_id == tx.tenant_id") == 2

def test_direct_mfs_feed_refuses_ambiguous_receiver_accounts():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "app" / "api" / "direct_mfs_feed.py").read_text(encoding="utf-8")
    assert "matching_accounts = [a for a in accounts if _norm_number(a.account_number) == receiver]" in source
    assert "if len(matching_accounts) > 1:" in source
    assert "automatic credit refused" in source

def test_exchange_retry_lookup_is_tenant_scoped():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "exchanges.py"
    ).read_text(encoding="utf-8")
    import ast

    tree = ast.parse(source)
    transaction_queries = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "where"
        and "select(Transaction)" in ast.unparse(node.func.value)
    ]
    assert len(transaction_queries) >= 2
    for query in transaction_queries:
        assert "Transaction.tenant_id" in ast.unparse(query)

def test_wallet_ledger_transaction_query_is_tenant_scoped():
    from pathlib import Path
    import ast

    source = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "wallets.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    transaction_queries = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "where"
        and "select(Transaction)" in ast.unparse(node.func.value)
    ]
    assert transaction_queries
    assert any(
        "Transaction.wallet_id == w.id" in ast.unparse(query)
        and "Transaction.tenant_id == tenant_id" in ast.unparse(query)
        for query in transaction_queries
    )

def test_exchange_provider_errors_are_not_reflected_to_clients():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "exchanges.py"
    ).read_text(encoding="utf-8")
    assert 'HTTPException(502, "exchange provider unavailable") from None' in source
    assert 'f"Exchange provider unavailable: {exc}"' not in source

def test_direct_payment_amount_parser_rejects_invalid_nonfinite_and_nonpositive_values():
    from fastapi import HTTPException
    from app.api.direct_payments import _positive_decimal

    assert str(_positive_decimal("12.50", "invalid")) == "12.50"
    for value in ("not-a-number", "NaN", "Infinity", "-Infinity", "0", "-1", None):
        with pytest.raises(HTTPException) as exc:
            _positive_decimal(value, "invalid amount")
        assert exc.value.status_code == 422
        assert exc.value.detail == "invalid amount"

def test_internal_ad_wallet_idempotency_rejects_changed_payload():
    from types import SimpleNamespace
    from decimal import Decimal
    from fastapi import HTTPException
    from app.api.internal_ads import AdWalletOperation, _existing_operation_result
    from app.models.models import TxStatus, TxType

    existing = SimpleNamespace(
        id="tx-1",
        type=TxType.deposit,
        currency="BDT",
        amount=Decimal("50"),
        reference="ad-order-1",
        status=TxStatus.completed,
    )
    same = AdWalletOperation(
        tenant_id="tenant-a", user_id="user-a", currency="BDT", amount="50",
        operation="credit", idempotency_key="idem-key-001", reference="ad-order-1",
    )
    assert _existing_operation_result(existing, same, "BDT")["transaction_id"] == "tx-1"

    for changes in (
        {"amount": "51"},
        {"operation": "debit"},
        {"reference": "ad-order-2"},
        {"currency": "USD"},
    ):
        payload = same.model_dump()
        payload.update(changes)
        candidate = AdWalletOperation(**payload)
        with pytest.raises(HTTPException) as exc:
            _existing_operation_result(existing, candidate, candidate.currency.upper())
        assert exc.value.status_code == 409

def test_admin_transaction_decisions_lock_and_reject_only_pending_rows():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "admin.py"
    ).read_text(encoding="utf-8")
    assert source.count("s.execute(query.with_for_update())") == 2
    assert source.count('raise HTTPException(400, "tx not pending approval")') == 2
    assert source.count("Wallet.tenant_id == tx.tenant_id") == 2
    assert source.count("query.with_for_update()") == 2
    assert source.count(").with_for_update()") == 2

def test_withdrawal_idempotency_payload_is_bound_to_amount_currency_method_and_destination():
    from decimal import Decimal
    from types import SimpleNamespace
    from fastapi import HTTPException
    from app.api.withdrawals import _validate_existing_withdrawal, _destination_fingerprint
    from app.schemas.schemas import WithdrawalIn
    from app.models.models import PaymentMethod, TxStatus, TxType

    body = WithdrawalIn(
        currency="BDT", amount="100", method=PaymentMethod.manual,
        destination="01XXXXXXXXX", idempotency_key="withdrawal-key-01",
    )
    existing = SimpleNamespace(
        amount=Decimal("100"), currency="BDT", method=PaymentMethod.manual,
        meta={"destination_sha256": _destination_fingerprint("01XXXXXXXXX")},
        type=TxType.withdrawal, status=TxStatus.processing,
    )
    _validate_existing_withdrawal(existing, body, "BDT", Decimal("100"))

    for changes in (
        {"amount": "101"},
        {"currency": "USD"},
        {"method": PaymentMethod.bkash},
        {"destination": "01YYYYYYYYY"},
    ):
        payload = body.model_dump()
        payload.update(changes)
        candidate = WithdrawalIn(**payload)
        with pytest.raises(HTTPException) as exc:
            _validate_existing_withdrawal(existing, candidate, candidate.currency.upper(), Decimal(str(candidate.amount)))
        assert exc.value.status_code == 409


def test_withdrawals_persist_idempotency_before_provider_side_effect():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "withdrawals.py"
    ).read_text(encoding="utf-8")
    assert "Transaction.idempotency_key == body.idempotency_key" in source
    assert "idempotency_key=body.idempotency_key" in source
    assert source.index("await s.commit()") < source.index("provider.create_withdrawal")
    assert "withdrawal provider outcome is pending reconciliation" in source
    assert "destination_sha256" in source

@pytest.mark.parametrize("bad_amount", [float("nan"), float("inf"), float("-inf")])
def test_payment_request_schemas_reject_non_finite_amounts(bad_amount):
    from pydantic import ValidationError
    from app.schemas.schemas import DepositIn, WithdrawalIn, TransferIn

    with pytest.raises(ValidationError):
        DepositIn(currency="BDT", amount=bad_amount, method="manual", idempotency_key="deposit-key-01")
    with pytest.raises(ValidationError):
        WithdrawalIn(currency="BDT", amount=bad_amount, method="manual", destination="01XXXXXXXXX", idempotency_key="withdrawal-key-01")
    with pytest.raises(ValidationError):
        TransferIn(to_user_id="user-b", currency="BDT", amount=bad_amount, idempotency_key="transfer-key-01")

def test_admin_approval_checks_wallet_and_withdrawal_reservation_invariants():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "admin.py"
    ).read_text(encoding="utf-8")
    assert source.count('raise HTTPException(409, "transaction wallet is missing")') == 2
    assert 'if balance < amount or frozen < amount:' in source
    assert source.count('raise HTTPException(409, "withdrawal reservation is inconsistent; manual reconciliation required")') == 2
    assert 'only deposit and withdrawal transactions can be approved' in source

