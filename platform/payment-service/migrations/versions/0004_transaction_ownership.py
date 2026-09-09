"""Add tenant-safe transaction ownership and wallet uniqueness.

Revision ID: 0004
Revises: 0003_webhook_events
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_transaction_ownership"
down_revision = "0003_webhook_events"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS user_id VARCHAR(64)"))
    op.execute(sa.text("UPDATE transactions t SET user_id = w.user_id FROM wallets w WHERE t.wallet_id = w.id AND t.user_id IS NULL"))
    op.execute(sa.text("DO $$ BEGIN IF EXISTS (SELECT 1 FROM transactions WHERE user_id IS NULL) THEN RAISE EXCEPTION 'transactions.user_id could not be backfilled'; END IF; END $$;"))
    op.execute(sa.text("ALTER TABLE transactions ALTER COLUMN user_id SET NOT NULL"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_transactions_user_id ON transactions (user_id)"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_wallet_user_currency"))
    op.execute(sa.text("CREATE UNIQUE INDEX IF NOT EXISTS ix_wallet_tenant_user_currency ON wallets (tenant_id, user_id, currency)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_tx_external_method ON transactions (external_id, method)"))


def downgrade():
    op.execute(sa.text("DROP INDEX IF EXISTS ix_tx_external_method"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_wallet_tenant_user_currency"))
    op.execute(sa.text("CREATE UNIQUE INDEX IF NOT EXISTS ix_wallet_user_currency ON wallets (user_id, currency)"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_transactions_user_id"))
    op.execute(sa.text("ALTER TABLE transactions DROP COLUMN IF EXISTS user_id"))
