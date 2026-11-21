"""M40.S01.T002 review: jobs assigned by name get the user id when exactly one active user has that name."""

from alembic import op

revision = "20261121_0061"
down_revision = "20261121_0060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE pm_work_orders w SET technician_id = u.id
        FROM users u
        WHERE w.technician_id IS NULL AND w.technician IS NOT NULL AND u.is_active
          AND lower(u.full_name) = lower(w.technician)
          AND (SELECT count(*) FROM users x WHERE x.is_active AND lower(x.full_name) = lower(w.technician)) = 1
    """)


def downgrade() -> None:
    pass
