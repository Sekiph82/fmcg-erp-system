"""Link a production return event to its posted return flow line."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261108_0016"
down_revision = "20261108_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "production_consumptions",
        sa.Column("return_flow_line_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_production_consumptions_return_flow_line",
        "production_consumptions",
        "material_flow_lines",
        ["return_flow_line_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_production_consumptions_return_flow_line_id",
        "production_consumptions",
        ["return_flow_line_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_production_consumptions_return_flow_line_id",
        table_name="production_consumptions",
    )
    op.drop_constraint(
        "fk_production_consumptions_return_flow_line",
        "production_consumptions",
        type_="foreignkey",
    )
    op.drop_column("production_consumptions", "return_flow_line_id")
