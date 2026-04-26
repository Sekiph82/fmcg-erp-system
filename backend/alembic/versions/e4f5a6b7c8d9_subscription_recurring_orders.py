"""subscription_recurring_orders

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-04-26 15:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'e4f5a6b7c8d9'
down_revision = 'd3e4f5a6b7c8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'subscription_templates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('template_code', sa.String(50), nullable=False),
        sa.Column('template_name', sa.String(200), nullable=False),
        sa.Column('customer_id', sa.UUID(), nullable=False),
        sa.Column('distributor_id', sa.UUID(), nullable=True),
        sa.Column('price_list_id', sa.UUID(), nullable=True),
        sa.Column('contract_id', sa.UUID(), nullable=True),
        sa.Column('currency', sa.String(3), nullable=True),
        sa.Column('recurrence_type', sa.String(50), nullable=False),
        sa.Column('recurrence_interval', sa.Integer(), nullable=True),
        sa.Column('recurrence_day_of_month', sa.Integer(), nullable=True),
        sa.Column('recurrence_weekday', sa.Integer(), nullable=True),
        sa.Column('recurrence_week_ordinal', sa.Integer(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('next_generation_date', sa.Date(), nullable=True),
        sa.Column('last_generation_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('generation_mode', sa.String(50), nullable=False),
        sa.Column('delivery_address_id', sa.UUID(), nullable=True),
        sa.Column('route_id', sa.UUID(), nullable=True),
        sa.Column('payment_terms_id', sa.UUID(), nullable=True),
        sa.Column('allow_promotion_eval', sa.Boolean(), nullable=True),
        sa.Column('price_change_threshold_pct', sa.Numeric(5, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('approved_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.ForeignKeyConstraint(['distributor_id'], ['distributors.id']),
        sa.ForeignKeyConstraint(['route_id'], ['sales_routes.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('template_code'),
    )
    op.create_index('ix_subscription_templates_template_code', 'subscription_templates', ['template_code'])

    op.create_table(
        'subscription_lines',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('template_id', sa.UUID(), nullable=False),
        sa.Column('item_id', sa.UUID(), nullable=False),
        sa.Column('item_variant_id', sa.UUID(), nullable=True),
        sa.Column('uom', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Numeric(14, 3), nullable=False),
        sa.Column('min_quantity', sa.Numeric(14, 3), nullable=True),
        sa.Column('max_quantity', sa.Numeric(14, 3), nullable=True),
        sa.Column('allow_quantity_change', sa.Boolean(), nullable=True),
        sa.Column('price_source', sa.String(50), nullable=False),
        sa.Column('fixed_price', sa.Numeric(14, 4), nullable=True),
        sa.Column('active_flag', sa.Boolean(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['subscription_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'subscription_generation_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('template_id', sa.UUID(), nullable=False),
        sa.Column('generated_so_id', sa.UUID(), nullable=True),
        sa.Column('scheduled_date', sa.Date(), nullable=False),
        sa.Column('actual_generation_date', sa.DateTime(), nullable=True),
        sa.Column('generation_status', sa.String(50), nullable=False),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('validation_warnings', sa.JSON(), nullable=True),
        sa.Column('generated_by_system', sa.Boolean(), nullable=True),
        sa.Column('generated_by_user_id', sa.UUID(), nullable=True),
        sa.Column('reviewed_by', sa.UUID(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['subscription_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['generated_so_id'], ['sales_orders.id']),
        sa.ForeignKeyConstraint(['generated_by_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('template_id', 'scheduled_date', name='uq_sub_gen_template_date'),
    )

    op.create_table(
        'subscription_pause_skips',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('template_id', sa.UUID(), nullable=False),
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('requested_by', sa.UUID(), nullable=True),
        sa.Column('approved_by', sa.UUID(), nullable=True),
        sa.Column('portal_request', sa.Boolean(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['subscription_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'subscription_ai_recommendations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('agent_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('severity', sa.String(20), nullable=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('template_id', sa.UUID(), nullable=True),
        sa.Column('customer_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['subscription_templates.id']),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('subscription_ai_recommendations')
    op.drop_table('subscription_pause_skips')
    op.drop_table('subscription_generation_logs')
    op.drop_table('subscription_lines')
    op.drop_index('ix_subscription_templates_template_code', 'subscription_templates')
    op.drop_table('subscription_templates')
