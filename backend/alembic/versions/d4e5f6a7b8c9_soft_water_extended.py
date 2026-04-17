"""
Extend soft_water_records with additional operational columns.

Adds:
  raw_water_input_m3      – raw water volume fed into the softener (for balance)
  regen_start             – regeneration cycle start timestamp
  regen_end               – regeneration cycle end timestamp
  conductivity_feed_uscm  – feed water conductivity (µS/cm)
  conductivity_product_uscm – product water conductivity (µS/cm)
  downtime_minutes        – downtime during the logged period
  maintenance_flag        – flag indicating maintenance required
  destination_tag         – where treated water is routed (e.g. Boiler Feed, CIP)
  department              – department assignment (for filtering)

Revision ID: d4e5f6a7b8c9
Revises: c2d3e4f5a0b1
"""
from alembic import op
import sqlalchemy as sa

revision    = "d4e5f6a7b8c9"
down_revision = "c2d3e4f5a0b1"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column("soft_water_records",
        sa.Column("raw_water_input_m3", sa.Numeric(14, 3), nullable=True))
    op.add_column("soft_water_records",
        sa.Column("regen_start", sa.DateTime(timezone=True), nullable=True))
    op.add_column("soft_water_records",
        sa.Column("regen_end", sa.DateTime(timezone=True), nullable=True))
    op.add_column("soft_water_records",
        sa.Column("conductivity_feed_uscm", sa.Numeric(10, 2), nullable=True))
    op.add_column("soft_water_records",
        sa.Column("conductivity_product_uscm", sa.Numeric(10, 2), nullable=True))
    op.add_column("soft_water_records",
        sa.Column("downtime_minutes", sa.Integer, nullable=True))
    op.add_column("soft_water_records",
        sa.Column("maintenance_flag", sa.Boolean, nullable=False, server_default="false"))
    op.add_column("soft_water_records",
        sa.Column("destination_tag", sa.String(100), nullable=True))
    op.add_column("soft_water_records",
        sa.Column("department", sa.String(100), nullable=True))
    op.create_index("ix_soft_water_dept", "soft_water_records", ["department"])


def downgrade() -> None:
    op.drop_index("ix_soft_water_dept", table_name="soft_water_records")
    op.drop_column("soft_water_records", "department")
    op.drop_column("soft_water_records", "destination_tag")
    op.drop_column("soft_water_records", "maintenance_flag")
    op.drop_column("soft_water_records", "downtime_minutes")
    op.drop_column("soft_water_records", "conductivity_product_uscm")
    op.drop_column("soft_water_records", "conductivity_feed_uscm")
    op.drop_column("soft_water_records", "regen_end")
    op.drop_column("soft_water_records", "regen_start")
    op.drop_column("soft_water_records", "raw_water_input_m3")
