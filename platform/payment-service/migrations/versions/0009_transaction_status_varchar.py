"""Widen transaction status to support the requires_approval value.

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
    op.alter_column(
        "transactions",
        "status",
        schema="public",
        existing_type=sa.String(length=16),
        type_=sa.String(length=24),
        existing_nullable=False,
    )


def downgrade():
    # Forward-only: a 17-character requires_approval value cannot fit in VARCHAR(16).
    # Do not risk truncating or rejecting historical transaction status values.
    pass
