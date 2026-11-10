"""Recalculate stored OEE components from recorded source facts.

The migration updates derived KPI columns only. Planned time, actual runtime,
downtime, ideal cycle time, and unit counts remain unchanged.
"""

from alembic import op
import sqlalchemy as sa


revision = "20261108_0024"
down_revision = "20261108_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "oee_records" not in sa.inspect(bind).get_table_names():
        return

    op.execute(
        sa.text(
            """
            WITH source AS (
                SELECT
                    id,
                    planned_production_time_min::numeric AS planned_min,
                    COALESCE(downtime_min, 0)::numeric AS downtime_min,
                    CASE
                        WHEN actual_production_time_min IS NOT NULL
                        THEN LEAST(
                            GREATEST(actual_production_time_min::numeric, 0),
                            GREATEST(
                                planned_production_time_min::numeric - COALESCE(downtime_min, 0)::numeric,
                                0
                            )
                        )
                    END AS effective_run_min,
                    CASE WHEN actual_production_time_min IS NOT NULL THEN LEAST(
                        GREATEST(actual_production_time_min::numeric, 0),
                        GREATEST(
                            planned_production_time_min::numeric - COALESCE(downtime_min, 0)::numeric,
                            0
                        )
                    ) END AS actual_run_min,
                    ideal_cycle_time_sec::numeric AS ideal_cycle_sec,
                    total_units_produced::numeric AS total_units,
                    good_units_produced::numeric AS good_units,
                    actual_production_time_min IS NOT NULL AND actual_production_time_min >= 0 AS actual_time_valid
                FROM oee_records
            ), components AS (
                SELECT
                    id,
                    CASE
                        WHEN planned_min > 0 AND downtime_min >= 0 AND actual_time_valid
                        THEN ROUND(LEAST(GREATEST(effective_run_min / planned_min, 0), 1), 4)
                    END AS availability,
                    CASE
                        WHEN planned_min >= 0 AND downtime_min >= 0 AND actual_time_valid AND actual_run_min > 0
                            AND ideal_cycle_sec > 0 AND total_units >= 0
                        THEN ROUND(
                            LEAST(GREATEST(total_units * ideal_cycle_sec / (actual_run_min * 60), 0), 1),
                            4
                        )
                    END AS performance,
                    CASE
                        WHEN total_units > 0 AND good_units >= 0 AND good_units <= total_units
                        THEN ROUND(good_units / total_units, 4)
                    END AS quality,
                    CASE
                        WHEN planned_min > 0 AND downtime_min >= 0
                        THEN downtime_min / planned_min > 0.20
                        ELSE FALSE
                    END AS is_high_downtime
                FROM source
            ), result AS (
                SELECT
                    id,
                    availability,
                    performance,
                    quality,
                    CASE
                        WHEN availability IS NOT NULL
                            AND performance IS NOT NULL
                            AND quality IS NOT NULL
                        THEN ROUND(availability * performance * quality, 4)
                    END AS oee_score,
                    is_high_downtime
                FROM components
            )
            UPDATE oee_records AS record
            SET availability = result.availability,
                performance = result.performance,
                quality = result.quality,
                oee_score = result.oee_score,
                is_low_oee = result.oee_score IS NOT NULL AND result.oee_score < 0.65,
                is_high_downtime = result.is_high_downtime
            FROM result
            WHERE record.id = result.id
            """
        )
    )

    if "machine_performance_snapshots" not in sa.inspect(bind).get_table_names():
        return

    op.execute(
        sa.text(
            """
            WITH source AS (
                SELECT
                    id,
                    planned_time_min::numeric AS planned_min,
                    downtime_min::numeric AS downtime_min,
                    run_time_min::numeric AS run_min,
                    CASE
                        WHEN planned_time_min > 0 AND downtime_min >= 0
                        THEN LEAST(
                            GREATEST(run_time_min::numeric, 0),
                            GREATEST(planned_time_min::numeric - downtime_min::numeric, 0)
                        )
                        ELSE GREATEST(run_time_min::numeric, 0)
                    END AS effective_run_min,
                    rated_speed::numeric AS rated_speed,
                    units_produced::numeric AS total_units,
                    good_units::numeric AS good_units
                FROM machine_performance_snapshots
            ), components AS (
                SELECT
                    id,
                    CASE
                        WHEN planned_min > 0 AND downtime_min >= 0 AND run_min >= 0
                        THEN ROUND(LEAST(GREATEST(effective_run_min / planned_min, 0), 1), 4)
                    END AS availability,
                    CASE
                        WHEN run_min >= 0 AND effective_run_min > 0
                            AND rated_speed > 0 AND total_units >= 0
                        THEN ROUND(
                            LEAST(GREATEST(total_units * 60 / (rated_speed * effective_run_min), 0), 1),
                            4
                        )
                    END AS performance,
                    CASE
                        WHEN total_units > 0 AND good_units >= 0 AND good_units <= total_units
                        THEN ROUND(good_units / total_units, 4)
                    END AS quality,
                    CASE
                        WHEN planned_min > 0 AND downtime_min >= 0
                        THEN downtime_min / planned_min > 0.20
                        ELSE FALSE
                    END AS high_downtime
                FROM source
            ), result AS (
                SELECT
                    id,
                    availability,
                    performance,
                    quality,
                    CASE
                        WHEN availability IS NOT NULL
                            AND performance IS NOT NULL
                            AND quality IS NOT NULL
                        THEN ROUND(availability * performance * quality, 4)
                    END AS oee,
                    high_downtime
                FROM components
            )
            UPDATE machine_performance_snapshots AS snapshot
            SET availability = result.availability,
                performance = result.performance,
                quality_rate = result.quality,
                oee = result.oee,
                low_oee_flag = result.oee IS NOT NULL AND result.oee < 0.65,
                high_downtime_flag = result.high_downtime,
                anomaly_flag = (result.oee IS NOT NULL AND result.oee < 0.65) OR result.high_downtime
            FROM result
            WHERE snapshot.id = result.id
            """
        )
    )

def downgrade() -> None:
    # This is a derived-data correction. The original values cannot be
    # reconstructed without a snapshot, and source production facts are intact.
    pass
