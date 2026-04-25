"""3-Way Invoice Matching System

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-04-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'd6e7f8a9b0c1'
down_revision = 'c5d6e7f8a9b0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── im_tolerance_rules ────────────────────────────────────────────────────
    op.create_table(
        'im_tolerance_rules',
        sa.Column('id',                            sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('rule_name',                     sa.String(200), nullable=False),
        sa.Column('supplier_id',                   sa.UUID(as_uuid=True), sa.ForeignKey('suppliers.id'), nullable=True),
        sa.Column('item_category',                 sa.String(100), nullable=True),
        sa.Column('quantity_tolerance_pct',        sa.Numeric(7, 3),  nullable=False, server_default='1'),
        sa.Column('quantity_tolerance_abs',        sa.Numeric(14, 3), nullable=True),
        sa.Column('price_tolerance_pct',           sa.Numeric(7, 3),  nullable=False, server_default='2'),
        sa.Column('price_tolerance_abs',           sa.Numeric(14, 4), nullable=True),
        sa.Column('tax_tolerance_pct',             sa.Numeric(7, 3),  nullable=False, server_default='0'),
        sa.Column('auto_approve_within_tolerance', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('block_payment_beyond_tolerance',sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('approval_role_required',        sa.String(100), nullable=True),
        sa.Column('is_active',                     sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('priority',                      sa.Integer(), nullable=False, server_default='10'),
        sa.Column('notes',                         sa.Text(),    nullable=True),
        sa.Column('created_at',                    sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at',                    sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # ── im_headers ────────────────────────────────────────────────────────────
    op.create_table(
        'im_headers',
        sa.Column('id',                  sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('match_no',            sa.String(50),  nullable=False, unique=True),
        sa.Column('invoice_id',          sa.UUID(as_uuid=True), sa.ForeignKey('purchase_invoices.id'), nullable=False),
        sa.Column('po_id',               sa.UUID(as_uuid=True), sa.ForeignKey('purchase_orders.id'), nullable=True),
        sa.Column('supplier_id',         sa.UUID(as_uuid=True), sa.ForeignKey('suppliers.id'), nullable=True),
        sa.Column('invoice_no',          sa.String(100), nullable=True),
        sa.Column('invoice_date',        sa.Date(),      nullable=True),
        sa.Column('currency',            sa.String(10),  nullable=False, server_default='USD'),
        sa.Column('invoice_total',       sa.Numeric(16, 4), nullable=False, server_default='0'),
        sa.Column('overall_status',      sa.String(40),  nullable=False, server_default='PENDING_REVIEW'),
        sa.Column('duplicate_flag',      sa.Boolean(),   nullable=False, server_default='false'),
        sa.Column('review_required',     sa.Boolean(),   nullable=False, server_default='false'),
        sa.Column('is_payable',          sa.Boolean(),   nullable=False, server_default='false'),
        sa.Column('payment_hold_reason', sa.Text(),      nullable=True),
        sa.Column('reviewed_by',         sa.String(150), nullable=True),
        sa.Column('reviewed_at',         sa.DateTime(),  nullable=True),
        sa.Column('approved_by',         sa.String(150), nullable=True),
        sa.Column('approved_at',         sa.DateTime(),  nullable=True),
        sa.Column('notes',               sa.Text(),      nullable=True),
        sa.Column('run_at',              sa.DateTime(),  nullable=True),
        sa.Column('created_at',          sa.DateTime(),  nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at',          sa.DateTime(),  nullable=False, server_default=sa.func.now()),
    )

    # ── im_lines ──────────────────────────────────────────────────────────────
    op.create_table(
        'im_lines',
        sa.Column('id',                 sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('header_id',          sa.UUID(as_uuid=True), sa.ForeignKey('im_headers.id'), nullable=False),
        sa.Column('invoice_line_id',    sa.UUID(as_uuid=True), sa.ForeignKey('purchase_invoice_lines.id'), nullable=True),
        sa.Column('po_line_id',         sa.UUID(as_uuid=True), sa.ForeignKey('po_lines.id'), nullable=True),
        sa.Column('material_id',        sa.UUID(as_uuid=True), sa.ForeignKey('materials.id'), nullable=True),
        sa.Column('material_name',      sa.String(200), nullable=True),
        sa.Column('description',        sa.String(300), nullable=True),
        sa.Column('ordered_qty',        sa.Numeric(14, 3), nullable=True),
        sa.Column('ordered_unit_price', sa.Numeric(14, 4), nullable=True),
        sa.Column('ordered_tax_rate',   sa.Numeric(6, 4),  nullable=True),
        sa.Column('total_received_qty', sa.Numeric(14, 3), nullable=True),
        sa.Column('total_accepted_qty', sa.Numeric(14, 3), nullable=True),
        sa.Column('prev_invoiced_qty',  sa.Numeric(14, 3), nullable=False, server_default='0'),
        sa.Column('billable_qty',       sa.Numeric(14, 3), nullable=True),
        sa.Column('invoiced_qty',       sa.Numeric(14, 3), nullable=True),
        sa.Column('invoiced_unit_price',sa.Numeric(14, 4), nullable=True),
        sa.Column('invoiced_tax_rate',  sa.Numeric(6, 4),  nullable=True),
        sa.Column('invoiced_line_total',sa.Numeric(16, 4), nullable=True),
        sa.Column('qty_variance',       sa.Numeric(14, 3), nullable=True),
        sa.Column('price_variance',     sa.Numeric(14, 4), nullable=True),
        sa.Column('tax_variance',       sa.Numeric(6, 4),  nullable=True),
        sa.Column('qty_variance_pct',   sa.Numeric(7, 3),  nullable=True),
        sa.Column('price_variance_pct', sa.Numeric(7, 3),  nullable=True),
        sa.Column('match_status',       sa.String(40),  nullable=False, server_default='PARTIAL_MATCH'),
        sa.Column('tolerance_rule_id',  sa.UUID(as_uuid=True), sa.ForeignKey('im_tolerance_rules.id'), nullable=True),
        sa.Column('action_required',    sa.Boolean(),   nullable=False, server_default='false'),
        sa.Column('notes',              sa.Text(),      nullable=True),
        sa.Column('created_at',         sa.DateTime(),  nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at',         sa.DateTime(),  nullable=False, server_default=sa.func.now()),
    )

    # ── im_grn_links ──────────────────────────────────────────────────────────
    op.create_table(
        'im_grn_links',
        sa.Column('id',            sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('match_line_id', sa.UUID(as_uuid=True), sa.ForeignKey('im_lines.id'), nullable=False),
        sa.Column('grn_id',        sa.UUID(as_uuid=True), sa.ForeignKey('goods_receipts.id'), nullable=True),
        sa.Column('grn_line_id',   sa.UUID(as_uuid=True), sa.ForeignKey('grn_lines.id'), nullable=True),
        sa.Column('grn_no',        sa.String(50),  nullable=True),
        sa.Column('received_qty',  sa.Numeric(14, 3), nullable=True),
        sa.Column('accepted_qty',  sa.Numeric(14, 3), nullable=True),
        sa.Column('rejected_qty',  sa.Numeric(14, 3), nullable=True),
        sa.Column('received_date', sa.Date(),      nullable=True),
        sa.Column('created_at',    sa.DateTime(),  nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at',    sa.DateTime(),  nullable=False, server_default=sa.func.now()),
    )

    # ── im_duplicate_logs ─────────────────────────────────────────────────────
    op.create_table(
        'im_duplicate_logs',
        sa.Column('id',                 sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('invoice_id',         sa.UUID(as_uuid=True), sa.ForeignKey('purchase_invoices.id'), nullable=False),
        sa.Column('matched_invoice_id', sa.UUID(as_uuid=True), sa.ForeignKey('purchase_invoices.id'), nullable=True),
        sa.Column('supplier_id',        sa.UUID(as_uuid=True), sa.ForeignKey('suppliers.id'), nullable=True),
        sa.Column('invoice_no',         sa.String(100), nullable=True),
        sa.Column('matched_invoice_no', sa.String(100), nullable=True),
        sa.Column('duplicate_risk',     sa.String(20),  nullable=False, server_default='SUSPECTED'),
        sa.Column('match_reasons',      sa.JSON(),      nullable=True),
        sa.Column('similarity_score',   sa.Numeric(5, 2), nullable=True),
        sa.Column('is_resolved',        sa.Boolean(),   nullable=False, server_default='false'),
        sa.Column('resolved_by',        sa.String(150), nullable=True),
        sa.Column('resolved_at',        sa.DateTime(),  nullable=True),
        sa.Column('resolution_notes',   sa.Text(),      nullable=True),
        sa.Column('created_at',         sa.DateTime(),  nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at',         sa.DateTime(),  nullable=False, server_default=sa.func.now()),
    )

    # ── im_reviews ────────────────────────────────────────────────────────────
    op.create_table(
        'im_reviews',
        sa.Column('id',              sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('header_id',       sa.UUID(as_uuid=True), sa.ForeignKey('im_headers.id'), nullable=False),
        sa.Column('action',          sa.String(30),  nullable=False),
        sa.Column('reviewer_name',   sa.String(150), nullable=False),
        sa.Column('reviewer_role',   sa.String(100), nullable=True),
        sa.Column('previous_status', sa.String(40),  nullable=True),
        sa.Column('new_status',      sa.String(40),  nullable=True),
        sa.Column('justification',   sa.Text(),      nullable=True),
        sa.Column('line_ids',        sa.JSON(),      nullable=True),
        sa.Column('created_at',      sa.DateTime(),  nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at',      sa.DateTime(),  nullable=False, server_default=sa.func.now()),
    )

    # ── im_ai_recommendations ─────────────────────────────────────────────────
    op.create_table(
        'im_ai_recommendations',
        sa.Column('id',               sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('header_id',        sa.UUID(as_uuid=True), sa.ForeignKey('im_headers.id'), nullable=True),
        sa.Column('agent_type',       sa.String(40),  nullable=False),
        sa.Column('status',           sa.String(20),  nullable=False, server_default='PENDING'),
        sa.Column('title',            sa.String(300), nullable=False),
        sa.Column('explanation',      sa.Text(),      nullable=True),
        sa.Column('impact_summary',   sa.Text(),      nullable=True),
        sa.Column('suggested_action', sa.Text(),      nullable=True),
        sa.Column('priority',         sa.String(10),  nullable=False, server_default='MEDIUM'),
        sa.Column('confidence_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('data_snapshot',    sa.JSON(),      nullable=True),
        sa.Column('actioned_at',      sa.DateTime(),  nullable=True),
        sa.Column('actioned_by',      sa.String(150), nullable=True),
        sa.Column('created_at',       sa.DateTime(),  nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at',       sa.DateTime(),  nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('im_ai_recommendations')
    op.drop_table('im_reviews')
    op.drop_table('im_duplicate_logs')
    op.drop_table('im_grn_links')
    op.drop_table('im_lines')
    op.drop_table('im_headers')
    op.drop_table('im_tolerance_rules')
