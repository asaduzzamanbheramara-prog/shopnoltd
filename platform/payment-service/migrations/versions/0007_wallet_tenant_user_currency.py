"""Repair tenant-scoped wallet uniqueness for databases already at 0006.

Revision ID: 0007_wallet_tenant_user_currency
Revises: 0006_payment_accounts

This is a forward-only schema reconciliation. Revision 0004 was already applied
on existing installations, so editing 0004 alone cannot repair those databases.
The invariant at 0006 is a unique index on (tenant_id, user_id, currency).
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_wallet_tenant_user_currency"
down_revision = "0006_payment_accounts"
branch_labels = None
depends_on = None


def upgrade():
    # Fail before changing constraints if the live data cannot satisfy the
    # intended tenant-scoped uniqueness rule. No wallet rows are rewritten.
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM public.wallets
                    GROUP BY tenant_id, user_id, currency
                    HAVING COUNT(*) > 1
                ) THEN
                    RAISE EXCEPTION
                        'wallets contains duplicate tenant/user/currency keys; refusing uniqueness repair';
                END IF;
            END
            $$;
            """
        )
    )

    # If an index with the desired name already exists, verify that it is the
    # correct UNIQUE index instead of silently accepting a conflicting object.
    op.execute(
        sa.text(
            """
            DO $$
            DECLARE
                existing_definition text;
            BEGIN
                SELECT pg_get_indexdef(i.indexrelid)
                  INTO existing_definition
                  FROM pg_index i
                  JOIN pg_class c ON c.oid = i.indexrelid
                  JOIN pg_namespace n ON n.oid = c.relnamespace
                 WHERE n.nspname = 'public'
                   AND c.relname = 'ix_wallet_tenant_user_currency';

                IF existing_definition IS NOT NULL
                   AND (
                       existing_definition NOT LIKE 'CREATE UNIQUE INDEX%'
                       OR existing_definition NOT LIKE '%(tenant_id, user_id, currency)%'
                   ) THEN
                    RAISE EXCEPTION
                        'ix_wallet_tenant_user_currency exists with an unexpected definition; refusing repair';
                END IF;
            END
            $$;
            """
        )
    )

    op.execute(
        sa.text(
            "ALTER TABLE public.wallets "
            "DROP CONSTRAINT IF EXISTS ix_wallet_user_currency"
        )
    )
    op.execute(sa.text("DROP INDEX IF EXISTS public.ix_wallet_user_currency"))
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_wallet_tenant_user_currency "
            "ON public.wallets (tenant_id, user_id, currency)"
        )
    )


def downgrade():
    # Intentionally preserve the corrected 0006 schema invariant. Removing
    # this repair would reintroduce a known schema drift; downgrading further
    # through 0004 still removes the tenant index and restores the legacy key.
    pass
