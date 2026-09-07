"""
Ledger: every balance change goes through apply_ledger_entry().

Wallet rows are locked before reading or changing the balance. Stable
references make repeated payment/webhook delivery idempotent.
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

    current_balance = Decimal(str(wallet.balance or 0))
    delta_decimal = Decimal(str(delta))
    new_balance = current_balance + delta_decimal
    if new_balance < 0 and not allow_negative:
        raise InsufficientBalanceError(
            f"Balance {current_balance} {currency} insufficient for {delta_decimal} {currency} ({entry_type})"
        )

    wallet.balance = new_balance
    entry = WalletLedgerEntry(
        user_id=user_id,
        currency=currency,
        entry_type=entry_type,
        amount=delta_decimal,
        balance_after=new_balance,
        reason=reason,
        reference=reference,
        created_by=created_by,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
