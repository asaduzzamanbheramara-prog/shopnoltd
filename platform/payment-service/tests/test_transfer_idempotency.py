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

def test_exchange_idempotency_rejects_changed_currency_pair_or_amount():
    from decimal import Decimal
    from types import SimpleNamespace
    from fastapi import HTTPException
    from app.api.exchanges import _existing_result

    existing = SimpleNamespace(
        meta={
            "from_amount": "25",
            "to_amount": "30",
            "rate": "1.2",
            "from_currency": "USD",
            "to_currency": "EUR",
        },
        fee=Decimal("0.5"),
        id="exchange-tx-1",
    )
    _existing_result(existing, "USD", "EUR", "exchange:key-0001", Decimal("25"))
    for frm, to, amount in (
        ("GBP", "EUR", Decimal("25")),
        ("USD", "BDT", Decimal("25")),
        ("USD", "EUR", Decimal("26")),
    ):
        with pytest.raises(HTTPException) as exc:
            _existing_result(existing, frm, to, "exchange:key-0001", amount)
        assert exc.value.status_code == 409

def test_deposit_provider_errors_are_redacted_from_api_and_transaction_metadata():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "deposits.py"
    ).read_text(encoding="utf-8")
    assert "raise HTTPException(503, \"payment provider is unavailable\") from None" in source
    assert "raise HTTPException(502, \"payment provider request failed\") from None" in source
    assert '"_error": str(exc)' not in source
    assert "out.get(\"note\")" not in source

def test_withdrawal_fee_is_reserved_and_settled_with_principal():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app" / "api"
    withdrawal = (root / "withdrawals.py").read_text(encoding="utf-8")
    admin = (root / "admin.py").read_text(encoding="utf-8")
    assert "reserved_amount = amount + fee" in withdrawal
    assert "available < reserved_amount" in withdrawal
    assert "wallet.frozen = Decimal(str(wallet.frozen)) + reserved_amount" in withdrawal
    assert "Decimal(str(tx.amount)) + Decimal(str(tx.fee))" in admin

def test_wallet_ledger_accounts_for_withdrawal_and_exchange_fees():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "wallets.py"
    ).read_text(encoding="utf-8")
    assert "amount = -(amount + float(t.fee or 0))" in source
    assert "amount -= float(t.fee or 0)" in source

def test_direct_payment_verification_allows_only_one_credit_per_intent():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "direct_payments.py"
    ).read_text(encoding="utf-8")
    assert 'if sub.status != "submitted":' in source
    assert 'if not intent or intent.status != "submitted":' in source
    assert "intent_query.with_for_update()" in source
    assert "submission_query.with_for_update()" in source

def test_direct_payment_evidence_amount_must_match_intent():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "direct_payments.py"
    ).read_text(encoding="utf-8")
    assert 'if claimed_amount != Decimal(str(intent.amount)):' in source
    assert 'submitted amount does not match the payment intent' in source

def test_signed_mfs_feed_amount_parser_rejects_non_finite_values():
    from fastapi import HTTPException
    from app.api.direct_mfs_feed import _decimal

    assert _decimal("25.50", "amount") == Decimal("25.50")
    for value in ("NaN", "Infinity", "-Infinity", "0", "-1"):
        with pytest.raises(HTTPException) as exc:
            _decimal(value, "amount")
        assert exc.value.status_code == 422

def test_deposit_idempotency_rejects_changed_amount_currency_or_method():
    from decimal import Decimal
    from types import SimpleNamespace
    from fastapi import HTTPException
    from app.api.deposits import _validate_existing_deposit
    from app.schemas.schemas import DepositIn
    from app.models.models import PaymentMethod

    body = DepositIn(
        currency="BDT", amount="100", method=PaymentMethod.manual,
        idempotency_key="deposit-key-001",
    )
    existing = SimpleNamespace(
        amount=Decimal("100"), currency="BDT", method=PaymentMethod.manual,
    )
    _validate_existing_deposit(existing, body, "BDT")
    for changes in (
        {"amount": "101"},
        {"currency": "USD"},
        {"method": PaymentMethod.bkash},
    ):
        payload = body.model_dump()
        payload.update(changes)
        candidate = DepositIn(**payload)
        with pytest.raises(HTTPException) as exc:
            _validate_existing_deposit(existing, candidate, candidate.currency.upper())
        assert exc.value.status_code == 409

def test_configured_withdrawal_approval_cannot_be_overridden_by_provider_status():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "withdrawals.py"
    ).read_text(encoding="utf-8")
    assert "if settings.admin_approval_required or out.get(\"status\") == \"requires_approval\"" in source

def test_platform_fee_configuration_is_finite_and_bounded():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "app" / "core" / "config.py"
    ).read_text(encoding="utf-8")
    assert "Field(default=1.5, ge=0, le=100, allow_inf_nan=False)" in source

def test_wallet_creation_does_not_swallow_unrelated_database_errors():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "wallets.py"
    ).read_text(encoding="utf-8")
    assert "from sqlalchemy.exc import IntegrityError" in source
    assert "except IntegrityError:" in source
    assert "except Exception:" not in source

def test_required_withdrawal_approval_precedes_any_external_payout_call():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "withdrawals.py"
    ).read_text(encoding="utf-8")
    approval_guard = source.index("if settings.admin_approval_required:")
    payout_call = source.index("provider.create_withdrawal")
    assert approval_guard < payout_call
    assert "return _withdrawal_out(tx)" in source[approval_guard:payout_call]

def test_signed_mfs_auto_credit_requires_exact_payment_intent_reference():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "direct_mfs_feed.py"
    ).read_text(encoding="utf-8")
    assert 'if not reference or reference.strip().upper() != intent.expected_reference.strip().upper():' in source
    assert 'payment reference does not match the selected payment intent' in source

def test_direct_payment_intent_endpoint_uses_validated_request_schema():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "direct_payments.py"
    ).read_text(encoding="utf-8")
    assert "DirectPaymentIntentIn, DirectPaymentVerificationIn" in source
    assert "async def create_intent(body: DirectPaymentIntentIn" in source

def test_direct_payment_submission_endpoint_uses_validated_request_schema():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "direct_payments.py"
    ).read_text(encoding="utf-8")
    assert "DirectPaymentIntentIn, DirectPaymentSubmissionIn, DirectPaymentVerificationIn" in source
    assert "body: DirectPaymentSubmissionIn" in source

