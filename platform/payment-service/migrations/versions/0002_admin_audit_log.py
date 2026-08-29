"""add admin_audit_log table

Revision ID: 0002_admin_audit_log
Revises: 0001_init
Create Date: 2026-08-29
"""
import sqlalchemy as sa
from alembic import op

revision = "0002_admin_audit_log"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_audit_log",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor", sa.String(128), nullable=False, index=True),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("table_name", sa.String(128), nullable=False, index=True),
        sa.Column("record_id", sa.String(128), nullable=True),
        sa.Column("before", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("after", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, index=True),
    )


def downgrade():
    op.drop_table("admin_audit_log")
