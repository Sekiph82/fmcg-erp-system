"""M36.S01.T005 meeting scheduling: booking time zone, iCalendar sequence, personal calendar feeds."""

import sqlalchemy as sa
from alembic import op

revision = "20261121_0050"
down_revision = "20261121_0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = {c["name"] for c in sa.inspect(bind).get_columns("meeting_records")}
    if "time_zone" not in existing:
        op.add_column("meeting_records", sa.Column("time_zone", sa.String(64), nullable=True))
    if "sequence" not in existing:
        op.add_column("meeting_records", sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"))
    op.execute("CREATE INDEX IF NOT EXISTS ix_meeting_records_host_time ON meeting_records (host_id, scheduled_at)")
    from app.models.meetings import MeetingCalendarFeed  # fresh databases get it from the model-based baseline

    MeetingCalendarFeed.__table__.create(bind, checkfirst=True)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS meeting_calendar_feeds")
    op.execute("DROP INDEX IF EXISTS ix_meeting_records_host_time")
    op.drop_column("meeting_records", "sequence")
    op.drop_column("meeting_records", "time_zone")
