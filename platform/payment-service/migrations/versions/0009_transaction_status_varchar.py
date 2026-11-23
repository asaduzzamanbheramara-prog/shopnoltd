"""Widen transaction status storage for requires_approval.

Revision ID: 0009_transaction_status_varchar
Revises: 0008_transaction_idempotency
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_transaction_status_varchar"
down_revision = "0008_transaction_idempotency"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        sa.text(
            "ALTER TABLE public.transactions "
            "ALTER COLUMN status TYPE VARCHAR(24) USING status::text"
        )
    )


def downgrade():
    # Refuse to narrow if a future status value would be truncated.
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "IF EXISTS (SELECT 1 FROM public.transactions WHERE length(status::text) > 16) THEN "
            "RAISE EXCEPTION 'cannot downgrade transaction status: values exceed VARCHAR(16)'; "
            "END IF; "
            "ALTER TABLE public.transactions ALTER COLUMN status TYPE VARCHAR(16) USING status::text; "
            "END $$"
        )
    )
