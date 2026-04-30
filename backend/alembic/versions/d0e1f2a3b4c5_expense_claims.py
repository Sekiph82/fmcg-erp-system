"""expense_claims

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-04-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'd0e1f2a3b4c5'
down_revision = 'c9d0e1f2a3b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'expense_categories',
        sa.Column('expense_category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_code', sa.String(30), nullable=False),
        sa.Column('category_name', sa.String(100), nullable=False),
        sa.Column('default_gl_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('default_cost_center_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('receipt_required_flag', sa.Boolean(), nullable=True),
        sa.Column('approval_required_flag', sa.Boolean(), nullable=True),
        sa.Column('taxable_flag', sa.Boolean(), nullable=True),
        sa.Column('daily_limit_amount', sa.Numeric(14, 2), nullable=True),
        sa.Column('monthly_limit_amount', sa.Numeric(14, 2), nullable=True),
        sa.Column('active_flag', sa.Boolean(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('expense_category_id'),
        sa.UniqueConstraint('category_code'),
    )

    op.create_table(
        'expense_policies',
        sa.Column('expense_policy_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('policy_name', sa.String(150), nullable=False),
        sa.Column('employee_grade_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('max_amount_per_line', sa.Numeric(14, 2), nullable=True),
        sa.Column('max_amount_per_day', sa.Numeric(14, 2), nullable=True),
        sa.Column('max_amount_per_month', sa.Numeric(14, 2), nullable=True),
        sa.Column('receipt_required_above_amount', sa.Numeric(14, 2), nullable=True),
        sa.Column('approval_level_required', sa.Integer(), nullable=True),
        sa.Column('active_flag', sa.Boolean(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['expense_categories.expense_category_id']),
        sa.PrimaryKeyConstraint('expense_policy_id'),
    )

    op.create_table(
        'expense_advances',
        sa.Column('advance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('advance_no', sa.String(30), nullable=False),
        sa.Column('advance_date', sa.Date(), nullable=False),
        sa.Column('advance_amount', sa.Numeric(14, 2), nullable=False),
        sa.Column('settled_amount', sa.Numeric(14, 2), nullable=True),
        sa.Column('currency', sa.String(3), nullable=True),
        sa.Column('purpose', sa.String(255), nullable=True),
        sa.Column('settlement_status', sa.Enum('open', 'partially_settled', 'settled', 'overdue', name='advancesettlementstatus'), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('advance_id'),
        sa.UniqueConstraint('advance_no'),
    )

    op.create_table(
        'expense_claims',
        sa.Column('expense_claim_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('claim_no', sa.String(30), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('claim_date', sa.Date(), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=True),
        sa.Column('period_end', sa.Date(), nullable=True),
        sa.Column('currency', sa.String(3), nullable=True),
        sa.Column('total_claimed_amount', sa.Numeric(14, 2), nullable=True),
        sa.Column('total_approved_amount', sa.Numeric(14, 2), nullable=True),
        sa.Column('total_rejected_amount', sa.Numeric(14, 2), nullable=True),
        sa.Column('advance_deducted', sa.Numeric(14, 2), nullable=True),
        sa.Column('reimbursement_method', sa.Enum('payroll', 'ap', 'bank', 'cash', 'manual', name='reimbursementmethod'), nullable=True),
        sa.Column('status', sa.Enum('draft', 'submitted', 'manager_approved', 'finance_approved', 'rejected', 'paid', 'cancelled', name='expensestatus'), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('approved_by_manager', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('manager_approved_at', sa.DateTime(), nullable=True),
        sa.Column('approved_by_finance', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('finance_approved_at', sa.DateTime(), nullable=True),
        sa.Column('rejected_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('rejected_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('payment_reference', sa.String(100), nullable=True),
        sa.Column('advance_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['advance_id'], ['expense_advances.advance_id']),
        sa.PrimaryKeyConstraint('expense_claim_id'),
        sa.UniqueConstraint('claim_no'),
    )

    op.create_table(
        'expense_claim_lines',
        sa.Column('expense_line_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expense_claim_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expense_category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expense_date', sa.Date(), nullable=False),
        sa.Column('description', sa.String(255), nullable=False),
        sa.Column('vendor_name', sa.String(150), nullable=True),
        sa.Column('receipt_no', sa.String(100), nullable=True),
        sa.Column('claimed_amount', sa.Numeric(14, 2), nullable=False),
        sa.Column('approved_amount', sa.Numeric(14, 2), nullable=True),
        sa.Column('tax_amount', sa.Numeric(14, 2), nullable=True),
        sa.Column('currency', sa.String(3), nullable=True),
        sa.Column('payment_method_used', sa.String(50), nullable=True),
        sa.Column('cost_center_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('sales_route_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('attachment_ref', sa.String(500), nullable=True),
        sa.Column('policy_violation_flag', sa.Boolean(), nullable=True),
        sa.Column('policy_violation_note', sa.Text(), nullable=True),
        sa.Column('policy_violation_severity', sa.Enum('warning', 'block', name='policyviolationseverity'), nullable=True),
        sa.Column('line_status', sa.String(30), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['expense_category_id'], ['expense_categories.expense_category_id']),
        sa.ForeignKeyConstraint(['expense_claim_id'], ['expense_claims.expense_claim_id']),
        sa.PrimaryKeyConstraint('expense_line_id'),
    )

    op.create_table(
        'expense_accounting_entries',
        sa.Column('entry_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expense_claim_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entry_date', sa.Date(), nullable=False),
        sa.Column('debit_account', sa.String(100), nullable=False),
        sa.Column('credit_account', sa.String(100), nullable=False),
        sa.Column('amount', sa.Numeric(14, 2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(14, 2), nullable=True),
        sa.Column('cost_center_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('posted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['expense_claim_id'], ['expense_claims.expense_claim_id']),
        sa.PrimaryKeyConstraint('entry_id'),
    )

    op.create_table(
        'exp_ai_recommendations',
        sa.Column('rec_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_type', sa.Enum('risk_monitor', 'policy_optimizer', 'reimbursement_assistant', name='expaiagenttype'), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('ref_expense_claim_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ref_employee_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.Enum('pending', 'acknowledged', 'dismissed', 'actioned', name='expairecstatus'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('actioned_at', sa.DateTime(), nullable=True),
        sa.Column('actioned_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('rec_id'),
    )


def downgrade() -> None:
    op.drop_table('exp_ai_recommendations')
    op.drop_table('expense_accounting_entries')
    op.drop_table('expense_claim_lines')
    op.drop_table('expense_claims')
    op.drop_table('expense_advances')
    op.drop_table('expense_policies')
    op.drop_table('expense_categories')
    op.execute("DROP TYPE IF EXISTS expaiagenttype")
    op.execute("DROP TYPE IF EXISTS expairecstatus")
    op.execute("DROP TYPE IF EXISTS expensestatus")
    op.execute("DROP TYPE IF EXISTS reimbursementmethod")
    op.execute("DROP TYPE IF EXISTS advancesettlementstatus")
    op.execute("DROP TYPE IF EXISTS policyviolationseverity")
