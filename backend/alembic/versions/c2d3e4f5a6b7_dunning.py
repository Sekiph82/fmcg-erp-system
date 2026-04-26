"""dunning_overdue_collection

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-04-26 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c2d3e4f5a6b7'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'dunning_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('policy_code', sa.String(50), nullable=False, unique=True),
        sa.Column('policy_name', sa.String(200), nullable=False),
        sa.Column('active_flag', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('applies_to_customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('applies_to_channel', sa.String(60), nullable=True),
        sa.Column('applies_to_region', sa.String(100), nullable=True),
        sa.Column('applies_to_country', sa.String(100), nullable=True),
        sa.Column('applies_to_segment', sa.String(100), nullable=True),
        sa.Column('default_flag', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('auto_credit_hold_days', sa.Integer(), nullable=True),
        sa.Column('auto_credit_hold_amount', sa.Numeric(16, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'dunning_levels',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('policy_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dunning_policies.id'), nullable=False),
        sa.Column('level_no', sa.Integer(), nullable=False),
        sa.Column('level_name', sa.String(100), nullable=False),
        sa.Column('days_overdue_from', sa.Integer(), nullable=False),
        sa.Column('days_overdue_to', sa.Integer(), nullable=True),
        sa.Column('action_type', sa.String(40), nullable=False, server_default='EMAIL'),
        sa.Column('template_code', sa.String(100), nullable=True),
        sa.Column('auto_send_flag', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('requires_approval_flag', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('apply_credit_hold_flag', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('escalate_to_role', sa.String(100), nullable=True),
        sa.Column('active_flag', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('policy_id', 'level_no', name='uq_dunning_level'),
    )

    op.create_table(
        'dunning_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('template_code', sa.String(100), nullable=False),
        sa.Column('language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('subject', sa.String(300), nullable=False),
        sa.Column('body_text', sa.Text(), nullable=False),
        sa.Column('channel', sa.String(40), nullable=False, server_default='EMAIL'),
        sa.Column('active_flag', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('template_code', 'language', name='uq_dunning_template'),
    )

    op.create_table(
        'dunning_cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_no', sa.String(50), nullable=False, unique=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('policy_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dunning_policies.id'), nullable=True),
        sa.Column('current_level_no', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('case_status', sa.String(30), nullable=False, server_default='OPEN'),
        sa.Column('total_overdue_amount', sa.Numeric(16, 2), nullable=False, server_default='0'),
        sa.Column('oldest_due_date', sa.Date(), nullable=True),
        sa.Column('latest_action_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_action_date', sa.Date(), nullable=True),
        sa.Column('assigned_collector_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('credit_hold_flag', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('credit_hold_reason', sa.Text(), nullable=True),
        sa.Column('credit_hold_date', sa.Date(), nullable=True),
        sa.Column('priority_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('collector_notes', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'dunning_case_invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dunning_cases.id'), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('invoices.id'), nullable=False),
        sa.Column('invoice_number', sa.String(80), nullable=False),
        sa.Column('invoice_due_date', sa.Date(), nullable=False),
        sa.Column('invoice_balance_amount', sa.Numeric(16, 2), nullable=False),
        sa.Column('days_overdue', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('dispute_flag', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('dispute_reason', sa.Text(), nullable=True),
        sa.Column('promise_to_pay_date', sa.Date(), nullable=True),
        sa.Column('excluded_from_dunning', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('case_id', 'invoice_id', name='uq_dunning_case_inv'),
    )

    op.create_table(
        'dunning_action_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dunning_cases.id'), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('level_no', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(40), nullable=False),
        sa.Column('channel_type', sa.String(40), nullable=True),
        sa.Column('action_datetime', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sent_by_system_flag', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('template_code', sa.String(100), nullable=True),
        sa.Column('outcome_status', sa.String(30), nullable=False, server_default='SENT'),
        sa.Column('external_message_ref', sa.String(200), nullable=True),
        sa.Column('rendered_subject', sa.String(400), nullable=True),
        sa.Column('rendered_body', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
    )

    op.create_table(
        'dunning_ptps',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dunning_cases.id'), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('promised_amount', sa.Numeric(16, 2), nullable=False),
        sa.Column('promised_date', sa.Date(), nullable=False),
        sa.Column('recorded_by', sa.String(200), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='OPEN'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'dunning_exceptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dunning_cases.id'), nullable=False),
        sa.Column('exception_type', sa.String(50), nullable=False),
        sa.Column('approved_by', sa.String(200), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'dunning_ai_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dunning_cases.id'), nullable=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('agent_type', sa.String(40), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False, server_default='INFO'),
        sa.Column('reference_type', sa.String(80), nullable=True),
        sa.Column('reference_id', sa.String(80), nullable=True),
        sa.Column('actioned_by', sa.String(200), nullable=True),
        sa.Column('actioned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('dunning_ai_recommendations')
    op.drop_table('dunning_exceptions')
    op.drop_table('dunning_ptps')
    op.drop_table('dunning_action_logs')
    op.drop_table('dunning_case_invoices')
    op.drop_table('dunning_cases')
    op.drop_table('dunning_templates')
    op.drop_table('dunning_levels')
    op.drop_table('dunning_policies')
