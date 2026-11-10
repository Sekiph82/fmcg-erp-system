"""Add source and staging locations to material reservation lines.

Revision ID: 20261108_0013
Revises: 20261104_0012
Create Date: 2026-11-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261108_0013"
down_revision = "20261104_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "material_reservation_lines",
        sa.Column("source_location_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "material_reservation_lines",
        sa.Column("staging_location_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_reservation_line_source_location",
        "material_reservation_lines",
        "storage_locations",
        ["source_location_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_reservation_line_staging_location",
        "material_reservation_lines",
        "storage_locations",
        ["staging_location_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_reservation_line_staging_location",
        "material_reservation_lines",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_reservation_line_source_location",
        "material_reservation_lines",
        type_="foreignkey",
    )
    op.drop_column("material_reservation_lines", "staging_location_id")
    op.drop_column("material_reservation_lines", "source_location_id")
