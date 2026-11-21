"""M36.S05.T002 review: keyed connection hash on landing events for the per-connection view limit."""

from alembic import op

revision = "20261121_0066"
down_revision = "20261121_0065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE crm_landing_events ADD COLUMN IF NOT EXISTS ip_hash VARCHAR(64)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_crm_landing_events_ip ON crm_landing_events (ip_hash, created_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_crm_landing_events_ip")
    op.execute("ALTER TABLE crm_landing_events DROP COLUMN IF EXISTS ip_hash")
