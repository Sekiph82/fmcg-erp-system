"""subcontracting_system

Revision ID: 4a1b1eba5eed
Revises: 4cddbd375e74
Create Date: 2026-04-25 09:02:57.060510

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4a1b1eba5eed'
down_revision: Union[str, None] = '4cddbd375e74'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'subcontractor_locations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('supplier_id', sa.UUID(), nullable=False),
        sa.Column('warehouse_id', sa.UUID(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('supplier_id'),
        sa.UniqueConstraint('warehouse_id'),
    )

    op.create_table(
        'subcontract_orders',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('order_no', sa.String(50), nullable=False),
        sa.Column('supplier_id', sa.UUID(), nullable=False),
        sa.Column('order_date', sa.Date(), nullable=False),
        sa.Column('expected_completion_date', sa.Date(), nullable=True),
        sa.Column('actual_completion_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('linked_po_id', sa.UUID(), nullable=True),
        sa.Column('warehouse_id', sa.UUID(), nullable=True),
        sa.Column('subcontractor_location_id', sa.UUID(), nullable=True),
        sa.Column('total_material_cost', sa.Numeric(16, 4), nullable=True),
        sa.Column('total_service_cost', sa.Numeric(16, 4), nullable=True),
        sa.Column('total_wastage_cost', sa.Numeric(16, 4), nullable=True),
        sa.Column('currency', sa.String(10), nullable=False, server_default='KES'),
        sa.Column('approved_by_id', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['linked_po_id'], ['purchase_orders.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['subcontractor_location_id'], ['subcontractor_locations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_no'),
    )
    op.create_index('ix_subcontract_orders_order_no', 'subcontract_orders', ['order_no'])
    op.create_index('ix_subcontract_orders_supplier_id', 'subcontract_orders', ['supplier_id'])

    op.create_table(
        'subcontract_order_lines',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('order_id', sa.UUID(), nullable=False),
        sa.Column('line_no', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=True),
        sa.Column('material_id', sa.UUID(), nullable=True),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('quantity_ordered', sa.Numeric(14, 3), nullable=False),
        sa.Column('quantity_received', sa.Numeric(14, 3), nullable=False, server_default='0'),
        sa.Column('uom', sa.String(20), nullable=False, server_default='KG'),
        sa.Column('bom_id', sa.UUID(), nullable=True),
        sa.Column('service_unit_cost', sa.Numeric(14, 4), nullable=True),
        sa.Column('estimated_yield_pct', sa.Numeric(7, 3), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['subcontract_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['bom_id'], ['advanced_boms.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id', 'line_no', name='uq_sc_order_line'),
    )

    op.create_table(
        'subcontract_material_issues',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('issue_no', sa.String(50), nullable=False),
        sa.Column('order_id', sa.UUID(), nullable=False),
        sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('issued_by_id', sa.UUID(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['subcontract_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['issued_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('issue_no'),
    )
    op.create_index('ix_subcontract_material_issues_issue_no', 'subcontract_material_issues', ['issue_no'])

    op.create_table(
        'subcontract_material_issue_lines',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('issue_id', sa.UUID(), nullable=False),
        sa.Column('line_no', sa.Integer(), nullable=False),
        sa.Column('material_id', sa.UUID(), nullable=False),
        sa.Column('lot_id', sa.UUID(), nullable=True),
        sa.Column('quantity_issued', sa.Numeric(14, 3), nullable=False),
        sa.Column('quantity_returned', sa.Numeric(14, 3), nullable=False, server_default='0'),
        sa.Column('quantity_consumed', sa.Numeric(14, 3), nullable=False, server_default='0'),
        sa.Column('quantity_scrapped', sa.Numeric(14, 3), nullable=False, server_default='0'),
        sa.Column('uom', sa.String(20), nullable=False, server_default='KG'),
        sa.Column('unit_cost', sa.Numeric(14, 4), nullable=True),
        sa.Column('stock_movement_id', sa.UUID(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['issue_id'], ['subcontract_material_issues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['lot_id'], ['lots.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['stock_movement_id'], ['stock_movements.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('issue_id', 'line_no', name='uq_sc_issue_line'),
    )

    op.create_table(
        'subcontract_receipts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('receipt_no', sa.String(50), nullable=False),
        sa.Column('order_id', sa.UUID(), nullable=False),
        sa.Column('receipt_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('received_by_id', sa.UUID(), nullable=True),
        sa.Column('qc_inspection_id', sa.UUID(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['subcontract_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['received_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['qc_inspection_id'], ['qc_inspections.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('receipt_no'),
    )
    op.create_index('ix_subcontract_receipts_receipt_no', 'subcontract_receipts', ['receipt_no'])

    op.create_table(
        'subcontract_receipt_lines',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('receipt_id', sa.UUID(), nullable=False),
        sa.Column('order_line_id', sa.UUID(), nullable=True),
        sa.Column('line_no', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=True),
        sa.Column('material_id', sa.UUID(), nullable=True),
        sa.Column('quantity_received', sa.Numeric(14, 3), nullable=False),
        sa.Column('quantity_accepted', sa.Numeric(14, 3), nullable=False, server_default='0'),
        sa.Column('quantity_rejected', sa.Numeric(14, 3), nullable=False, server_default='0'),
        sa.Column('uom', sa.String(20), nullable=False, server_default='KG'),
        sa.Column('lot_number', sa.String(100), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('unit_service_cost', sa.Numeric(14, 4), nullable=True),
        sa.Column('stock_movement_id', sa.UUID(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['receipt_id'], ['subcontract_receipts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_line_id'], ['subcontract_order_lines.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['stock_movement_id'], ['stock_movements.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('receipt_id', 'line_no', name='uq_sc_receipt_line'),
    )

    op.create_table(
        'subcontract_yield_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('order_id', sa.UUID(), nullable=False),
        sa.Column('order_line_id', sa.UUID(), nullable=False),
        sa.Column('total_material_issued', sa.Numeric(14, 3), nullable=False, server_default='0'),
        sa.Column('expected_material_input', sa.Numeric(14, 3), nullable=True),
        sa.Column('quantity_ordered', sa.Numeric(14, 3), nullable=False),
        sa.Column('quantity_received', sa.Numeric(14, 3), nullable=False, server_default='0'),
        sa.Column('expected_yield_pct', sa.Numeric(7, 3), nullable=True),
        sa.Column('actual_yield_pct', sa.Numeric(7, 3), nullable=True),
        sa.Column('yield_variance_pct', sa.Numeric(7, 3), nullable=True),
        sa.Column('yield_status', sa.String(50), nullable=False),
        sa.Column('total_scrapped', sa.Numeric(14, 3), nullable=False, server_default='0'),
        sa.Column('scrap_reason', sa.String(50), nullable=True),
        sa.Column('scrap_cost', sa.Numeric(14, 4), nullable=True),
        sa.Column('material_variance_qty', sa.Numeric(14, 3), nullable=True),
        sa.Column('material_variance_cost', sa.Numeric(14, 4), nullable=True),
        sa.Column('is_abnormal', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['subcontract_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_line_id'], ['subcontract_order_lines.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id', 'order_line_id', name='uq_sc_yield'),
    )

    op.create_table(
        'sc_performance_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('order_id', sa.UUID(), nullable=False),
        sa.Column('supplier_id', sa.UUID(), nullable=False),
        sa.Column('planned_completion', sa.Date(), nullable=True),
        sa.Column('actual_completion', sa.Date(), nullable=True),
        sa.Column('delay_days', sa.Integer(), nullable=True),
        sa.Column('on_time', sa.Boolean(), nullable=True),
        sa.Column('total_qty_ordered', sa.Numeric(14, 3), nullable=False, server_default='0'),
        sa.Column('total_qty_received', sa.Numeric(14, 3), nullable=False, server_default='0'),
        sa.Column('total_qty_rejected', sa.Numeric(14, 3), nullable=False, server_default='0'),
        sa.Column('rejection_rate_pct', sa.Numeric(7, 3), nullable=True),
        sa.Column('avg_yield_pct', sa.Numeric(7, 3), nullable=True),
        sa.Column('budgeted_cost', sa.Numeric(16, 4), nullable=True),
        sa.Column('actual_cost', sa.Numeric(16, 4), nullable=True),
        sa.Column('cost_variance_pct', sa.Numeric(7, 3), nullable=True),
        sa.Column('performance_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['subcontract_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id', name='uq_sc_perf_order'),
    )

    op.create_table(
        'sc_ai_recommendations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('order_id', sa.UUID(), nullable=True),
        sa.Column('supplier_id', sa.UUID(), nullable=True),
        sa.Column('agent_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('recommendation', sa.Text(), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['subcontract_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('sc_ai_recommendations')
    op.drop_table('sc_performance_records')
    op.drop_table('subcontract_yield_records')
    op.drop_table('subcontract_receipt_lines')
    op.drop_table('subcontract_receipts')
    op.drop_table('subcontract_material_issue_lines')
    op.drop_table('subcontract_material_issues')
    op.drop_table('subcontract_order_lines')
    op.drop_table('subcontract_orders')
    op.drop_table('subcontractor_locations')
