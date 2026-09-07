"""durable webhook event idempotency
Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("event_key", sa.String(128), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="received"),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("received_at", sa.DateTime, nullable=False),
        sa.Column("processed_at", sa.DateTime, nullable=True),
    )
    op.create_index(
        "uq_webhook_provider_event",
        "webhook_events",
        ["provider", "event_key"],
        unique=True,
    )


def downgrade():
    op.drop_index("uq_webhook_provider_event", table_name="webhook_events")
    op.drop_table("webhook_events")
