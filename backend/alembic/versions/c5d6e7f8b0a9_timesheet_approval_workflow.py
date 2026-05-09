"""timesheet_approval_workflow

Revision ID: c5d6e7f8b0a9
Revises: b4c5d6e7a8f9
Create Date: 2026-04-30 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c5d6e7f8b0a9'
down_revision = 'b4c5d6e7a8f9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'timesheet_headers',
        sa.Column('timesheet_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', sa.String(100), nullable=False),
        sa.Column('employee_name', sa.String(200), nullable=True),
        sa.Column('department_id', sa.String(100), nullable=True),
        sa.Column('department_name', sa.String(200), nullable=True),
        sa.Column('manager_id', sa.String(100), nullable=True),
        sa.Column('manager_name', sa.String(200), nullable=True),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('status', sa.Enum(
            'draft', 'submitted', 'manager_approved', 'rejected', 'finalized',
            name='timesheetstatus'
        ), nullable=False),
        sa.Column('total_hours', sa.Numeric(6, 2), nullable=True),
        sa.Column('overtime_hours', sa.Numeric(6, 2), nullable=True),
        sa.Column('regular_hours', sa.Numeric(6, 2), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('approved_by', sa.String(200), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('finalized_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_count', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('timesheet_id'),
        sa.UniqueConstraint('employee_id', 'period_start', 'period_end', name='uq_timesheet_employee_period'),
    )

    op.create_table(
        'timesheet_lines',
        sa.Column('timesheet_line_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timesheet_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('work_date', sa.Date(), nullable=False),
        sa.Column('project_id', sa.String(100), nullable=True),
        sa.Column('project_name', sa.String(200), nullable=True),
        sa.Column('task_id', sa.String(100), nullable=True),
        sa.Column('task_name', sa.String(200), nullable=True),
        sa.Column('activity_type', sa.Enum(
            'regular', 'overtime', 'training', 'leave', 'meeting', 'admin', 'project', 'support', 'other',
            name='activitytype'
        ), nullable=False),
        sa.Column('cost_center_id', sa.String(100), nullable=True),
        sa.Column('cost_center_name', sa.String(200), nullable=True),
        sa.Column('hours_worked', sa.Numeric(5, 2), nullable=False),
        sa.Column('overtime_flag', sa.Boolean(), nullable=True),
        sa.Column('billable_flag', sa.Boolean(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['timesheet_id'], ['timesheet_headers.timesheet_id']),
        sa.PrimaryKeyConstraint('timesheet_line_id'),
    )

    op.create_table(
        'timesheet_approval_logs',
        sa.Column('approval_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timesheet_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('approver_id', sa.String(100), nullable=True),
        sa.Column('approver_name', sa.String(200), nullable=True),
        sa.Column('action', sa.Enum(
            'submitted', 'approved', 'rejected', 'finalized', 'resubmitted',
            name='approvalaction'
        ), nullable=False),
        sa.Column('action_date', sa.DateTime(), nullable=True),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['timesheet_id'], ['timesheet_headers.timesheet_id']),
        sa.PrimaryKeyConstraint('approval_id'),
    )

    op.create_table(
        'ts_ai_recommendations',
        sa.Column('rec_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_type', sa.Enum(
            'utilization_analyzer', 'anomaly_detector',
            name='tsaiagentype'
        ), nullable=False),
        sa.Column('status', sa.Enum(
            'pending', 'acknowledged', 'actioned', 'dismissed',
            name='tsairecstatus'
        ), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('employee_id', sa.String(100), nullable=True),
        sa.Column('department_id', sa.String(100), nullable=True),
        sa.Column('timesheet_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('actioned_by', sa.String(200), nullable=True),
        sa.Column('actioned_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('rec_id'),
    )


def downgrade() -> None:
    op.drop_table('ts_ai_recommendations')
    op.drop_table('timesheet_approval_logs')
    op.drop_table('timesheet_lines')
    op.drop_table('timesheet_headers')
    op.execute("DROP TYPE IF EXISTS timesheetstatus")
    op.execute("DROP TYPE IF EXISTS activitytype")
    op.execute("DROP TYPE IF EXISTS approvalaction")
    op.execute("DROP TYPE IF EXISTS tsaiagentype")
    op.execute("DROP TYPE IF EXISTS tsairecstatus")
