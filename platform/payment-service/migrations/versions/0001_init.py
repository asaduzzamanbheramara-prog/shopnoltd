"""initial schema
Revision ID: 0001
"""
from alembic import op
import sqlalchemy as sa
revision = "0001"; down_revision = None; branch_labels = None; depends_on = None
def upgrade():
    op.create_table("wallets", sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("tenant_id", sa.String(64), nullable=False, index=True), sa.Column("user_id", sa.String(64), nullable=False), sa.Column("currency", sa.String(8), nullable=False), sa.Column("balance", sa.Numeric(20, 8), server_default="0"), sa.Column("frozen", sa.Numeric(20, 8), server_default="0"), sa.Column("created_at", sa.DateTime), sa.Column("updated_at", sa.DateTime), sa.UniqueConstraint("user_id", "currency", name="ix_wallet_user_currency"))
    op.create_table("transactions", sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("tenant_id", sa.String(64), nullable=False, index=True), sa.Column("wallet_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("wallets.id")), sa.Column("type", sa.String(16)), sa.Column("method", sa.String(16)), sa.Column("status", sa.String(16)), sa.Column("amount", sa.Numeric(20, 8)), sa.Column("fee", sa.Numeric(20, 8), server_default="0"), sa.Column("currency", sa.String(8)), sa.Column("external_id", sa.String(128), index=True), sa.Column("reference", sa.String(128)), sa.Column("meta", sa.dialects.postgresql.JSONB), sa.Column("approved_by", sa.String(64)), sa.Column("created_at", sa.DateTime, index=True), sa.Column("completed_at", sa.DateTime))
def downgrade(): op.drop_table("transactions"); op.drop_table("wallets")

