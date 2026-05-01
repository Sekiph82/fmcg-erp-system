"""webhook_event_engine

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-05-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'e3f4a5b6c7d8'
down_revision = 'd2e3f4a5b6c7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enums ─────────────────────────────────────────────────────────────────
    http_method = postgresql.ENUM('POST', 'PUT', name='httpmethod')
    http_method.create(op.get_bind(), checkfirst=True)

    auth_type = postgresql.ENUM('none', 'basic', 'bearer', 'hmac', name='authtype')
    auth_type.create(op.get_bind(), checkfirst=True)

    delivery_status = postgresql.ENUM(
        'pending', 'sent', 'failed', 'retrying', 'dead_letter',
        name='deliverystatus',
    )
    delivery_status.create(op.get_bind(), checkfirst=True)

    # ── webhook_event_definitions ─────────────────────────────────────────────
    op.create_table(
        'webhook_event_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_code', sa.String(100), nullable=False, unique=True),
        sa.Column('event_name', sa.String(255), nullable=False),
        sa.Column('module', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('payload_schema', postgresql.JSONB, nullable=True),
        sa.Column('active_flag', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_webhook_event_definitions_event_code', 'webhook_event_definitions', ['event_code'])
    op.create_index('ix_webhook_event_definitions_module', 'webhook_event_definitions', ['module'])

    # ── webhook_event_logs ────────────────────────────────────────────────────
    op.create_table(
        'webhook_event_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_def_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('webhook_event_definitions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('event_code', sa.String(100), nullable=False),
        sa.Column('module', sa.String(100), nullable=False),
        sa.Column('reference_type', sa.String(100), nullable=True),
        sa.Column('reference_id', sa.String(100), nullable=True),
        sa.Column('payload', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('actor_id', sa.String(100), nullable=True),
        sa.Column('partition_key', sa.String(100), nullable=True),
        sa.Column('sequence_no', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_webhook_event_logs_event_code', 'webhook_event_logs', ['event_code'])
    op.create_index('ix_webhook_event_logs_module', 'webhook_event_logs', ['module'])
    op.create_index('ix_webhook_event_logs_reference_id', 'webhook_event_logs', ['reference_id'])
    op.create_index('ix_webhook_event_logs_partition_key', 'webhook_event_logs', ['partition_key'])

    # ── webhook_subscriptions ─────────────────────────────────────────────────
    op.create_table(
        'webhook_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('endpoint_url', sa.String(2048), nullable=False),
        sa.Column('http_method', sa.Enum('POST', 'PUT', name='httpmethod'), nullable=False, server_default='POST'),
        sa.Column('headers', postgresql.JSONB, nullable=True),
        sa.Column('auth_type', sa.Enum('none', 'basic', 'bearer', 'hmac', name='authtype'), nullable=False, server_default='none'),
        sa.Column('secret_key', sa.String(512), nullable=True),
        sa.Column('auth_user', sa.String(255), nullable=True),
        sa.Column('filter_expression', postgresql.JSONB, nullable=True),
        sa.Column('event_codes', postgresql.JSONB, nullable=True),
        sa.Column('transform_template', postgresql.JSONB, nullable=True),
        sa.Column('max_retries', sa.Integer, nullable=False, server_default='5'),
        sa.Column('timeout_seconds', sa.Integer, nullable=False, server_default='30'),
        sa.Column('active_flag', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── webhook_delivery_attempts ─────────────────────────────────────────────
    op.create_table(
        'webhook_delivery_attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_log_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('webhook_event_logs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('webhook_subscriptions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('attempt_no', sa.Integer, nullable=False, server_default='1'),
        sa.Column('request_payload', postgresql.JSONB, nullable=True),
        sa.Column('response_status', sa.Integer, nullable=True),
        sa.Column('response_body', sa.Text, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('attempted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.Enum('pending', 'sent', 'failed', 'retrying', 'dead_letter', name='deliverystatus'), nullable=False, server_default='pending'),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_webhook_delivery_attempts_event_log_id', 'webhook_delivery_attempts', ['event_log_id'])
    op.create_index('ix_webhook_delivery_attempts_subscription_id', 'webhook_delivery_attempts', ['subscription_id'])
    op.create_index('ix_webhook_delivery_attempts_status', 'webhook_delivery_attempts', ['status'])

    # ── webhook_inbound_endpoints ─────────────────────────────────────────────
    op.create_table(
        'webhook_inbound_endpoints',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('endpoint_path', sa.String(255), nullable=False, unique=True),
        sa.Column('method', sa.Enum('POST', 'PUT', name='httpmethod'), nullable=False, server_default='POST'),
        sa.Column('auth_type', sa.Enum('none', 'basic', 'bearer', 'hmac', name='authtype'), nullable=False, server_default='none'),
        sa.Column('secret_key', sa.String(512), nullable=True),
        sa.Column('handler_module', sa.String(100), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('active_flag', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('last_received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('receive_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_webhook_inbound_endpoints_endpoint_path', 'webhook_inbound_endpoints', ['endpoint_path'])


def downgrade() -> None:
    op.drop_table('webhook_inbound_endpoints')
    op.drop_table('webhook_delivery_attempts')
    op.drop_table('webhook_subscriptions')
    op.drop_table('webhook_event_logs')
    op.drop_table('webhook_event_definitions')

    op.execute("DROP TYPE IF EXISTS deliverystatus")
    op.execute("DROP TYPE IF EXISTS authtype")
    op.execute("DROP TYPE IF EXISTS httpmethod")
