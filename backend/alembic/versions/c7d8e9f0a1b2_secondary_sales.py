"""secondary_sales_distributor_sell_through

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-05-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c7d8e9f0a1b2'
down_revision = 'b6c7d8e9f0a1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    upload_source = postgresql.ENUM(
        'POS', 'ERP_INTEGRATION', 'MANUAL_CSV', 'MOBILE', 'API',
        name='uploadsource',
    )
    secondary_sales_status = postgresql.ENUM(
        'PENDING', 'VALIDATED', 'PROCESSED', 'REJECTED',
        name='secondarysalesstatus',
    )
    retail_channel = postgresql.ENUM(
        'SUPERMARKET', 'KIOSK', 'WHOLESALE', 'PHARMACY', 'HOTEL', 'ONLINE', 'OTHER',
        name='retailchannel',
    )
    upload_source.create(op.get_bind(), checkfirst=True)
    secondary_sales_status.create(op.get_bind(), checkfirst=True)
    retail_channel.create(op.get_bind(), checkfirst=True)

    # retailer_masters
    op.create_table(
        'retailer_masters',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('distributor_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('distributors.id', ondelete='SET NULL'), nullable=True),
        sa.Column('retailer_code', sa.String(50), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('location', sa.String(500), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('channel', sa.Enum('SUPERMARKET', 'KIOSK', 'WHOLESALE', 'PHARMACY', 'HOTEL', 'ONLINE', 'OTHER', name='retailchannel'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_retailer_masters_distributor_id', 'retailer_masters', ['distributor_id'])
    op.create_index('ix_retailer_masters_retailer_code', 'retailer_masters', ['retailer_code'])

    # secondary_sales_headers
    op.create_table(
        'secondary_sales_headers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('reference_no', sa.String(50), nullable=False, unique=True),
        sa.Column('distributor_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('distributors.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('period_from', sa.Date(), nullable=False),
        sa.Column('period_to', sa.Date(), nullable=False),
        sa.Column('upload_source', sa.Enum('POS', 'ERP_INTEGRATION', 'MANUAL_CSV', 'MOBILE', 'API', name='uploadsource'), nullable=False, server_default='MANUAL_CSV'),
        sa.Column('upload_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'VALIDATED', 'PROCESSED', 'REJECTED', name='secondarysalesstatus'), nullable=False, server_default='PENDING'),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('validation_errors', sa.Text(), nullable=True),
        sa.Column('total_lines', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_value', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_secondary_sales_headers_distributor_id', 'secondary_sales_headers', ['distributor_id'])
    op.create_index('ix_secondary_sales_headers_reference_no', 'secondary_sales_headers', ['reference_no'])

    # secondary_sales_lines
    op.create_table(
        'secondary_sales_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('header_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('secondary_sales_headers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('retailer_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('retailer_masters.id', ondelete='SET NULL'), nullable=True),
        sa.Column('retailer_name', sa.String(255), nullable=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True),
        sa.Column('product_sku', sa.String(100), nullable=True),
        sa.Column('quantity_sold', sa.Numeric(14, 3), nullable=False),
        sa.Column('unit_price', sa.Numeric(14, 4), nullable=True),
        sa.Column('total_value', sa.Numeric(18, 2), nullable=True),
        sa.Column('sale_date', sa.Date(), nullable=True),
        sa.Column('is_valid', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('validation_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_secondary_sales_lines_header_id', 'secondary_sales_lines', ['header_id'])

    # distributor_inventory_snapshots
    op.create_table(
        'distributor_inventory_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('distributor_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('distributors.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('stock_qty', sa.Numeric(14, 3), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('sell_through_rate', sa.Numeric(7, 4), nullable=True),
        sa.Column('days_of_stock', sa.Numeric(7, 1), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('distributor_id', 'product_id', 'snapshot_date', name='uq_dist_inv_snapshot'),
    )
    op.create_index('ix_distributor_inventory_snapshots_distributor_id', 'distributor_inventory_snapshots', ['distributor_id'])


def downgrade() -> None:
    op.drop_table('distributor_inventory_snapshots')
    op.drop_table('secondary_sales_lines')
    op.drop_table('secondary_sales_headers')
    op.drop_table('retailer_masters')
    op.execute("DROP TYPE IF EXISTS uploadsource")
    op.execute("DROP TYPE IF EXISTS secondarysalesstatus")
    op.execute("DROP TYPE IF EXISTS retailchannel")
