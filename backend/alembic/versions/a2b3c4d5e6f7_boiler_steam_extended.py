"""
Extend boiler_steam_records with period-total and operational columns.

Adds:
  steam_generated_kg      – total steam produced in this log period (kg)
  feedwater_consumed_m3   – total feed water consumed in period (m³)
  condensate_returned_m3  – condensate return volume in period (m³)
  boiler_load_pct         – boiler operating load (%)
  burner_runtime_hours    – burner/firing time in period (hours)
  start_stop_count        – number of starts/stops in period
  chemical_dosing_amount  – chemical dosing quantity
  chemical_dosing_unit    – unit for dosing (kg, L, ppm)
  downtime_minutes        – downtime in this period
  downtime_reason         – reason for downtime
  department              – department for cost allocation
  period_hours            – hours covered by this log record

Revision ID: a2b3c4d5e6f7
Revises: d4e5f6a7b8c9
"""
from alembic import op
import sqlalchemy as sa

revision      = "a2b3c4d5e6f7"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column("boiler_steam_records",
        sa.Column("steam_generated_kg", sa.Numeric(14, 3), nullable=True))
    op.add_column("boiler_steam_records",
        sa.Column("feedwater_consumed_m3", sa.Numeric(14, 3), nullable=True))
    op.add_column("boiler_steam_records",
        sa.Column("condensate_returned_m3", sa.Numeric(14, 3), nullable=True))
    op.add_column("boiler_steam_records",
        sa.Column("boiler_load_pct", sa.Numeric(7, 3), nullable=True))
    op.add_column("boiler_steam_records",
        sa.Column("burner_runtime_hours", sa.Numeric(10, 3), nullable=True))
    op.add_column("boiler_steam_records",
        sa.Column("start_stop_count", sa.Integer, nullable=True))
    op.add_column("boiler_steam_records",
        sa.Column("chemical_dosing_amount", sa.Numeric(10, 4), nullable=True))
    op.add_column("boiler_steam_records",
        sa.Column("chemical_dosing_unit", sa.String(20), nullable=True))
    op.add_column("boiler_steam_records",
        sa.Column("downtime_minutes", sa.Integer, nullable=True))
    op.add_column("boiler_steam_records",
        sa.Column("downtime_reason", sa.Text, nullable=True))
    op.add_column("boiler_steam_records",
        sa.Column("department", sa.String(100), nullable=True))
    op.add_column("boiler_steam_records",
        sa.Column("period_hours", sa.Numeric(8, 2), nullable=True))
    op.add_column("boiler_steam_records",
        sa.Column("maintenance_flag", sa.Boolean, nullable=False, server_default="false"))

    op.create_index("ix_boiler_dept", "boiler_steam_records", ["department"])
    op.create_index("ix_boiler_status", "boiler_steam_records", ["status"])


def downgrade() -> None:
    op.drop_index("ix_boiler_status", table_name="boiler_steam_records")
    op.drop_index("ix_boiler_dept", table_name="boiler_steam_records")
    op.drop_column("boiler_steam_records", "maintenance_flag")
    op.drop_column("boiler_steam_records", "period_hours")
    op.drop_column("boiler_steam_records", "department")
    op.drop_column("boiler_steam_records", "downtime_reason")
    op.drop_column("boiler_steam_records", "downtime_minutes")
    op.drop_column("boiler_steam_records", "chemical_dosing_unit")
    op.drop_column("boiler_steam_records", "chemical_dosing_amount")
    op.drop_column("boiler_steam_records", "start_stop_count")
    op.drop_column("boiler_steam_records", "burner_runtime_hours")
    op.drop_column("boiler_steam_records", "boiler_load_pct")
    op.drop_column("boiler_steam_records", "condensate_returned_m3")
    op.drop_column("boiler_steam_records", "feedwater_consumed_m3")
    op.drop_column("boiler_steam_records", "steam_generated_kg")
