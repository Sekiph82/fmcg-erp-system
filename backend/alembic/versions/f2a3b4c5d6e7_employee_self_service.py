"""employee_self_service

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-04-30 02:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'f2a3b4c5d6e7'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ess_accounts',
        sa.Column('ess_account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(200), nullable=False),
        sa.Column('password_hash', sa.String(200), nullable=False),
        sa.Column('status', sa.Enum('active', 'inactive', 'suspended', name='essaccountstatus'), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('failed_attempts', sa.Integer(), nullable=True),
        sa.Column('reset_token', sa.String(100), nullable=True),
        sa.Column('reset_token_expiry', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('ess_account_id'),
        sa.UniqueConstraint('employee_id'),
        sa.UniqueConstraint('email'),
    )

    op.create_table(
        'ess_employee_profiles',
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('full_name', sa.String(150), nullable=False),
        sa.Column('email', sa.String(200), nullable=False),
        sa.Column('personal_email', sa.String(200), nullable=True),
        sa.Column('phone', sa.String(30), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('department_name', sa.String(150), nullable=True),
        sa.Column('manager_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('manager_name', sa.String(150), nullable=True),
        sa.Column('job_title', sa.String(150), nullable=True),
        sa.Column('joining_date', sa.Date(), nullable=True),
        sa.Column('employment_status', sa.Enum('active', 'on_leave', 'resigned', 'terminated', 'probation', name='employmentstatus_ess'), nullable=True),
        sa.Column('grade', sa.String(50), nullable=True),
        sa.Column('profile_photo', sa.String(500), nullable=True),
        sa.Column('bank_account_no', sa.String(50), nullable=True),
        sa.Column('national_id', sa.String(30), nullable=True),
        sa.Column('emergency_contact_name', sa.String(150), nullable=True),
        sa.Column('emergency_contact_phone', sa.String(30), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['ess_accounts.employee_id']),
        sa.PrimaryKeyConstraint('profile_id'),
        sa.UniqueConstraint('employee_id'),
    )

    op.create_table(
        'ess_leave_types',
        sa.Column('leave_type_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type_code', sa.String(30), nullable=False),
        sa.Column('type_name', sa.String(100), nullable=False),
        sa.Column('annual_entitlement_days', sa.Integer(), nullable=True),
        sa.Column('carry_forward_max', sa.Integer(), nullable=True),
        sa.Column('requires_approval', sa.Boolean(), nullable=True),
        sa.Column('requires_document', sa.Boolean(), nullable=True),
        sa.Column('paid_leave', sa.Boolean(), nullable=True),
        sa.Column('active_flag', sa.Boolean(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('leave_type_id'),
        sa.UniqueConstraint('type_code'),
    )

    op.create_table(
        'ess_leave_balances',
        sa.Column('balance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('leave_type_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('entitled_days', sa.Numeric(5, 1), nullable=True),
        sa.Column('taken_days', sa.Numeric(5, 1), nullable=True),
        sa.Column('pending_days', sa.Numeric(5, 1), nullable=True),
        sa.Column('carried_forward', sa.Numeric(5, 1), nullable=True),
        sa.Column('adjusted_days', sa.Numeric(5, 1), nullable=True),
        sa.ForeignKeyConstraint(['leave_type_id'], ['ess_leave_types.leave_type_id']),
        sa.PrimaryKeyConstraint('balance_id'),
        sa.UniqueConstraint('employee_id', 'leave_type_id', 'year', name='uq_leave_balance'),
    )

    op.create_table(
        'ess_leave_requests',
        sa.Column('leave_request_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('leave_request_no', sa.String(30), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('leave_type_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('days_requested', sa.Numeric(5, 1), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('attachment_ref', sa.String(500), nullable=True),
        sa.Column('status', sa.Enum('draft', 'submitted', 'approved', 'rejected', 'cancelled', name='leavestatus'), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['leave_type_id'], ['ess_leave_types.leave_type_id']),
        sa.PrimaryKeyConstraint('leave_request_id'),
        sa.UniqueConstraint('leave_request_no'),
    )

    op.create_table(
        'ess_attendance_records',
        sa.Column('attendance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('attendance_date', sa.Date(), nullable=False),
        sa.Column('check_in', sa.DateTime(), nullable=True),
        sa.Column('check_out', sa.DateTime(), nullable=True),
        sa.Column('status', sa.Enum('present', 'absent', 'late', 'half_day', 'on_leave', 'holiday', 'work_from_home', name='attendancestatus'), nullable=True),
        sa.Column('hours_worked', sa.Numeric(4, 2), nullable=True),
        sa.Column('overtime_hours', sa.Numeric(4, 2), nullable=True),
        sa.Column('late_minutes', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('attendance_id'),
        sa.UniqueConstraint('employee_id', 'attendance_date', name='uq_employee_attendance_date'),
    )

    op.create_table(
        'ess_requests',
        sa.Column('request_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('request_no', sa.String(30), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('request_type', sa.Enum('leave', 'expense', 'profile_update', 'document', 'certificate', 'payslip', 'other', name='essrequesttype'), nullable=False),
        sa.Column('request_date', sa.Date(), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('attachment_ref', sa.String(500), nullable=True),
        sa.Column('status', sa.Enum('draft', 'submitted', 'in_review', 'approved', 'rejected', 'closed', name='essrequeststatus'), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('hr_notes', sa.Text(), nullable=True),
        sa.Column('reference_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('request_id'),
        sa.UniqueConstraint('request_no'),
    )

    op.create_table(
        'ess_notifications',
        sa.Column('notification_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('notification_type', sa.Enum('leave_approved', 'leave_rejected', 'request_update', 'hr_announcement', 'reminder', 'system', 'payslip_ready', name='notificationtype'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('reference_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('read_flag', sa.Boolean(), nullable=True),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('notification_id'),
    )

    op.create_table(
        'ess_documents',
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_type', sa.Enum('payslip', 'contract', 'offer_letter', 'experience_cert', 'salary_cert', 'hr_letter', 'appraisal', 'other', name='essdocumenttype'), nullable=False),
        sa.Column('document_name', sa.String(255), nullable=False),
        sa.Column('document_ref', sa.String(500), nullable=True),
        sa.Column('period', sa.String(30), nullable=True),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('visible_to_employee', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('document_id'),
    )

    op.create_table(
        'ess_activity_logs',
        sa.Column('activity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('activity_type', sa.String(80), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('reference_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['ess_accounts.employee_id']),
        sa.PrimaryKeyConstraint('activity_id'),
    )

    op.create_table(
        'ess_ai_recommendations',
        sa.Column('rec_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_type', sa.Enum('employee_assistant', 'hr_support_assistant', name='essaiagenttype'), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('ref_employee_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.Enum('pending', 'acknowledged', 'dismissed', 'actioned', name='essairecstatus'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('actioned_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('rec_id'),
    )


def downgrade() -> None:
    op.drop_table('ess_ai_recommendations')
    op.drop_table('ess_activity_logs')
    op.drop_table('ess_documents')
    op.drop_table('ess_notifications')
    op.drop_table('ess_requests')
    op.drop_table('ess_attendance_records')
    op.drop_table('ess_leave_requests')
    op.drop_table('ess_leave_balances')
    op.drop_table('ess_leave_types')
    op.drop_table('ess_employee_profiles')
    op.drop_table('ess_accounts')
    op.execute("DROP TYPE IF EXISTS essaccountstatus")
    op.execute("DROP TYPE IF EXISTS employmentstatus_ess")
    op.execute("DROP TYPE IF EXISTS leavestatus")
    op.execute("DROP TYPE IF EXISTS attendancestatus")
    op.execute("DROP TYPE IF EXISTS essrequesttype")
    op.execute("DROP TYPE IF EXISTS essrequeststatus")
    op.execute("DROP TYPE IF EXISTS notificationtype")
    op.execute("DROP TYPE IF EXISTS essdocumenttype")
    op.execute("DROP TYPE IF EXISTS essaiagenttype")
    op.execute("DROP TYPE IF EXISTS essairecstatus")
