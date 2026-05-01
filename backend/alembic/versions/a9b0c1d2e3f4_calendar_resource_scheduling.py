"""calendar_resource_scheduling

Revision ID: a9b0c1d2e3f4
Revises: f8a9b0c1d2e3
Create Date: 2026-05-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'a9b0c1d2e3f4'
down_revision = 'f8a9b0c1d2e3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'calendar_resources',
        sa.Column('resource_id', sa.String(36), primary_key=True),
        sa.Column('resource_type', sa.String(20), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('capacity', sa.Integer(), default=1),
        sa.Column('location', sa.String(200)),
        sa.Column('description', sa.Text()),
        sa.Column('availability_rules', sa.JSON()),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    op.create_table(
        'cal_recurrence_rules',
        sa.Column('recurrence_id', sa.String(36), primary_key=True),
        sa.Column('frequency', sa.String(20), nullable=False),
        sa.Column('interval', sa.Integer(), default=1),
        sa.Column('end_date', sa.DateTime()),
        sa.Column('max_occurrences', sa.Integer()),
        sa.Column('days_of_week', sa.JSON()),
        sa.Column('exceptions', sa.JSON()),
        sa.Column('created_at', sa.DateTime()),
    )

    op.create_table(
        'calendar_events',
        sa.Column('event_id', sa.String(36), primary_key=True),
        sa.Column('event_title', sa.String(300), nullable=False),
        sa.Column('event_type', sa.String(20), default='meeting'),
        sa.Column('start_datetime', sa.DateTime(), nullable=False),
        sa.Column('end_datetime', sa.DateTime(), nullable=False),
        sa.Column('all_day_flag', sa.Boolean(), default=False),
        sa.Column('created_by', sa.String(100)),
        sa.Column('description', sa.Text()),
        sa.Column('location', sa.String(200)),
        sa.Column('status', sa.String(20), default='scheduled'),
        sa.Column('source_module', sa.String(50)),
        sa.Column('source_ref_id', sa.String(36)),
        sa.Column('recurrence_id', sa.String(36),
                  sa.ForeignKey('cal_recurrence_rules.recurrence_id')),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )
    op.create_index('ix_calendar_events_start', 'calendar_events', ['start_datetime'])
    op.create_index('ix_calendar_events_end', 'calendar_events', ['end_datetime'])

    op.create_table(
        'cal_event_participants',
        sa.Column('participant_id', sa.String(36), primary_key=True),
        sa.Column('event_id', sa.String(36),
                  sa.ForeignKey('calendar_events.event_id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('user_id', sa.String(36)),
        sa.Column('participant_name', sa.String(200)),
        sa.Column('participant_email', sa.String(200)),
        sa.Column('role', sa.String(20), default='attendee'),
        sa.Column('response_status', sa.String(20), default='pending'),
    )
    op.create_index('ix_cal_participants_event', 'cal_event_participants', ['event_id'])

    op.create_table(
        'cal_resource_bookings',
        sa.Column('booking_id', sa.String(36), primary_key=True),
        sa.Column('event_id', sa.String(36),
                  sa.ForeignKey('calendar_events.event_id', ondelete='SET NULL')),
        sa.Column('resource_id', sa.String(36),
                  sa.ForeignKey('calendar_resources.resource_id'), nullable=False),
        sa.Column('start_datetime', sa.DateTime(), nullable=False),
        sa.Column('end_datetime', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(20), default='reserved'),
        sa.Column('notes', sa.Text()),
        sa.Column('booked_by', sa.String(100)),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_cal_bookings_resource', 'cal_resource_bookings', ['resource_id'])
    op.create_index('ix_cal_bookings_start', 'cal_resource_bookings', ['start_datetime'])

    op.create_table(
        'cal_ai_recommendations',
        sa.Column('rec_id', sa.String(36), primary_key=True),
        sa.Column('agent_type', sa.String(30), nullable=False),
        sa.Column('title', sa.String(300)),
        sa.Column('body', sa.Text()),
        sa.Column('score', sa.Float()),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('rec_metadata', sa.JSON()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )


def downgrade():
    op.drop_table('cal_ai_recommendations')
    op.drop_index('ix_cal_bookings_start', 'cal_resource_bookings')
    op.drop_index('ix_cal_bookings_resource', 'cal_resource_bookings')
    op.drop_table('cal_resource_bookings')
    op.drop_index('ix_cal_participants_event', 'cal_event_participants')
    op.drop_table('cal_event_participants')
    op.drop_index('ix_calendar_events_end', 'calendar_events')
    op.drop_index('ix_calendar_events_start', 'calendar_events')
    op.drop_table('calendar_events')
    op.drop_table('cal_recurrence_rules')
    op.drop_table('calendar_resources')
