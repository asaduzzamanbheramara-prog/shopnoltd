"""add safe payment account registry

Revision ID: 0006_payment_accounts
Revises: 0005_direct_payments
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_payment_accounts"
down_revision = "0005_direct_payments"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payment_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("account_label", sa.String(128), nullable=False),
        sa.Column("account_type", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="BDT"),
        sa.Column("display_name", sa.String(128), nullable=True),
        sa.Column("masked_account", sa.String(128), nullable=True),
        sa.Column("public_identifier", sa.String(128), nullable=True),
        sa.Column("private_value", sa.String(256), nullable=True),
        sa.Column("instructions", sa.String(1000), nullable=True),
        sa.Column("qr_url", sa.String(2048), nullable=True),
        sa.Column("payment_url", sa.String(2048), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_payment_accounts_tenant", "payment_accounts", ["tenant_id"])
    op.create_index("ix_payment_accounts_provider", "payment_accounts", ["provider"])
    op.create_index("ix_payment_accounts_status", "payment_accounts", ["status"])
    op.create_index("ix_payment_accounts_sort", "payment_accounts", ["tenant_id", "sort_order"])


def downgrade():
    op.drop_index("ix_payment_accounts_sort", table_name="payment_accounts")
    op.drop_index("ix_payment_accounts_status", table_name="payment_accounts")
    op.drop_index("ix_payment_accounts_provider", table_name="payment_accounts")
    op.drop_index("ix_payment_accounts_tenant", table_name="payment_accounts")
    op.drop_table("payment_accounts")
