"""Use database sequences for globally unique MPS plan and line numbers."""

from alembic import op


revision = "20261022_0011"
down_revision = "20261021_0010"
branch_labels = None
depends_on = None


def _create_sequence(name: str, table: str, column: str, prefix: str) -> None:
    op.execute(f"CREATE SEQUENCE {name} AS BIGINT MINVALUE 1 START WITH 1")
    op.execute(
        f"""
        WITH current_max AS (
            SELECT MAX(substring({column} FROM '^{prefix}([0-9]+)$')::BIGINT) AS value
            FROM {table}
            WHERE {column} ~ '^{prefix}[0-9]+$'
        )
        SELECT setval(
            '{name}',
            GREATEST(COALESCE(value, 0), 1),
            COALESCE(value, 0) >= 1
        )
        FROM current_max
        """
    )


def upgrade() -> None:
    # Prevent concurrent legacy count-based allocators from inserting numbers
    # while each sequence is initialized. Deploy with old MPS and what-if
    # writers quiesced until all sequence-backed code is active.
    op.execute("LOCK TABLE mps_plans IN ACCESS EXCLUSIVE MODE")
    op.execute("LOCK TABLE mps_lines IN ACCESS EXCLUSIVE MODE")
    op.execute("LOCK TABLE mps_whatif_scenarios IN ACCESS EXCLUSIVE MODE")
    _create_sequence("mps_plan_no_seq", "mps_plans", "plan_no", "MPS-")
    _create_sequence("mps_line_no_seq", "mps_lines", "line_no", "MPSL-")
    _create_sequence(
        "mps_whatif_scenario_no_seq",
        "mps_whatif_scenarios",
        "scenario_no",
        r"WI-[0-9A-Fa-f]{6}-",
    )


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS mps_whatif_scenario_no_seq")
    op.execute("DROP SEQUENCE IF EXISTS mps_line_no_seq")
    op.execute("DROP SEQUENCE IF EXISTS mps_plan_no_seq")
