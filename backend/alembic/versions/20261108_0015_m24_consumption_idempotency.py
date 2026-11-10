"""Add an idempotency key to actual material consumption events."""

from alembic import op
import sqlalchemy as sa


revision = "20261108_0015"
down_revision = "20261108_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "production_consumptions",
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
    )
    op.create_index(
        "ix_production_consumptions_idempotency_key",
        "production_consumptions",
        ["idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_production_consumptions_idempotency_key",
        table_name="production_consumptions",
    )
    op.drop_column("production_consumptions", "idempotency_key")
