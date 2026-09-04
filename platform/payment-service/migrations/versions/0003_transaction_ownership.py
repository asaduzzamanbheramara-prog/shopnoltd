"""add transaction ownership and tenant-safe wallet uniqueness

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("transactions", sa.Column("user_id", sa.String(64), nullable=True))
    op.execute(
        sa.text(
            "UPDATE transactions t "
            "SET user_id = w.user_id "
            "FROM wallets w "
            "WHERE t.wallet_id = w.id AND t.user_id IS NULL"
        )
    )
    op.alter_column("transactions", "user_id", nullable=False)
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])

    op.drop_constraint("ix_wallet_user_currency", "wallets", type_="unique")
    op.create_unique_constraint(
        "ix_wallet_tenant_user_currency", "wallets", ["tenant_id", "user_id", "currency"]
    )

    op.create_index(
        "ix_transactions_external_method",
        "transactions",
        ["external_id", "method"],
    )


def downgrade():
    op.drop_index("ix_transactions_external_method", table_name="transactions")
    op.drop_constraint("ix_wallet_tenant_user_currency", "wallets", type_="unique")
    op.create_unique_constraint(
        "ix_wallet_user_currency", "wallets", ["user_id", "currency"]
    )
    op.drop_index("ix_transactions_user_id", table_name="transactions")
    op.drop_column("transactions", "user_id")
