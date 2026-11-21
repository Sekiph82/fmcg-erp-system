"""M40.S01.T001 customer feedback: one-time NPS links; loyalty points once per paid invoice."""

from alembic import op

revision = "20261121_0057"
down_revision = "20261121_0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS nps_survey_links (
            id UUID PRIMARY KEY,
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            survey_id UUID NOT NULL REFERENCES nps_surveys(id) ON DELETE CASCADE,
            customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
            so_id UUID REFERENCES sales_orders(id) ON DELETE SET NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            used_at TIMESTAMPTZ,
            created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_nps_survey_links_customer_id ON nps_survey_links (customer_id)")
    # a paid invoice earns points once, even under concurrent payments
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_loyalty_txn_invoice_once ON loyalty_transactions (account_id, reference_id) "
               "WHERE reference_type = 'INVOICE'")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_loyalty_txn_invoice_once")
    op.execute("DROP TABLE IF EXISTS nps_survey_links")
