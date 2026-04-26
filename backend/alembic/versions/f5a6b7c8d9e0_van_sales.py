"""van_sales_mobile_pos

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-04-26 16:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'f5a6b7c8d9e0'
down_revision = 'e4f5a6b7c8d9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'vans',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('van_code', sa.String(50), nullable=False),
        sa.Column('plate_number', sa.String(30), nullable=True),
        sa.Column('driver_id', sa.UUID(), nullable=True),
        sa.Column('route_id', sa.UUID(), nullable=True),
        sa.Column('warehouse_id', sa.UUID(), nullable=True),
        sa.Column('capacity_kg', sa.Numeric(10, 2), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='ACTIVE'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['driver_id'], ['users.id']),
        sa.ForeignKeyConstraint(['route_id'], ['sales_routes.id']),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('van_code'),
    )
    op.create_index('ix_vans_van_code', 'vans', ['van_code'])

    op.create_table(
        'van_stock',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('van_id', sa.UUID(), nullable=False),
        sa.Column('item_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=True),
        sa.Column('quantity', sa.Numeric(14, 3), nullable=False, server_default='0'),
        sa.Column('reserved_qty', sa.Numeric(14, 3), nullable=False, server_default='0'),
        sa.Column('unit_cost', sa.Numeric(14, 4), nullable=True),
        sa.Column('uom', sa.String(20), nullable=False, server_default='PCS'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['van_id'], ['vans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['products.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['lots.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('van_id', 'item_id', 'batch_id', name='uq_van_stock_item_batch'),
    )

    op.create_table(
        'van_stock_movements',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('van_id', sa.UUID(), nullable=False),
        sa.Column('item_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=True),
        sa.Column('movement_type', sa.String(30), nullable=False),
        sa.Column('quantity', sa.Numeric(14, 3), nullable=False),
        sa.Column('reference_id', sa.UUID(), nullable=True),
        sa.Column('reference_no', sa.String(100), nullable=True),
        sa.Column('moved_by', sa.UUID(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['van_id'], ['vans.id']),
        sa.ForeignKeyConstraint(['item_id'], ['products.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['lots.id']),
        sa.ForeignKeyConstraint(['moved_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'van_visits',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('van_id', sa.UUID(), nullable=False),
        sa.Column('route_id', sa.UUID(), nullable=True),
        sa.Column('customer_id', sa.UUID(), nullable=False),
        sa.Column('route_date', sa.Date(), nullable=False),
        sa.Column('sequence_no', sa.Integer(), nullable=True),
        sa.Column('planned_time', sa.DateTime(), nullable=True),
        sa.Column('check_in_time', sa.DateTime(), nullable=True),
        sa.Column('check_out_time', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='PLANNED'),
        sa.Column('gps_lat', sa.Numeric(10, 7), nullable=True),
        sa.Column('gps_lng', sa.Numeric(10, 7), nullable=True),
        sa.Column('missed_reason', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('offline_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['van_id'], ['vans.id']),
        sa.ForeignKeyConstraint(['route_id'], ['sales_routes.id']),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('offline_id'),
    )

    op.create_table(
        'van_sales_txns',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('txn_no', sa.String(50), nullable=False),
        sa.Column('van_id', sa.UUID(), nullable=False),
        sa.Column('route_id', sa.UUID(), nullable=True),
        sa.Column('customer_id', sa.UUID(), nullable=False),
        sa.Column('visit_id', sa.UUID(), nullable=True),
        sa.Column('driver_id', sa.UUID(), nullable=True),
        sa.Column('txn_type', sa.String(30), nullable=False, server_default='SALE'),
        sa.Column('txn_datetime', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='DRAFT'),
        sa.Column('payment_status', sa.String(50), nullable=False, server_default='UNPAID'),
        sa.Column('subtotal', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('discount_amount', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('tax_amount', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('total_amount', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('paid_amount', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('balance_due', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='KES'),
        sa.Column('linked_so_id', sa.UUID(), nullable=True),
        sa.Column('price_list_id', sa.UUID(), nullable=True),
        sa.Column('promo_ids', sa.JSON(), nullable=True),
        sa.Column('offline_id', sa.String(100), nullable=True),
        sa.Column('synced_at', sa.DateTime(), nullable=True),
        sa.Column('device_id', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['van_id'], ['vans.id']),
        sa.ForeignKeyConstraint(['route_id'], ['sales_routes.id']),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.ForeignKeyConstraint(['visit_id'], ['van_visits.id']),
        sa.ForeignKeyConstraint(['driver_id'], ['users.id']),
        sa.ForeignKeyConstraint(['linked_so_id'], ['sales_orders.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('txn_no'),
        sa.UniqueConstraint('offline_id'),
    )
    op.create_index('ix_van_sales_txns_txn_no', 'van_sales_txns', ['txn_no'])

    op.create_table(
        'van_sales_txn_lines',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('txn_id', sa.UUID(), nullable=False),
        sa.Column('item_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=True),
        sa.Column('uom', sa.String(20), nullable=False, server_default='PCS'),
        sa.Column('quantity', sa.Numeric(14, 3), nullable=False),
        sa.Column('unit_price', sa.Numeric(14, 4), nullable=False),
        sa.Column('discount_pct', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('discount_amt', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('tax_pct', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('tax_amt', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('line_total', sa.Numeric(14, 2), nullable=False),
        sa.Column('return_reason', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['txn_id'], ['van_sales_txns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['products.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['lots.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'van_payments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('txn_id', sa.UUID(), nullable=False),
        sa.Column('method', sa.String(30), nullable=False),
        sa.Column('amount', sa.Numeric(14, 2), nullable=False),
        sa.Column('reference_no', sa.String(200), nullable=True),
        sa.Column('collected_at', sa.DateTime(), nullable=False),
        sa.Column('collected_by', sa.UUID(), nullable=True),
        sa.Column('receipt_no', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['txn_id'], ['van_sales_txns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['collected_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'van_reconciliations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('van_id', sa.UUID(), nullable=False),
        sa.Column('route_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='OPEN'),
        sa.Column('opening_stock', sa.JSON(), nullable=True),
        sa.Column('closing_stock', sa.JSON(), nullable=True),
        sa.Column('sales_qty', sa.JSON(), nullable=True),
        sa.Column('returns_qty', sa.JSON(), nullable=True),
        sa.Column('discrepancy', sa.JSON(), nullable=True),
        sa.Column('total_sales', sa.Numeric(14, 2), nullable=True),
        sa.Column('total_cash', sa.Numeric(14, 2), nullable=True),
        sa.Column('total_mpesa', sa.Numeric(14, 2), nullable=True),
        sa.Column('total_credit', sa.Numeric(14, 2), nullable=True),
        sa.Column('total_returns', sa.Numeric(14, 2), nullable=True),
        sa.Column('submitted_by', sa.UUID(), nullable=True),
        sa.Column('approved_by', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['van_id'], ['vans.id']),
        sa.ForeignKeyConstraint(['submitted_by'], ['users.id']),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('van_id', 'route_date', name='uq_van_recon_date'),
    )

    op.create_table(
        'vs_ai_recommendations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('agent_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('severity', sa.String(20), nullable=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('van_id', sa.UUID(), nullable=True),
        sa.Column('driver_id', sa.UUID(), nullable=True),
        sa.Column('route_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['van_id'], ['vans.id']),
        sa.ForeignKeyConstraint(['driver_id'], ['users.id']),
        sa.ForeignKeyConstraint(['route_id'], ['sales_routes.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('vs_ai_recommendations')
    op.drop_table('van_reconciliations')
    op.drop_table('van_payments')
    op.drop_table('van_sales_txn_lines')
    op.drop_index('ix_van_sales_txns_txn_no', 'van_sales_txns')
    op.drop_table('van_sales_txns')
    op.drop_table('van_visits')
    op.drop_table('van_stock_movements')
    op.drop_table('van_stock')
    op.drop_index('ix_vans_van_code', 'vans')
    op.drop_table('vans')
