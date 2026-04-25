"""bank_reconciliation

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-04-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'e7f8a9b0c1d2'
down_revision = 'd6e7f8a9b0c1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # br_bank_accounts
    op.create_table(
        'br_bank_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bank_name', sa.String(100), nullable=False),
        sa.Column('branch_name', sa.String(100), nullable=True),
        sa.Column('account_name', sa.String(255), nullable=False),
        sa.Column('account_number_masked', sa.String(50), nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, server_default='KES'),
        sa.Column('country', sa.String(2), nullable=False, server_default='KE'),
        sa.Column('account_type', sa.String(20), nullable=False, server_default='CURRENT'),
        sa.Column('reconciliation_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('mobile_money_flag', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('mpesa_till_or_paybill_no', sa.String(20), nullable=True),
        sa.Column('gl_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('cash_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['gl_account_id'], ['chart_of_accounts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['cash_account_id'], ['cash_accounts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # br_statements
    op.create_table(
        'br_statements',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('statement_no', sa.String(50), nullable=False),
        sa.Column('bank_account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('statement_date', sa.Date(), nullable=False),
        sa.Column('period_start_date', sa.Date(), nullable=False),
        sa.Column('period_end_date', sa.Date(), nullable=False),
        sa.Column('opening_balance', sa.Numeric(14, 4), nullable=False, server_default='0'),
        sa.Column('closing_balance', sa.Numeric(14, 4), nullable=False, server_default='0'),
        sa.Column('statement_currency', sa.String(3), nullable=False, server_default='KES'),
        sa.Column('import_source', sa.String(20), nullable=False, server_default='MANUAL'),
        sa.Column('import_file_name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='DRAFT'),
        sa.Column('imported_by', sa.String(100), nullable=True),
        sa.Column('imported_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_by', sa.String(100), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('total_credits', sa.Numeric(14, 4), nullable=False, server_default='0'),
        sa.Column('total_debits', sa.Numeric(14, 4), nullable=False, server_default='0'),
        sa.Column('total_lines', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['bank_account_id'], ['br_bank_accounts.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('statement_no'),
    )

    # br_statement_lines
    op.create_table(
        'br_statement_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('statement_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('line_no', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('value_date', sa.Date(), nullable=True),
        sa.Column('external_reference', sa.String(100), nullable=True),
        sa.Column('bank_reference', sa.String(100), nullable=True),
        sa.Column('narration', sa.Text(), nullable=True),
        sa.Column('counterparty_name', sa.String(255), nullable=True),
        sa.Column('amount', sa.Numeric(14, 4), nullable=False),
        sa.Column('debit_credit_indicator', sa.String(1), nullable=False, server_default='C'),
        sa.Column('running_balance', sa.Numeric(14, 4), nullable=True),
        sa.Column('normalized_reference', sa.String(100), nullable=True),
        sa.Column('normalized_narration', sa.String(500), nullable=True),
        sa.Column('match_status', sa.String(30), nullable=False, server_default='UNMATCHED'),
        sa.Column('matched_amount', sa.Numeric(14, 4), nullable=False, server_default='0'),
        sa.Column('unmatched_amount', sa.Numeric(14, 4), nullable=False, server_default='0'),
        sa.Column('reconciliation_notes', sa.Text(), nullable=True),
        sa.Column('is_duplicate_suspected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('raw_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['statement_id'], ['br_statements.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_br_stmt_lines_statement_id', 'br_statement_lines', ['statement_id'])
    op.create_index('ix_br_stmt_lines_match_status', 'br_statement_lines', ['match_status'])

    # br_rules
    op.create_table(
        'br_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bank_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('rule_name', sa.String(200), nullable=False),
        sa.Column('condition_type', sa.String(40), nullable=False),
        sa.Column('condition_value', sa.String(500), nullable=False),
        sa.Column('target_transaction_type', sa.String(30), nullable=False),
        sa.Column('auto_apply', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('confidence_weight', sa.Numeric(5, 4), nullable=False, server_default='0.8'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['bank_account_id'], ['br_bank_accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # br_matches
    op.create_table(
        'br_matches',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('statement_line_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('erp_transaction_type', sa.String(30), nullable=False),
        sa.Column('erp_transaction_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('erp_reference', sa.String(100), nullable=True),
        sa.Column('erp_transaction_date', sa.Date(), nullable=True),
        sa.Column('erp_amount', sa.Numeric(14, 4), nullable=True),
        sa.Column('erp_description', sa.String(500), nullable=True),
        sa.Column('matched_amount', sa.Numeric(14, 4), nullable=False),
        sa.Column('match_method', sa.String(20), nullable=False, server_default='MANUAL'),
        sa.Column('confidence_score', sa.Numeric(5, 4), nullable=True),
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('approved_by', sa.String(100), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['statement_line_id'], ['br_statement_lines.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rule_id'], ['br_rules.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_br_matches_line_id', 'br_matches', ['statement_line_id'])

    # br_adjustments
    op.create_table(
        'br_adjustments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('statement_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('statement_line_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('adjustment_type', sa.String(20), nullable=False),
        sa.Column('amount', sa.Numeric(14, 4), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('gl_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('auto_created', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('posted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('posted_by', sa.String(100), nullable=True),
        sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['statement_id'], ['br_statements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['statement_line_id'], ['br_statement_lines.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # br_ai_recommendations
    op.create_table(
        'br_ai_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('statement_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('statement_line_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('agent_type', sa.String(30), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('impact_summary', sa.String(500), nullable=True),
        sa.Column('suggested_action', sa.Text(), nullable=True),
        sa.Column('priority', sa.String(10), nullable=False, server_default='MEDIUM'),
        sa.Column('confidence_score', sa.Numeric(5, 4), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('actioned_by', sa.String(100), nullable=True),
        sa.Column('actioned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['statement_id'], ['br_statements.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['statement_line_id'], ['br_statement_lines.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('br_ai_recommendations')
    op.drop_table('br_adjustments')
    op.drop_index('ix_br_matches_line_id', table_name='br_matches')
    op.drop_table('br_matches')
    op.drop_table('br_rules')
    op.drop_index('ix_br_stmt_lines_match_status', table_name='br_statement_lines')
    op.drop_index('ix_br_stmt_lines_statement_id', table_name='br_statement_lines')
    op.drop_table('br_statement_lines')
    op.drop_table('br_statements')
    op.drop_table('br_bank_accounts')
