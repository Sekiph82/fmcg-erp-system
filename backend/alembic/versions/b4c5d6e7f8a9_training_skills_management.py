"""training_skills_management

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-04-30 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b4c5d6e7f8a9'
down_revision = 'a3b4c5d6e7f8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'training_skills',
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('skill_code', sa.String(50), nullable=False),
        sa.Column('skill_name', sa.String(200), nullable=False),
        sa.Column('category', sa.Enum('technical','soft','safety','compliance','management', name='skillcategory'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active_flag', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('skill_id'),
        sa.UniqueConstraint('skill_code'),
    )

    op.create_table(
        'employee_skill_profiles',
        sa.Column('employee_skill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', sa.String(100), nullable=False),
        sa.Column('employee_name', sa.String(200), nullable=True),
        sa.Column('department_id', sa.String(100), nullable=True),
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('current_level', sa.Enum('basic','intermediate','advanced','expert', name='skilllevel'), nullable=True),
        sa.Column('required_level', sa.Enum('basic','intermediate','advanced','expert', name='skilllevel'), nullable=True),
        sa.Column('last_assessed_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['skill_id'], ['training_skills.skill_id']),
        sa.PrimaryKeyConstraint('employee_skill_id'),
        sa.UniqueConstraint('employee_id', 'skill_id', name='uq_employee_skill'),
    )

    op.create_table(
        'training_programs',
        sa.Column('training_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('training_code', sa.String(50), nullable=False),
        sa.Column('training_name', sa.String(300), nullable=False),
        sa.Column('training_type', sa.Enum('internal','external','online','classroom','on_job', name='trainingtype'), nullable=False),
        sa.Column('category', sa.Enum('technical','soft','safety','compliance','management', name='skillcategory'), nullable=False),
        sa.Column('duration_hours', sa.Numeric(6, 2), nullable=True),
        sa.Column('provider', sa.String(200), nullable=True),
        sa.Column('cost', sa.Numeric(12, 2), nullable=True),
        sa.Column('mandatory_flag', sa.Boolean(), nullable=True),
        sa.Column('validity_period_days', sa.Integer(), nullable=True),
        sa.Column('active_flag', sa.Boolean(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('training_id'),
        sa.UniqueConstraint('training_code'),
    )

    op.create_table(
        'training_sessions',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('training_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('location', sa.String(300), nullable=True),
        sa.Column('trainer_id', sa.String(100), nullable=True),
        sa.Column('trainer_name', sa.String(200), nullable=True),
        sa.Column('capacity', sa.Integer(), nullable=True),
        sa.Column('enrolled_count', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('planned','in_progress','completed','cancelled', name='sessionstatus'), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['training_id'], ['training_programs.training_id']),
        sa.PrimaryKeyConstraint('session_id'),
    )

    op.create_table(
        'training_assignments',
        sa.Column('assignment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', sa.String(100), nullable=False),
        sa.Column('employee_name', sa.String(200), nullable=True),
        sa.Column('department_id', sa.String(100), nullable=True),
        sa.Column('training_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assigned_by', sa.String(200), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('completion_date', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum('assigned','in_progress','completed','overdue','waived', name='assignmentstatus'), nullable=False),
        sa.Column('score', sa.Numeric(5, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['training_id'], ['training_programs.training_id']),
        sa.ForeignKeyConstraint(['session_id'], ['training_sessions.session_id']),
        sa.PrimaryKeyConstraint('assignment_id'),
        sa.UniqueConstraint('employee_id', 'training_id', 'session_id', name='uq_assignment_employee_training_session'),
    )

    op.create_table(
        'certification_records',
        sa.Column('certification_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', sa.String(100), nullable=False),
        sa.Column('employee_name', sa.String(200), nullable=True),
        sa.Column('training_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('certificate_name', sa.String(300), nullable=False),
        sa.Column('certificate_no', sa.String(100), nullable=True),
        sa.Column('issuer', sa.String(200), nullable=True),
        sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum('valid','expiring','expired','revoked', name='certificationstatus'), nullable=False),
        sa.Column('document_url', sa.String(500), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['training_id'], ['training_programs.training_id']),
        sa.PrimaryKeyConstraint('certification_id'),
    )

    op.create_table(
        'training_feedback',
        sa.Column('feedback_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', sa.String(100), nullable=False),
        sa.Column('employee_name', sa.String(200), nullable=True),
        sa.Column('training_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('content_rating', sa.Integer(), nullable=True),
        sa.Column('trainer_rating', sa.Integer(), nullable=True),
        sa.Column('relevance_rating', sa.Integer(), nullable=True),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['training_id'], ['training_programs.training_id']),
        sa.ForeignKeyConstraint(['session_id'], ['training_sessions.session_id']),
        sa.PrimaryKeyConstraint('feedback_id'),
        sa.UniqueConstraint('employee_id', 'training_id', 'session_id', name='uq_feedback_employee_training_session'),
    )

    op.create_table(
        'tr_ai_recommendations',
        sa.Column('rec_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_type', sa.Enum('skill_gap_advisor','effectiveness_analyzer','compliance_risk', name='traiagentype'), nullable=False),
        sa.Column('status', sa.Enum('pending','acknowledged','actioned','dismissed', name='trairecstatus'), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('employee_id', sa.String(100), nullable=True),
        sa.Column('department_id', sa.String(100), nullable=True),
        sa.Column('training_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('certification_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('actioned_by', sa.String(200), nullable=True),
        sa.Column('actioned_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('rec_id'),
    )


def downgrade() -> None:
    op.drop_table('tr_ai_recommendations')
    op.drop_table('training_feedback')
    op.drop_table('certification_records')
    op.drop_table('training_assignments')
    op.drop_table('training_sessions')
    op.drop_table('training_programs')
    op.drop_table('employee_skill_profiles')
    op.drop_table('training_skills')
    op.execute("DROP TYPE IF EXISTS skillcategory")
    op.execute("DROP TYPE IF EXISTS skilllevel")
    op.execute("DROP TYPE IF EXISTS trainingtype")
    op.execute("DROP TYPE IF EXISTS sessionstatus")
    op.execute("DROP TYPE IF EXISTS assignmentstatus")
    op.execute("DROP TYPE IF EXISTS certificationstatus")
    op.execute("DROP TYPE IF EXISTS traiagentype")
    op.execute("DROP TYPE IF EXISTS trairecstatus")
