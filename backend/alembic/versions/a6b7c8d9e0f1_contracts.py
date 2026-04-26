"""contract_management

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-04-26 17:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'a6b7c8d9e0f1'
down_revision = 'f5a6b7c8d9e0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'contracts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('contract_code', sa.String(50), nullable=False),
        sa.Column('contract_name', sa.String(200), nullable=False),
        sa.Column('contract_type', sa.String(50), nullable=False),
        sa.Column('party_type', sa.String(30), nullable=False),
        sa.Column('party_id', sa.UUID(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='DRAFT'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='KES'),
        sa.Column('payment_terms_id', sa.UUID(), nullable=True),
        sa.Column('price_list_id', sa.UUID(), nullable=True),
        sa.Column('auto_renew', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('renewal_notice_days', sa.Integer(), nullable=True, server_default='30'),
        sa.Column('linked_promo_ids', sa.JSON(), nullable=True),
        sa.Column('linked_tpm_plan_id', sa.UUID(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('approved_by', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('terminated_by', sa.UUID(), nullable=True),
        sa.Column('terminated_at', sa.DateTime(), nullable=True),
        sa.Column('termination_reason', sa.Text(), nullable=True),
        sa.Column('current_version', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.ForeignKeyConstraint(['terminated_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('contract_code'),
    )
    op.create_index('ix_contracts_contract_code', 'contracts', ['contract_code'])
    op.create_index('ix_contracts_party_id', 'contracts', ['party_id'])

    op.create_table(
        'contract_terms',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('contract_id', sa.UUID(), nullable=False),
        sa.Column('term_type', sa.String(50), nullable=False),
        sa.Column('item_id', sa.UUID(), nullable=True),
        sa.Column('category_id', sa.UUID(), nullable=True),
        sa.Column('brand_id', sa.UUID(), nullable=True),
        sa.Column('value_type', sa.String(30), nullable=False, server_default='FIXED'),
        sa.Column('value', sa.Numeric(18, 4), nullable=False),
        sa.Column('min_threshold', sa.Numeric(18, 4), nullable=True),
        sa.Column('max_threshold', sa.Numeric(18, 4), nullable=True),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_to', sa.Date(), nullable=True),
        sa.Column('active_flag', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'contract_rebates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('contract_id', sa.UUID(), nullable=False),
        sa.Column('rebate_name', sa.String(100), nullable=True),
        sa.Column('rebate_type', sa.String(30), nullable=False, server_default='VOLUME'),
        sa.Column('calculation_basis', sa.String(30), nullable=False, server_default='INVOICE'),
        sa.Column('item_id', sa.UUID(), nullable=True),
        sa.Column('threshold', sa.Numeric(18, 4), nullable=True),
        sa.Column('rebate_pct', sa.Numeric(7, 4), nullable=True),
        sa.Column('rebate_amount', sa.Numeric(14, 4), nullable=True),
        sa.Column('settlement_frequency', sa.String(30), nullable=False, server_default='QUARTERLY'),
        sa.Column('accrued_amount', sa.Numeric(14, 4), nullable=False, server_default='0'),
        sa.Column('settled_amount', sa.Numeric(14, 4), nullable=False, server_default='0'),
        sa.Column('active_flag', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'contract_performance',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('contract_id', sa.UUID(), nullable=False),
        sa.Column('period', sa.String(20), nullable=False),
        sa.Column('target_value', sa.Numeric(18, 4), nullable=True),
        sa.Column('actual_value', sa.Numeric(18, 4), nullable=True),
        sa.Column('achievement_pct', sa.Numeric(7, 3), nullable=True),
        sa.Column('rebate_earned', sa.Numeric(14, 4), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='OPEN'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('contract_id', 'period', name='uq_contract_perf_period'),
    )

    op.create_table(
        'contract_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('contract_id', sa.UUID(), nullable=False),
        sa.Column('version_no', sa.Integer(), nullable=False),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column('snapshot', sa.JSON(), nullable=True),
        sa.Column('effective_date', sa.Date(), nullable=True),
        sa.Column('approved_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('contract_id', 'version_no', name='uq_contract_version'),
    )

    op.create_table(
        'contract_approvals',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('contract_id', sa.UUID(), nullable=False),
        sa.Column('action', sa.String(30), nullable=False),
        sa.Column('actioned_by', sa.UUID(), nullable=True),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['actioned_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'ct_ai_recommendations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('agent_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('severity', sa.String(20), nullable=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('contract_id', sa.UUID(), nullable=True),
        sa.Column('party_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('ct_ai_recommendations')
    op.drop_table('contract_approvals')
    op.drop_table('contract_versions')
    op.drop_table('contract_performance')
    op.drop_table('contract_rebates')
    op.drop_table('contract_terms')
    op.drop_index('ix_contracts_party_id', 'contracts')
    op.drop_index('ix_contracts_contract_code', 'contracts')
    op.drop_table('contracts')
