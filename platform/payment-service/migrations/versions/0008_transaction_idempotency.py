"""Add transaction idempotency storage without changing historical rows.

Revision ID: 0008_transaction_idempotency
Revises: 0007_wallet_tenant_user_currency
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_transaction_idempotency"
down_revision = "0007_wallet_tenant_user_currency"
branch_labels = None
depends_on = None


def upgrade():
    # Nullable by design: existing transactions remain valid and unchanged.
    op.execute(
        sa.text(
            "ALTER TABLE public.transactions "
            "ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(128)"
        )
    )
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_transaction_deposit_idempotency "
            "ON public.transactions (tenant_id, user_id, type, idempotency_key) "
            "WHERE idempotency_key IS NOT NULL"
        )
    )


def downgrade():
    # Preserve the nullable key values; only remove the uniqueness guard so
    # earlier revisions can safely remove columns that the index references.
    op.execute(
        sa.text("DROP INDEX IF EXISTS public.uq_transaction_deposit_idempotency")
    )
