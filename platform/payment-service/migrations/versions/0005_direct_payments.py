"""Add direct bKash/Nagad/Rocket payment flow tables.

Revision ID: 0005_direct_payments
Revises: 0004_transaction_ownership
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_direct_payments"
down_revision = "0004_transaction_ownership"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "direct_payment_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("account_type", sa.String(16), nullable=False),
        sa.Column("account_number", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=True),
        sa.Column("currency", sa.String(8), nullable=False, server_default="BDT"),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("verification_mode", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("instructions", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_direct_payment_accounts_tenant_id", "direct_payment_accounts", ["tenant_id"])
    op.create_index("ix_direct_payment_accounts_provider", "direct_payment_accounts", ["provider"])
    op.create_index(
        "uq_direct_account_number",
        "direct_payment_accounts",
        ["tenant_id", "provider", "account_number"],
        unique=True,
    )

    op.create_table(
        "direct_payment_intents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("order_id", sa.String(128), nullable=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("direct_payment_accounts.id"), nullable=False),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("expected_reference", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="created"),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("expected_reference", name="uq_direct_payment_intents_expected_reference"),
    )
    op.create_index("ix_direct_payment_intents_tenant_id", "direct_payment_intents", ["tenant_id"])
    op.create_index("ix_direct_payment_intents_user_id", "direct_payment_intents", ["user_id"])
    op.create_index("ix_direct_payment_intents_order_id", "direct_payment_intents", ["order_id"])
    op.create_index("ix_direct_payment_intents_status", "direct_payment_intents", ["status"])
    op.create_index("ix_direct_payment_intents_expires_at", "direct_payment_intents", ["expires_at"])

    op.create_table(
        "direct_payment_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("intent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("direct_payment_intents.id"), nullable=False),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("txid", sa.String(128), nullable=False),
        sa.Column("sender_number", sa.String(32), nullable=True),
        sa.Column("amount_claimed", sa.Numeric(20, 8), nullable=False),
        sa.Column("raw_evidence", postgresql.JSONB, nullable=False),
        sa.Column("verification_data", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="submitted"),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id"), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_direct_payment_submissions_intent_id", "direct_payment_submissions", ["intent_id"])
    op.create_index("ix_direct_payment_submissions_status", "direct_payment_submissions", ["status"])
    op.create_index(
        "uq_direct_submission_provider_txid",
        "direct_payment_submissions",
        ["provider", "txid"],
        unique=True,
    )


def downgrade():
    op.drop_index("uq_direct_submission_provider_txid", table_name="direct_payment_submissions")
    op.drop_index("ix_direct_payment_submissions_status", table_name="direct_payment_submissions")
    op.drop_index("ix_direct_payment_submissions_intent_id", table_name="direct_payment_submissions")
    op.drop_table("direct_payment_submissions")

    op.drop_index("ix_direct_payment_intents_expires_at", table_name="direct_payment_intents")
    op.drop_index("ix_direct_payment_intents_status", table_name="direct_payment_intents")
    op.drop_index("ix_direct_payment_intents_order_id", table_name="direct_payment_intents")
    op.drop_index("ix_direct_payment_intents_user_id", table_name="direct_payment_intents")
    op.drop_index("ix_direct_payment_intents_tenant_id", table_name="direct_payment_intents")
    op.drop_table("direct_payment_intents")

    op.drop_index("uq_direct_account_number", table_name="direct_payment_accounts")
    op.drop_index("ix_direct_payment_accounts_provider", table_name="direct_payment_accounts")
    op.drop_index("ix_direct_payment_accounts_tenant_id", table_name="direct_payment_accounts")
    op.drop_table("direct_payment_accounts")
