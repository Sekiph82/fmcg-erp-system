"""sales_commission_tracking

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-04-26 19:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'c9d0e1f2a3b4'
down_revision = 'b8c9d0e1f2a3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'commission_rules',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('rule_code', sa.String(50), nullable=False),
        sa.Column('rule_name', sa.String(200), nullable=False),
        sa.Column('applies_to', sa.String(30), nullable=False),
        sa.Column('applicable_scope', sa.String(30), nullable=False, server_default='GLOBAL'),
        sa.Column('scope_ref_id', sa.UUID(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='DRAFT'),
        sa.Column('contract_id', sa.UUID(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rule_code'),
    )
    op.create_index('ix_commission_rules_rule_code', 'commission_rules', ['rule_code'])

    op.create_table(
        'commission_rule_lines',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('rule_id', sa.UUID(), nullable=False),
        sa.Column('condition_type', sa.String(30), nullable=False),
        sa.Column('min_threshold', sa.Numeric(18, 4), nullable=True),
        sa.Column('max_threshold', sa.Numeric(18, 4), nullable=True),
        sa.Column('commission_type', sa.String(30), nullable=False, server_default='PERCENTAGE'),
        sa.Column('commission_value', sa.Numeric(10, 4), nullable=False),
        sa.Column('target_flag', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('sort_order', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['rule_id'], ['commission_rules.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'commission_targets',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=False),
        sa.Column('applies_to', sa.String(30), nullable=False),
        sa.Column('period', sa.String(20), nullable=False),
        sa.Column('target_value', sa.Numeric(18, 4), nullable=False),
        sa.Column('actual_value', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('achievement_pct', sa.Numeric(7, 3), nullable=True),
        sa.Column('bonus_earned', sa.Numeric(14, 4), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entity_id', 'period', 'applies_to', name='uq_cm_target'),
    )

    op.create_table(
        'commission_txns',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('rule_id', sa.UUID(), nullable=True),
        sa.Column('sales_order_id', sa.UUID(), nullable=True),
        sa.Column('invoice_id', sa.UUID(), nullable=True),
        sa.Column('sales_rep_id', sa.UUID(), nullable=True),
        sa.Column('distributor_id', sa.UUID(), nullable=True),
        sa.Column('customer_id', sa.UUID(), nullable=True),
        sa.Column('base_amount', sa.Numeric(14, 2), nullable=False),
        sa.Column('commission_pct', sa.Numeric(7, 4), nullable=True),
        sa.Column('commission_amount', sa.Numeric(14, 4), nullable=False),
        sa.Column('calculation_date', sa.Date(), nullable=False),
        sa.Column('period', sa.String(20), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='PENDING'),
        sa.Column('is_reversal', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('calc_detail', sa.JSON(), nullable=True),
        sa.Column('approved_by', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['rule_id'], ['commission_rules.id']),
        sa.ForeignKeyConstraint(['sales_order_id'], ['sales_orders.id']),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id']),
        sa.ForeignKeyConstraint(['sales_rep_id'], ['users.id']),
        sa.ForeignKeyConstraint(['distributor_id'], ['distributors.id']),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'commission_adjustments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('txn_id', sa.UUID(), nullable=False),
        sa.Column('adjustment_amount', sa.Numeric(14, 4), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('approved_by', sa.UUID(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['txn_id'], ['commission_txns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'commission_payouts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=False),
        sa.Column('applies_to', sa.String(30), nullable=False),
        sa.Column('period', sa.String(20), nullable=False),
        sa.Column('total_commission', sa.Numeric(14, 4), nullable=False, server_default='0'),
        sa.Column('adjustments_total', sa.Numeric(14, 4), nullable=False, server_default='0'),
        sa.Column('net_commission', sa.Numeric(14, 4), nullable=False, server_default='0'),
        sa.Column('paid_amount', sa.Numeric(14, 4), nullable=False, server_default='0'),
        sa.Column('payment_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='DRAFT'),
        sa.Column('txn_ids', sa.JSON(), nullable=True),
        sa.Column('approved_by', sa.UUID(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entity_id', 'period', 'applies_to', name='uq_cm_payout_period'),
    )

    op.create_table(
        'cm_ai_recommendations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('agent_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('severity', sa.String(20), nullable=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('entity_id', sa.UUID(), nullable=True),
        sa.Column('rule_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['rule_id'], ['commission_rules.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('cm_ai_recommendations')
    op.drop_table('commission_payouts')
    op.drop_table('commission_adjustments')
    op.drop_table('commission_txns')
    op.drop_table('commission_targets')
    op.drop_table('commission_rule_lines')
    op.drop_index('ix_commission_rules_rule_code', 'commission_rules')
    op.drop_table('commission_rules')
