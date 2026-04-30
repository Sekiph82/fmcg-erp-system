"""recruitment_ats

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-04-30 01:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'e1f2a3b4c5d6'
down_revision = 'd0e1f2a3b4c5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'recruitment_stages',
        sa.Column('stage_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stage_code', sa.String(50), nullable=False),
        sa.Column('stage_name', sa.String(100), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('stage_type', sa.Enum('active', 'final_hire', 'final_reject', name='stagetype'), nullable=True),
        sa.Column('active_flag', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('stage_id'),
        sa.UniqueConstraint('stage_code'),
    )

    op.create_table(
        'job_requisitions',
        sa.Column('requisition_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('requisition_code', sa.String(30), nullable=False),
        sa.Column('job_title', sa.String(150), nullable=False),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('location', sa.String(150), nullable=True),
        sa.Column('employment_type', sa.Enum('full_time', 'part_time', 'contract', 'intern', name='employmenttype'), nullable=True),
        sa.Column('headcount', sa.Integer(), nullable=True),
        sa.Column('filled_count', sa.Integer(), nullable=True),
        sa.Column('requested_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.Enum('draft', 'approved', 'open', 'closed', 'cancelled', name='requisitionstatus'), nullable=True),
        sa.Column('opening_date', sa.Date(), nullable=True),
        sa.Column('closing_date', sa.Date(), nullable=True),
        sa.Column('job_description', sa.Text(), nullable=True),
        sa.Column('requirements', sa.Text(), nullable=True),
        sa.Column('salary_min', sa.Numeric(14, 2), nullable=True),
        sa.Column('salary_max', sa.Numeric(14, 2), nullable=True),
        sa.Column('currency', sa.String(3), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('requisition_id'),
        sa.UniqueConstraint('requisition_code'),
    )

    op.create_table(
        'job_postings',
        sa.Column('posting_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('requisition_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('posting_channel', sa.Enum('internal', 'website', 'job_portal', 'agency', 'referral', name='postingchannel'), nullable=True),
        sa.Column('posting_url', sa.String(500), nullable=True),
        sa.Column('publish_date', sa.Date(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum('draft', 'active', 'expired', 'closed', name='postingstatus'), nullable=True),
        sa.Column('views_count', sa.Integer(), nullable=True),
        sa.Column('applications_count', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['requisition_id'], ['job_requisitions.requisition_id']),
        sa.PrimaryKeyConstraint('posting_id'),
    )

    op.create_table(
        'candidates',
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('candidate_code', sa.String(30), nullable=False),
        sa.Column('full_name', sa.String(150), nullable=False),
        sa.Column('email', sa.String(200), nullable=False),
        sa.Column('phone', sa.String(30), nullable=True),
        sa.Column('location', sa.String(150), nullable=True),
        sa.Column('cv_attachment', sa.String(500), nullable=True),
        sa.Column('source', sa.Enum('portal', 'referral', 'agency', 'manual', 'linkedin', 'job_portal', name='candidatesource'), nullable=True),
        sa.Column('current_employer', sa.String(150), nullable=True),
        sa.Column('current_title', sa.String(150), nullable=True),
        sa.Column('years_experience', sa.Integer(), nullable=True),
        sa.Column('education_level', sa.String(100), nullable=True),
        sa.Column('skills_tags', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('blacklisted', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('candidate_id'),
        sa.UniqueConstraint('candidate_code'),
        sa.UniqueConstraint('email'),
    )

    op.create_table(
        'candidate_pipelines',
        sa.Column('pipeline_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('requisition_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stage_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_recruiter', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.Enum('active', 'moved', 'rejected', 'hired', 'on_hold', 'withdrawn', name='pipelinestatus'), nullable=True),
        sa.Column('application_date', sa.Date(), nullable=True),
        sa.Column('last_update', sa.DateTime(), nullable=True),
        sa.Column('screening_score', sa.Integer(), nullable=True),
        sa.Column('overall_score', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.candidate_id']),
        sa.ForeignKeyConstraint(['requisition_id'], ['job_requisitions.requisition_id']),
        sa.ForeignKeyConstraint(['stage_id'], ['recruitment_stages.stage_id']),
        sa.PrimaryKeyConstraint('pipeline_id'),
        sa.UniqueConstraint('candidate_id', 'requisition_id', name='uq_candidate_requisition'),
    )

    op.create_table(
        'candidate_pipeline_history',
        sa.Column('history_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pipeline_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stage_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('moved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('moved_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['pipeline_id'], ['candidate_pipelines.pipeline_id']),
        sa.ForeignKeyConstraint(['stage_id'], ['recruitment_stages.stage_id']),
        sa.PrimaryKeyConstraint('history_id'),
    )

    op.create_table(
        'interviews',
        sa.Column('interview_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('requisition_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stage_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('interviewer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('interview_date', sa.DateTime(), nullable=False),
        sa.Column('interview_type', sa.Enum('online', 'onsite', 'phone', 'panel', name='interviewtype'), nullable=True),
        sa.Column('location_or_link', sa.String(500), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('technical_score', sa.Integer(), nullable=True),
        sa.Column('cultural_score', sa.Integer(), nullable=True),
        sa.Column('decision', sa.Enum('pass', 'fail', 'hold', 'pending', name='interviewdecision'), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.candidate_id']),
        sa.ForeignKeyConstraint(['requisition_id'], ['job_requisitions.requisition_id']),
        sa.ForeignKeyConstraint(['stage_id'], ['recruitment_stages.stage_id']),
        sa.PrimaryKeyConstraint('interview_id'),
    )

    op.create_table(
        'offers',
        sa.Column('offer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('offer_code', sa.String(30), nullable=False),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('requisition_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('offer_date', sa.Date(), nullable=False),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('salary_offer', sa.Numeric(14, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=True),
        sa.Column('joining_date', sa.Date(), nullable=True),
        sa.Column('employment_type', sa.Enum('full_time', 'part_time', 'contract', 'intern', name='employmenttype'), nullable=True),
        sa.Column('status', sa.Enum('draft', 'sent', 'accepted', 'rejected', 'negotiating', 'expired', name='offerstatus'), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('responded_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('negotiation_notes', sa.Text(), nullable=True),
        sa.Column('employee_id_created', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.candidate_id']),
        sa.ForeignKeyConstraint(['requisition_id'], ['job_requisitions.requisition_id']),
        sa.PrimaryKeyConstraint('offer_id'),
        sa.UniqueConstraint('offer_code'),
    )

    op.create_table(
        'rt_ai_recommendations',
        sa.Column('rec_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_type', sa.Enum('candidate_matcher', 'hiring_risk_detector', 'pipeline_optimizer', name='rtaiagenttype'), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('ref_requisition_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ref_candidate_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.Enum('pending', 'acknowledged', 'dismissed', 'actioned', name='rtairecstatus'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('actioned_at', sa.DateTime(), nullable=True),
        sa.Column('actioned_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('rec_id'),
    )


def downgrade() -> None:
    op.drop_table('rt_ai_recommendations')
    op.drop_table('offers')
    op.drop_table('interviews')
    op.drop_table('candidate_pipeline_history')
    op.drop_table('candidate_pipelines')
    op.drop_table('candidates')
    op.drop_table('job_postings')
    op.drop_table('job_requisitions')
    op.drop_table('recruitment_stages')
    op.execute("DROP TYPE IF EXISTS rtaiagenttype")
    op.execute("DROP TYPE IF EXISTS rtairecstatus")
    op.execute("DROP TYPE IF EXISTS stagetype")
    op.execute("DROP TYPE IF EXISTS employmenttype")
    op.execute("DROP TYPE IF EXISTS requisitionstatus")
    op.execute("DROP TYPE IF EXISTS postingchannel")
    op.execute("DROP TYPE IF EXISTS postingstatus")
    op.execute("DROP TYPE IF EXISTS candidatesource")
    op.execute("DROP TYPE IF EXISTS pipelinestatus")
    op.execute("DROP TYPE IF EXISTS interviewtype")
    op.execute("DROP TYPE IF EXISTS interviewdecision")
    op.execute("DROP TYPE IF EXISTS offerstatus")
