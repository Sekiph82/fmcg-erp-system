"""kenya_payroll_localization

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-05-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'e9f0a1b2c3d4'
down_revision = 'd8e9f0a1b2c3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    pay_freq = postgresql.ENUM('MONTHLY', 'WEEKLY', 'BIWEEKLY', name='payfrequency')
    ke_component = postgresql.ENUM('NHIF', 'NSSF', 'HOUSING_LEVY', 'PERSONAL_RELIEF', name='kecomponenttype')
    payroll_run_status = postgresql.ENUM('DRAFT', 'CALCULATED', 'APPROVED', 'PAID', 'CANCELLED', name='payrollrunstatus')
    pay_freq.create(op.get_bind(), checkfirst=True)
    ke_component.create(op.get_bind(), checkfirst=True)
    payroll_run_status.create(op.get_bind(), checkfirst=True)

    # ke_payroll_profiles
    op.create_table(
        'ke_payroll_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('hr_employees.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('basic_salary', sa.Numeric(14, 2), nullable=False),
        sa.Column('pay_frequency', sa.Enum('MONTHLY', 'WEEKLY', 'BIWEEKLY', name='payfrequency'),
                  nullable=False, server_default='MONTHLY'),
        sa.Column('housing_allowance', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('transport_allowance', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('other_allowances', postgresql.JSONB(), nullable=True),
        sa.Column('tax_pin', sa.String(20), nullable=True),
        sa.Column('nhif_no', sa.String(20), nullable=True),
        sa.Column('nssf_no', sa.String(20), nullable=True),
        sa.Column('bank_name', sa.String(100), nullable=True),
        sa.Column('bank_account_no', sa.String(50), nullable=True),
        sa.Column('bank_branch', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_ke_payroll_profiles_employee_id', 'ke_payroll_profiles', ['employee_id'])

    # ke_tax_bands
    op.create_table(
        'ke_tax_bands',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tax_year', sa.Integer(), nullable=False),
        sa.Column('lower_limit', sa.Numeric(14, 2), nullable=False),
        sa.Column('upper_limit', sa.Numeric(14, 2), nullable=True),
        sa.Column('rate', sa.Numeric(6, 4), nullable=False),
        sa.Column('description', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_ke_tax_bands_tax_year', 'ke_tax_bands', ['tax_year'])

    # ke_statutory_rates
    op.create_table(
        'ke_statutory_rates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('component', sa.Enum('NHIF', 'NSSF', 'HOUSING_LEVY', 'PERSONAL_RELIEF', name='kecomponenttype'), nullable=False),
        sa.Column('rate_year', sa.Integer(), nullable=False),
        sa.Column('rate_value', sa.Numeric(10, 6), nullable=False),
        sa.Column('is_percentage', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('max_amount', sa.Numeric(14, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ke_nhif_tiers
    op.create_table(
        'ke_nhif_tiers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('rate_year', sa.Integer(), nullable=False),
        sa.Column('gross_from', sa.Numeric(14, 2), nullable=False),
        sa.Column('gross_to', sa.Numeric(14, 2), nullable=True),
        sa.Column('contribution', sa.Numeric(10, 2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_ke_nhif_tiers_rate_year', 'ke_nhif_tiers', ['rate_year'])

    # ke_payroll_runs
    op.create_table(
        'ke_payroll_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_no', sa.String(30), nullable=False, unique=True),
        sa.Column('period_month', sa.Integer(), nullable=False),
        sa.Column('period_year', sa.Integer(), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('run_date', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum('DRAFT', 'CALCULATED', 'APPROVED', 'PAID', 'CANCELLED', name='payrollrunstatus'),
                  nullable=False, server_default='DRAFT'),
        sa.Column('total_gross', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('total_paye', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('total_nhif', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('total_nssf', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('total_housing_levy', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('total_net', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('employee_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('period_month', 'period_year', name='uq_ke_payroll_run'),
    )
    op.create_index('ix_ke_payroll_runs_run_no', 'ke_payroll_runs', ['run_no'])

    # ke_payroll_lines
    op.create_table(
        'ke_payroll_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('ke_payroll_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('hr_employees.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('basic_salary', sa.Numeric(14, 2), nullable=False),
        sa.Column('housing_allowance', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('transport_allowance', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('other_allowances', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('overtime_pay', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('gross_salary', sa.Numeric(14, 2), nullable=False),
        sa.Column('nssf_employee', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('taxable_income', sa.Numeric(14, 2), nullable=False),
        sa.Column('paye_before_relief', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('personal_relief', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('paye_amount', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('nhif_amount', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('housing_levy', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('other_deductions', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('total_deductions', sa.Numeric(14, 2), nullable=False),
        sa.Column('net_salary', sa.Numeric(14, 2), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('components_json', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('run_id', 'employee_id', name='uq_ke_payroll_line'),
    )
    op.create_index('ix_ke_payroll_lines_run_id', 'ke_payroll_lines', ['run_id'])
    op.create_index('ix_ke_payroll_lines_employee_id', 'ke_payroll_lines', ['employee_id'])

    # ke_payslips
    op.create_table(
        'ke_payslips',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('payroll_line_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('ke_payroll_lines.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('hr_employees.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('ke_payroll_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('is_sent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_ke_payslips_employee_id', 'ke_payslips', ['employee_id'])
    op.create_index('ix_ke_payslips_run_id', 'ke_payslips', ['run_id'])


def downgrade() -> None:
    op.drop_table('ke_payslips')
    op.drop_table('ke_payroll_lines')
    op.drop_table('ke_payroll_runs')
    op.drop_table('ke_nhif_tiers')
    op.drop_table('ke_statutory_rates')
    op.drop_table('ke_tax_bands')
    op.drop_table('ke_payroll_profiles')
    op.execute("DROP TYPE IF EXISTS payrollrunstatus")
    op.execute("DROP TYPE IF EXISTS kecomponenttype")
    op.execute("DROP TYPE IF EXISTS payfrequency")
