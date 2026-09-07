"""
Ledger: every balance change (deposit, deduction, fine, admin adjustment)
goes through apply_ledger_entry() so there is one, and only one, code path
that touches wallet.balance. That's what makes it auditable and race-safe.

Row locking: SELECT ... FOR UPDATE takes a Postgres row lock on the wallet
for the duration of the transaction, so two concurrent requests touching the
same wallet serialize instead of racing.

Idempotency: payment webhooks may be delivered more than once. When a stable
reference is supplied, an existing ledger entry with the same user, currency,
and entry type is returned instead of applying the balance change again.
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Wallet, WalletLedgerEntry


class InsufficientBalanceError(Exception):
    pass


def apply_ledger_entry(
    db: Session,
    user_id: str,
    currency: str,
    delta: float,
    entry_type: str,
    reason: str,
    reference: str | None = None,
    created_by: str | None = None,
    allow_negative: bool = False,
) -> WalletLedgerEntry:
    """
    delta: positive to credit (deposit, refund, admin credit),
           negative to debit (deduction, fine, admin debit).
    Raises InsufficientBalanceError if the result would go negative and
    allow_negative is False.

    A stable reference makes repeated webhook/reconciliation delivery safe:
    the wallet row is locked before the idempotency lookup, so concurrent
    deliveries serialize correctly.
    """
    currency = currency.upper()
    wallet = (
        db.query(Wallet)
        .filter(Wallet.user_id == user_id, Wallet.currency == currency)
        .with_for_update()
        .first()
    )
    if not wallet:
        wallet = Wallet(user_id=user_id, currency=currency, balance=Decimal("0.00"))
        db.add(wallet)
        db.flush()

    if reference:
        existing = (
            db.query(WalletLedgerEntry)
            .filter(
                WalletLedgerEntry.user_id == user_id,
                WalletLedgerEntry.currency == currency,
                WalletLedgerEntry.entry_type == entry_type,
                WalletLedgerEntry.reference == reference,
            )
            .order_by(WalletLedgerEntry.created_at.asc())
            .first()
        )
        if existing:
            return existing

    current_balance = Decimal(str(wallet.balance))
    delta = Decimal(str(delta))
    new_balance = current_balance + delta
    if new_balance < 0 and not allow_negative:
        raise InsufficientBalanceError(
            f"Balance {current_balance} {currency} insufficient for {delta} {currency} ({entry_type})"
        )

    wallet.balance = new_balance

    entry = WalletLedgerEntry(
        user_id=user_id,
        currency=currency,
        entry_type=entry_type,
        amount=float(delta),
        balance_after=float(new_balance),
        reason=reason,
        reference=reference,
        created_by=created_by,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
