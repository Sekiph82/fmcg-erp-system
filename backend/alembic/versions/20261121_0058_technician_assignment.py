"""M40.S01.T002 technician work: assignee user on PM work orders and breakdowns, completion photos."""

from alembic import op

revision = "20261121_0058"
down_revision = "20261121_0057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table, col in (("pm_work_orders", "technician_id"), ("breakdown_records", "assigned_to_id")):
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} UUID REFERENCES users(id) ON DELETE SET NULL")
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{table}_{col} ON {table} ({col})")
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS photo_keys TEXT")


def downgrade() -> None:
    for table, col in (("pm_work_orders", "technician_id"), ("breakdown_records", "assigned_to_id")):
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_{col}")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS photo_keys")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {col}")
