"""compressor_air_extended

Adds operational detail columns to compressor_records:
  - Period totals (air_generated_nm3, air_unit, electricity_used_kwh)
  - Time breakdown (period_hours, runtime_hours, load_time_hours,
                    unload_time_hours, idle_time_hours)
  - Dryer tracking (dryer_status, dryer_dew_point_c)
  - Pressure points (receiver_tank_pressure_bar, line_pressure_bar)
  - Leak testing (leak_test_done, leak_estimation_pct, leak_volume_nm3)
  - Night/non-production (night_idle_kwh, night_idle_nm3)
  - Flags (maintenance_flag, department, start_stop_count, downtime_minutes,
           downtime_reason, running_hours_cumulative_delta)

Revision ID: b7c8d9e0f1a2
Revises:     a2b3c4d5e6f7
"""
from alembic import op
import sqlalchemy as sa

revision       = "b7c8d9e0f1a2"
down_revision  = "a2b3c4d5e6f7"
branch_labels  = None
depends_on     = None


def upgrade() -> None:
    # ── Period totals ──────────────────────────────────────────────────────────
    op.add_column("compressor_records", sa.Column("air_generated_nm3",    sa.Numeric(14, 3),  nullable=True))
    op.add_column("compressor_records", sa.Column("air_unit",             sa.String(20),      nullable=True, server_default="Nm3"))
    op.add_column("compressor_records", sa.Column("electricity_used_kwh", sa.Numeric(14, 4),  nullable=True))

    # ── Time breakdown ─────────────────────────────────────────────────────────
    op.add_column("compressor_records", sa.Column("period_hours",         sa.Numeric(8, 2),   nullable=True))
    op.add_column("compressor_records", sa.Column("runtime_hours",        sa.Numeric(10, 3),  nullable=True))
    op.add_column("compressor_records", sa.Column("load_time_hours",      sa.Numeric(10, 3),  nullable=True))
    op.add_column("compressor_records", sa.Column("unload_time_hours",    sa.Numeric(10, 3),  nullable=True))
    op.add_column("compressor_records", sa.Column("idle_time_hours",      sa.Numeric(10, 3),  nullable=True))

    # ── Dryer ──────────────────────────────────────────────────────────────────
    op.add_column("compressor_records", sa.Column("dryer_status",         sa.String(30),      nullable=True))
    op.add_column("compressor_records", sa.Column("dryer_dew_point_c",    sa.Numeric(8, 2),   nullable=True))

    # ── Pressure points ────────────────────────────────────────────────────────
    op.add_column("compressor_records", sa.Column("receiver_tank_pressure_bar", sa.Numeric(8, 3), nullable=True))
    op.add_column("compressor_records", sa.Column("line_pressure_bar",    sa.Numeric(8, 3),   nullable=True))

    # ── Leak testing ───────────────────────────────────────────────────────────
    op.add_column("compressor_records", sa.Column("leak_test_done",       sa.Boolean(),       nullable=False, server_default=sa.false()))
    op.add_column("compressor_records", sa.Column("leak_estimation_pct",  sa.Numeric(7, 3),   nullable=True))
    op.add_column("compressor_records", sa.Column("leak_volume_nm3",      sa.Numeric(14, 3),  nullable=True))

    # ── Night / non-production ─────────────────────────────────────────────────
    op.add_column("compressor_records", sa.Column("night_idle_kwh",       sa.Numeric(14, 4),  nullable=True))
    op.add_column("compressor_records", sa.Column("night_idle_nm3",       sa.Numeric(14, 3),  nullable=True))

    # ── Operational flags ──────────────────────────────────────────────────────
    op.add_column("compressor_records", sa.Column("maintenance_flag",     sa.Boolean(),       nullable=False, server_default=sa.false()))
    op.add_column("compressor_records", sa.Column("department",           sa.String(100),     nullable=True))
    op.add_column("compressor_records", sa.Column("start_stop_count",     sa.Integer(),       nullable=True))
    op.add_column("compressor_records", sa.Column("downtime_minutes",     sa.Integer(),       nullable=True))
    op.add_column("compressor_records", sa.Column("downtime_reason",      sa.Text(),          nullable=True))
    op.add_column("compressor_records", sa.Column("production_line",      sa.String(100),     nullable=True))

    op.create_index("ix_compressor_department", "compressor_records", ["department"])
    op.create_index("ix_compressor_leak_test",  "compressor_records", ["leak_test_done"])


def downgrade() -> None:
    op.drop_index("ix_compressor_leak_test",  table_name="compressor_records")
    op.drop_index("ix_compressor_department", table_name="compressor_records")

    for col in [
        "air_generated_nm3", "air_unit", "electricity_used_kwh",
        "period_hours", "runtime_hours", "load_time_hours",
        "unload_time_hours", "idle_time_hours",
        "dryer_status", "dryer_dew_point_c",
        "receiver_tank_pressure_bar", "line_pressure_bar",
        "leak_test_done", "leak_estimation_pct", "leak_volume_nm3",
        "night_idle_kwh", "night_idle_nm3",
        "maintenance_flag", "department", "start_stop_count",
        "downtime_minutes", "downtime_reason", "production_line",
    ]:
        op.drop_column("compressor_records", col)
