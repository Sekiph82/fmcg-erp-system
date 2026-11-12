"""M36.S01.T004 automation rule activation time and enqueue watermark on cf_workflow_rules."""

from alembic import op
import sqlalchemy as sa

revision = "20261112_0039"
down_revision = "20261112_0038"
branch_labels = None
depends_on = None

COLUMNS = ("activated_at", "enqueued_until")


def upgrade() -> None:
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("cf_workflow_rules")}
    for name in COLUMNS:  # fresh databases get them from the model-based baseline
        if name not in existing:
            op.add_column("cf_workflow_rules", sa.Column(name, sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("cf_workflow_rules")}
    for name in COLUMNS:
        if name in existing:
            op.drop_column("cf_workflow_rules", name)
