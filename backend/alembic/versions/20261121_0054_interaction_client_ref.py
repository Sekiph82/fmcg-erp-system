"""M36.S03.T003 mobile quick notes: idempotency key so a phone retry never creates a second note."""

from alembic import op

revision = "20261121_0054"
down_revision = "20261121_0053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE mkt_customer_interactions ADD COLUMN IF NOT EXISTS client_ref VARCHAR(64)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_mkt_customer_interactions_client_ref ON mkt_customer_interactions (client_ref)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_mkt_customer_interactions_client_ref")
    op.execute("ALTER TABLE mkt_customer_interactions DROP COLUMN IF EXISTS client_ref")
