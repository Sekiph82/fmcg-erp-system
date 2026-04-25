"""Landed Cost Allocation System

Revision ID: c5d6e7f8a9b0
Revises: 4a1b1eba5eed
Create Date: 2026-04-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c5d6e7f8a9b0'
down_revision = '4a1b1eba5eed'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── lc_headers ────────────────────────────────────────────────────────────
    op.create_table(
        'lc_headers',
        sa.Column('id',                  sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('lc_no',               sa.String(50),  nullable=False, unique=True),
        sa.Column('reference_type',      sa.String(30),  nullable=False, server_default='MANUAL'),
        sa.Column('shipment_id',         sa.UUID(as_uuid=True), sa.ForeignKey('intl_shipments.id'), nullable=True),
        sa.Column('po_id',               sa.UUID(as_uuid=True), sa.ForeignKey('purchase_orders.id'), nullable=True),
        sa.Column('vendor_name',         sa.String(200), nullable=True),
        sa.Column('bill_no',             sa.String(100), nullable=True),
        sa.Column('bill_date',           sa.Date(),      nullable=True),
        sa.Column('currency_code',       sa.String(10),  nullable=False, server_default='USD'),
        sa.Column('exchange_rate',       sa.Numeric(14, 6), nullable=False, server_default='1'),
        sa.Column('total_lc_amount_fc',  sa.Numeric(14, 4), nullable=False, server_default='0'),
        sa.Column('total_lc_amount_base',sa.Numeric(14, 4), nullable=False, server_default='0'),
        sa.Column('allocation_method',   sa.String(30),  nullable=False, server_default='BY_VALUE'),
        sa.Column('status',              sa.String(20),  nullable=False, server_default='DRAFT'),
        sa.Column('posted_at',           sa.DateTime(),  nullable=True),
        sa.Column('posted_by',           sa.String(150), nullable=True),
        sa.Column('notes',               sa.Text(),      nullable=True),
        sa.Column('created_at',          sa.DateTime(),  nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at',          sa.DateTime(),  nullable=False, server_default=sa.func.now()),
    )

    # ── lc_lines ──────────────────────────────────────────────────────────────
    op.create_table(
        'lc_lines',
        sa.Column('id',           sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('header_id',    sa.UUID(as_uuid=True), sa.ForeignKey('lc_headers.id'), nullable=False),
        sa.Column('cost_type',    sa.String(30),  nullable=False),
        sa.Column('description',  sa.String(300), nullable=True),
        sa.Column('vendor_name',  sa.String(200), nullable=True),
        sa.Column('amount_fc',    sa.Numeric(14, 4), nullable=False, server_default='0'),
        sa.Column('currency_code',sa.String(10),  nullable=False, server_default='USD'),
        sa.Column('exchange_rate',sa.Numeric(14, 6), nullable=False, server_default='1'),
        sa.Column('amount_base',  sa.Numeric(14, 4), nullable=False, server_default='0'),
        sa.Column('allocation_method', sa.String(30), nullable=True),
        sa.Column('is_included_in_valuation', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('account_code', sa.String(50),  nullable=True),
        sa.Column('remarks',      sa.Text(),       nullable=True),
        sa.Column('created_at',   sa.DateTime(),   nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at',   sa.DateTime(),   nullable=False, server_default=sa.func.now()),
    )

    # ── lc_grn_links ──────────────────────────────────────────────────────────
    op.create_table(
        'lc_grn_links',
        sa.Column('id',               sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('header_id',        sa.UUID(as_uuid=True), sa.ForeignKey('lc_headers.id'), nullable=False),
        sa.Column('grn_id',           sa.UUID(as_uuid=True), sa.ForeignKey('goods_receipts.id'), nullable=False),
        sa.Column('grn_no',           sa.String(50),  nullable=True),
        sa.Column('po_no',            sa.String(50),  nullable=True),
        sa.Column('grn_value_base',   sa.Numeric(14, 4), nullable=True),
        sa.Column('grn_total_qty',    sa.Numeric(14, 3), nullable=True),
        sa.Column('grn_total_weight', sa.Numeric(14, 3), nullable=True),
        sa.Column('grn_total_volume', sa.Numeric(14, 3), nullable=True),
        sa.Column('allocation_share', sa.Numeric(7, 4),  nullable=True),
        sa.Column('created_at',       sa.DateTime(),   nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at',       sa.DateTime(),   nullable=False, server_default=sa.func.now()),
    )

    # ── lc_inventory_adjustments (must exist before lc_allocation_lines FK) ──
    op.create_table(
        'lc_inventory_adjustments',
        sa.Column('id',                sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('header_id',         sa.UUID(as_uuid=True), sa.ForeignKey('lc_headers.id'), nullable=False),
        sa.Column('grn_line_id',       sa.UUID(as_uuid=True), sa.ForeignKey('grn_lines.id'), nullable=True),
        sa.Column('material_id',       sa.UUID(as_uuid=True), sa.ForeignKey('materials.id'), nullable=True),
        sa.Column('lot_no',            sa.String(100), nullable=True),
        sa.Column('adjustment_amount', sa.Numeric(14, 4), nullable=False, server_default='0'),
        sa.Column('per_unit_amount',   sa.Numeric(14, 6), nullable=True),
        sa.Column('qty_on_hand',       sa.Numeric(14, 3), nullable=True),
        sa.Column('old_avg_cost',      sa.Numeric(14, 6), nullable=True),
        sa.Column('new_avg_cost',      sa.Numeric(14, 6), nullable=True),
        sa.Column('journal_ref',       sa.String(100), nullable=True),
        sa.Column('posted_at',         sa.DateTime(),  nullable=True),
        sa.Column('created_at',        sa.DateTime(),  nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at',        sa.DateTime(),  nullable=False, server_default=sa.func.now()),
    )

    # ── lc_allocation_lines ───────────────────────────────────────────────────
    op.create_table(
        'lc_allocation_lines',
        sa.Column('id',               sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('header_id',        sa.UUID(as_uuid=True), sa.ForeignKey('lc_headers.id'), nullable=False),
        sa.Column('lc_line_id',       sa.UUID(as_uuid=True), sa.ForeignKey('lc_lines.id'), nullable=False),
        sa.Column('grn_id',           sa.UUID(as_uuid=True), sa.ForeignKey('goods_receipts.id'), nullable=True),
        sa.Column('grn_line_id',      sa.UUID(as_uuid=True), sa.ForeignKey('grn_lines.id'), nullable=True),
        sa.Column('material_id',      sa.UUID(as_uuid=True), sa.ForeignKey('materials.id'), nullable=True),
        sa.Column('material_name',    sa.String(200), nullable=True),
        sa.Column('lot_no',           sa.String(100), nullable=True),
        sa.Column('received_qty',     sa.Numeric(14, 3), nullable=True),
        sa.Column('received_weight',  sa.Numeric(14, 3), nullable=True),
        sa.Column('received_volume',  sa.Numeric(14, 3), nullable=True),
        sa.Column('purchase_value',   sa.Numeric(14, 4), nullable=True),
        sa.Column('allocation_basis', sa.Numeric(14, 6), nullable=True),
        sa.Column('allocation_share', sa.Numeric(7, 4),  nullable=True),
        sa.Column('allocated_amount', sa.Numeric(14, 4), nullable=False, server_default='0'),
        sa.Column('per_unit_lc_cost', sa.Numeric(14, 6), nullable=True),
        sa.Column('is_posted',        sa.Boolean(),    nullable=False, server_default='false'),
        sa.Column('inventory_adj_id', sa.UUID(as_uuid=True), sa.ForeignKey('lc_inventory_adjustments.id'), nullable=True),
        sa.Column('created_at',       sa.DateTime(),   nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at',       sa.DateTime(),   nullable=False, server_default=sa.func.now()),
    )

    # ── lc_ai_recommendations ────────────────────────────────────────────────
    op.create_table(
        'lc_ai_recommendations',
        sa.Column('id',               sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('header_id',        sa.UUID(as_uuid=True), sa.ForeignKey('lc_headers.id'), nullable=True),
        sa.Column('agent_type',       sa.String(30),   nullable=False),
        sa.Column('status',           sa.String(20),   nullable=False, server_default='PENDING'),
        sa.Column('title',            sa.String(300),  nullable=False),
        sa.Column('explanation',      sa.Text(),       nullable=True),
        sa.Column('impact_summary',   sa.Text(),       nullable=True),
        sa.Column('suggested_action', sa.Text(),       nullable=True),
        sa.Column('confidence_score', sa.Numeric(5, 2),nullable=True),
        sa.Column('data_snapshot',    sa.JSON(),       nullable=True),
        sa.Column('actioned_at',      sa.DateTime(),   nullable=True),
        sa.Column('actioned_by',      sa.String(150),  nullable=True),
        sa.Column('created_at',       sa.DateTime(),   nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at',       sa.DateTime(),   nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('lc_ai_recommendations')
    op.drop_table('lc_allocation_lines')
    op.drop_table('lc_inventory_adjustments')
    op.drop_table('lc_grn_links')
    op.drop_table('lc_lines')
    op.drop_table('lc_headers')
