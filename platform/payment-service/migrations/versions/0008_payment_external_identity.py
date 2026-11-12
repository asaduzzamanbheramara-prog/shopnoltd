"""Remove legacy local-user foreign keys from external JWT subject columns.

Revision ID: 0008_payment_external_identity
Revises: 0007_wallet_tenant_user_currency

Payment rows store the verified Keycloak JWT subject (sub). The OAuth user
mirror's internal users.id is a separate identifier in another database.
Ownership is enforced by authenticated tenant-scoped application queries;
PostgreSQL cannot enforce a cross-database foreign key.
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_payment_external_identity"
down_revision = "0007_wallet_tenant_user_currency"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("wallets", "transactions", "wallet_ledger_entries", "payment_methods"):
        op.execute(
            sa.text(
                f"ALTER TABLE public.{table} "
                f"DROP CONSTRAINT IF EXISTS {table}_user_id_fkey"
            )
        )


def downgrade():
    # A FK to OAuth users.id would be incorrect: payment user_id stores the
    # Keycloak subject and the OAuth database is a separate PostgreSQL database.
    # Recreating that invalid relationship would make valid payment writes fail.
    pass
