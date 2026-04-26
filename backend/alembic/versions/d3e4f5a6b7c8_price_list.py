"""price_list_enhancement

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-04-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'd3e4f5a6b7c8'
down_revision = 'c2d3e4f5a6b7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'pl_headers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('price_list_code', sa.String(50), nullable=False, unique=True),
        sa.Column('price_list_name', sa.String(200), nullable=False),
        sa.Column('currency', sa.String(10), nullable=False, server_default='KES'),
        sa.Column('pl_type', sa.String(30), nullable=False, server_default='STANDARD'),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('channel', sa.String(80), nullable=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('distributor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('distributors.id'), nullable=True),
        sa.Column('valid_from', sa.Date(), nullable=False),
        sa.Column('valid_to', sa.Date(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='DRAFT'),
        sa.Column('priority_rank', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('default_flag', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('linked_promo_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('minimum_margin_pct', sa.Numeric(6, 2), nullable=True),
        sa.Column('max_manual_discount', sa.Numeric(6, 2), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=True),
        sa.Column('approved_by', sa.String(200), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'pl_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('header_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pl_headers.id'), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('brand', sa.String(100), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('uom', sa.String(20), nullable=False, server_default='KG'),
        sa.Column('base_price', sa.Numeric(14, 4), nullable=False),
        sa.Column('minimum_price', sa.Numeric(14, 4), nullable=True),
        sa.Column('recommended_price', sa.Numeric(14, 4), nullable=True),
        sa.Column('currency', sa.String(10), nullable=False, server_default='KES'),
        sa.Column('tax_included_flag', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_to', sa.Date(), nullable=True),
        sa.Column('active_flag', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('header_id', 'product_id', 'uom', name='uq_pl_line'),
    )

    op.create_table(
        'pl_tiers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('line_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pl_lines.id'), nullable=False),
        sa.Column('min_qty', sa.Numeric(14, 3), nullable=False),
        sa.Column('max_qty', sa.Numeric(14, 3), nullable=True),
        sa.Column('unit_price', sa.Numeric(14, 4), nullable=True),
        sa.Column('discount_pct', sa.Numeric(6, 3), nullable=True),
        sa.Column('fixed_discount_amount', sa.Numeric(14, 4), nullable=True),
        sa.Column('effective_margin_pct', sa.Numeric(6, 2), nullable=True),
        sa.Column('active_flag', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'pl_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('header_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pl_headers.id'), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('distributor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('distributors.id'), nullable=True),
        sa.Column('channel', sa.String(80), nullable=True),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('segment', sa.String(100), nullable=True),
        sa.Column('valid_from', sa.Date(), nullable=False),
        sa.Column('valid_to', sa.Date(), nullable=True),
        sa.Column('priority_rank', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('active_flag', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'pl_discount_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('rule_code', sa.String(50), nullable=False, unique=True),
        sa.Column('rule_name', sa.String(200), nullable=False),
        sa.Column('scope', sa.String(20), nullable=False, server_default='LINE'),
        sa.Column('discount_type', sa.String(20), nullable=False),
        sa.Column('discount_value', sa.Numeric(14, 4), nullable=False),
        sa.Column('max_discount_pct', sa.Numeric(6, 2), nullable=True),
        sa.Column('requires_approval', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('min_margin_pct', sa.Numeric(6, 2), nullable=True),
        sa.Column('applies_to_pl_type', sa.String(40), nullable=True),
        sa.Column('applies_to_channel', sa.String(80), nullable=True),
        sa.Column('applies_to_customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('reason_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_to', sa.Date(), nullable=True),
        sa.Column('active_flag', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'pl_approvals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('header_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pl_headers.id'), nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('submitted_by', sa.String(200), nullable=False),
        sa.Column('reviewed_by', sa.String(200), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'pl_change_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('header_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pl_headers.id'), nullable=False),
        sa.Column('line_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('change_type', sa.String(30), nullable=False),
        sa.Column('changed_by', sa.String(200), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('old_value_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('new_value_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
    )

    op.create_table(
        'pl_ai_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('header_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pl_headers.id'), nullable=True),
        sa.Column('line_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('agent_type', sa.String(40), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False, server_default='INFO'),
        sa.Column('reference_type', sa.String(80), nullable=True),
        sa.Column('reference_id', sa.String(80), nullable=True),
        sa.Column('actioned_by', sa.String(200), nullable=True),
        sa.Column('actioned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('pl_ai_recommendations')
    op.drop_table('pl_change_history')
    op.drop_table('pl_approvals')
    op.drop_table('pl_discount_rules')
    op.drop_table('pl_assignments')
    op.drop_table('pl_tiers')
    op.drop_table('pl_lines')
    op.drop_table('pl_headers')
