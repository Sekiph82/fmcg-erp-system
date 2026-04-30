"""notification_center

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-05-01 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'd6e7f8a9b0c1'
down_revision = 'c5d6e7f8a9b0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'nc_notifications',
        sa.Column('notification_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('user_name', sa.String(200), nullable=True),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('notification_type', sa.Enum(
            'info', 'warning', 'error', 'approval_required', 'task_assigned',
            'reminder', 'system_alert', 'announcement',
            name='notificationtype'
        ), nullable=False),
        sa.Column('priority', sa.Enum('low', 'normal', 'high', 'critical', name='notificationpriority'), nullable=False),
        sa.Column('channel', sa.Enum('in_app', 'email', 'sms', 'whatsapp', name='notificationchannel'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'sent', 'failed', 'read', name='notificationstatus'), nullable=False),
        sa.Column('reference_type', sa.String(100), nullable=True),
        sa.Column('reference_id', sa.String(200), nullable=True),
        sa.Column('module', sa.String(100), nullable=True),
        sa.Column('read_flag', sa.Boolean(), nullable=True),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('scheduled_for', sa.DateTime(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('notification_id'),
    )
    op.create_index('ix_nc_notifications_user_id', 'nc_notifications', ['user_id'])
    op.create_index('ix_nc_notifications_read_flag', 'nc_notifications', ['read_flag'])
    op.create_index('ix_nc_notifications_created_at', 'nc_notifications', ['created_at'])

    op.create_table(
        'nc_notification_preferences',
        sa.Column('preference_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('notification_type', sa.Enum(
            'info', 'warning', 'error', 'approval_required', 'task_assigned',
            'reminder', 'system_alert', 'announcement',
            name='notificationtype'
        ), nullable=False),
        sa.Column('channel', sa.Enum('in_app', 'email', 'sms', 'whatsapp', name='notificationchannel'), nullable=False),
        sa.Column('enabled_flag', sa.Boolean(), nullable=True),
        sa.Column('muted_until', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('preference_id'),
        sa.UniqueConstraint('user_id', 'notification_type', 'channel', name='uq_nc_pref_user_type_channel'),
    )

    op.create_table(
        'nc_notification_templates',
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_code', sa.String(100), nullable=False),
        sa.Column('template_name', sa.String(200), nullable=False),
        sa.Column('notification_type', sa.Enum(
            'info', 'warning', 'error', 'approval_required', 'task_assigned',
            'reminder', 'system_alert', 'announcement',
            name='notificationtype'
        ), nullable=False),
        sa.Column('channel', sa.Enum('in_app', 'email', 'sms', 'whatsapp', name='notificationchannel'), nullable=False),
        sa.Column('title_template', sa.String(300), nullable=False),
        sa.Column('message_template', sa.Text(), nullable=False),
        sa.Column('language', sa.String(10), nullable=True),
        sa.Column('active_flag', sa.Boolean(), nullable=True),
        sa.Column('module', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('template_id'),
        sa.UniqueConstraint('template_code'),
    )

    op.create_table(
        'nc_notification_schedules',
        sa.Column('schedule_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('notification_type', sa.Enum(
            'info', 'warning', 'error', 'approval_required', 'task_assigned',
            'reminder', 'system_alert', 'announcement',
            name='notificationtype'
        ), nullable=False),
        sa.Column('channel', sa.Enum('in_app', 'email', 'sms', 'whatsapp', name='notificationchannel'), nullable=False),
        sa.Column('scheduled_for', sa.DateTime(), nullable=False),
        sa.Column('recurring', sa.Boolean(), nullable=True),
        sa.Column('recurrence_days', sa.Integer(), nullable=True),
        sa.Column('reference_type', sa.String(100), nullable=True),
        sa.Column('reference_id', sa.String(200), nullable=True),
        sa.Column('active_flag', sa.Boolean(), nullable=True),
        sa.Column('last_sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('schedule_id'),
    )

    op.create_table(
        'nc_ai_recommendations',
        sa.Column('rec_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_type', sa.Enum('optimizer', 'behavior_analyzer', name='ncnotifaiagentype'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'acknowledged', 'actioned', 'dismissed', name='ncnotifairecstatus'), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('actioned_by', sa.String(200), nullable=True),
        sa.Column('actioned_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('rec_id'),
    )


def downgrade() -> None:
    op.drop_table('nc_ai_recommendations')
    op.drop_table('nc_notification_schedules')
    op.drop_table('nc_notification_templates')
    op.drop_table('nc_notification_preferences')
    op.drop_index('ix_nc_notifications_created_at', 'nc_notifications')
    op.drop_index('ix_nc_notifications_read_flag', 'nc_notifications')
    op.drop_index('ix_nc_notifications_user_id', 'nc_notifications')
    op.drop_table('nc_notifications')
    op.execute("DROP TYPE IF EXISTS notificationtype")
    op.execute("DROP TYPE IF EXISTS notificationpriority")
    op.execute("DROP TYPE IF EXISTS notificationchannel")
    op.execute("DROP TYPE IF EXISTS notificationstatus")
    op.execute("DROP TYPE IF EXISTS ncnotifaiagentype")
    op.execute("DROP TYPE IF EXISTS ncnotifairecstatus")
