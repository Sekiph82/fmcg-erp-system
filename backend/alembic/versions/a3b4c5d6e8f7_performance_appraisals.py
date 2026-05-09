"""performance_appraisals

Revision ID: a3b4c5d6e8f7
Revises: f2a3b4c5d6e7
Create Date: 2026-04-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a3b4c5d6e8f7'
down_revision = 'f2a3b4c5d6e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'appraisal_periods',
        sa.Column('appraisal_period_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('period_code', sa.String(50), nullable=False),
        sa.Column('period_name', sa.String(200), nullable=False),
        sa.Column('period_type', sa.Enum(
            'annual', 'semi_annual', 'quarterly', 'probation', 'project_based', 'custom',
            name='appraisalperiodtype'
        ), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('review_start_date', sa.Date(), nullable=True),
        sa.Column('review_end_date', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum(
            'draft', 'active', 'closed', 'archived',
            name='appraisalperiodstatus'
        ), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('appraisal_period_id'),
        sa.UniqueConstraint('period_code'),
    )

    op.create_table(
        'appraisal_templates',
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_code', sa.String(50), nullable=False),
        sa.Column('template_name', sa.String(200), nullable=False),
        sa.Column('department_id', sa.String(100), nullable=True),
        sa.Column('role_id', sa.String(100), nullable=True),
        sa.Column('employee_grade_id', sa.String(100), nullable=True),
        sa.Column('kpi_weight_pct', sa.Numeric(5, 2), nullable=True),
        sa.Column('competency_weight_pct', sa.Numeric(5, 2), nullable=True),
        sa.Column('active_flag', sa.Boolean(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('template_id'),
        sa.UniqueConstraint('template_code'),
    )

    op.create_table(
        'appraisal_records',
        sa.Column('appraisal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('appraisal_period_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', sa.String(100), nullable=False),
        sa.Column('employee_name', sa.String(200), nullable=True),
        sa.Column('manager_id', sa.String(100), nullable=True),
        sa.Column('manager_name', sa.String(200), nullable=True),
        sa.Column('department_id', sa.String(100), nullable=True),
        sa.Column('department_name', sa.String(200), nullable=True),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.Enum(
            'draft', 'self_review', 'manager_review', 'hr_review', 'calibration', 'completed', 'rejected',
            name='appraisalstatus'
        ), nullable=False),
        sa.Column('self_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('manager_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('final_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('final_rating', sa.Enum(
            'excellent', 'good', 'meets_expectations', 'improvement_needed',
            name='finalrating'
        ), nullable=True),
        sa.Column('increment_recommendation', sa.Numeric(5, 2), nullable=True),
        sa.Column('promotion_recommendation', sa.Boolean(), nullable=True),
        sa.Column('self_submitted_at', sa.DateTime(), nullable=True),
        sa.Column('manager_reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('hr_reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('finalized_at', sa.DateTime(), nullable=True),
        sa.Column('hr_notes', sa.Text(), nullable=True),
        sa.Column('calibration_notes', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['appraisal_period_id'], ['appraisal_periods.appraisal_period_id']),
        sa.ForeignKeyConstraint(['template_id'], ['appraisal_templates.template_id']),
        sa.PrimaryKeyConstraint('appraisal_id'),
        sa.UniqueConstraint('appraisal_period_id', 'employee_id', name='uq_appraisal_period_employee'),
    )

    op.create_table(
        'appraisal_kpi_lines',
        sa.Column('kpi_line_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('appraisal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kpi_name', sa.String(300), nullable=False),
        sa.Column('kpi_description', sa.Text(), nullable=True),
        sa.Column('target_value', sa.Numeric(15, 4), nullable=True),
        sa.Column('actual_value', sa.Numeric(15, 4), nullable=True),
        sa.Column('unit', sa.String(50), nullable=True),
        sa.Column('weight_pct', sa.Numeric(5, 2), nullable=False),
        sa.Column('self_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('manager_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('final_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['appraisal_id'], ['appraisal_records.appraisal_id']),
        sa.PrimaryKeyConstraint('kpi_line_id'),
    )

    op.create_table(
        'appraisal_competency_lines',
        sa.Column('competency_line_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('appraisal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('competency_name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('weight_pct', sa.Numeric(5, 2), nullable=False),
        sa.Column('self_rating', sa.Numeric(3, 1), nullable=True),
        sa.Column('manager_rating', sa.Numeric(3, 1), nullable=True),
        sa.Column('final_rating', sa.Numeric(3, 1), nullable=True),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['appraisal_id'], ['appraisal_records.appraisal_id']),
        sa.PrimaryKeyConstraint('competency_line_id'),
    )

    op.create_table(
        'appraisal_development_plans',
        sa.Column('development_plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('appraisal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', sa.String(100), nullable=False),
        sa.Column('goal_title', sa.String(300), nullable=False),
        sa.Column('action_plan', sa.Text(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('owner_id', sa.String(100), nullable=True),
        sa.Column('owner_name', sa.String(200), nullable=True),
        sa.Column('status', sa.Enum(
            'open', 'in_progress', 'completed', 'cancelled',
            name='developmentplanstatus'
        ), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['appraisal_id'], ['appraisal_records.appraisal_id']),
        sa.PrimaryKeyConstraint('development_plan_id'),
    )

    op.create_table(
        'ap_ai_recommendations',
        sa.Column('rec_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_type', sa.Enum(
            'performance_insight', 'calibration_risk', 'development_plan',
            name='apaiagentype'
        ), nullable=False),
        sa.Column('status', sa.Enum(
            'pending', 'acknowledged', 'actioned', 'dismissed',
            name='apaairecstatus'
        ), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('appraisal_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('employee_id', sa.String(100), nullable=True),
        sa.Column('department_id', sa.String(100), nullable=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('actioned_by', sa.String(200), nullable=True),
        sa.Column('actioned_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('rec_id'),
    )


def downgrade() -> None:
    op.drop_table('ap_ai_recommendations')
    op.drop_table('appraisal_development_plans')
    op.drop_table('appraisal_competency_lines')
    op.drop_table('appraisal_kpi_lines')
    op.drop_table('appraisal_records')
    op.drop_table('appraisal_templates')
    op.drop_table('appraisal_periods')
    op.execute("DROP TYPE IF EXISTS appraisalperiodtype")
    op.execute("DROP TYPE IF EXISTS appraisalperiodstatus")
    op.execute("DROP TYPE IF EXISTS appraisalstatus")
    op.execute("DROP TYPE IF EXISTS finalrating")
    op.execute("DROP TYPE IF EXISTS developmentplanstatus")
    op.execute("DROP TYPE IF EXISTS apaiagentype")
    op.execute("DROP TYPE IF EXISTS apaairecstatus")
