"""Link production scrap events to their issue line and scrap flow line."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261108_0017"
down_revision = "20261108_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "production_consumptions",
        sa.Column("scrap_flow_line_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "production_consumptions",
        sa.Column("scrap_reason_code", sa.String(length=40), nullable=True),
    )
    op.create_foreign_key(
        "fk_production_consumptions_scrap_flow_line",
        "production_consumptions",
        "material_flow_lines",
        ["scrap_flow_line_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_production_consumptions_scrap_flow_line_id",
        "production_consumptions",
        ["scrap_flow_line_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_production_consumptions_scrap_flow_line_id",
        table_name="production_consumptions",
    )
    op.drop_constraint(
        "fk_production_consumptions_scrap_flow_line",
        "production_consumptions",
        type_="foreignkey",
    )
    op.drop_column("production_consumptions", "scrap_reason_code")
    op.drop_column("production_consumptions", "scrap_flow_line_id")
