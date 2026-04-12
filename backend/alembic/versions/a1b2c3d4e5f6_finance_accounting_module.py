"""finance accounting module - purchase invoices, purchase payments, payment method

Revision ID: a1b2c3d4e5f6
Revises: 3c45d9071c98
Create Date: 2026-04-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '3c45d9071c98'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # purchase_invoices table
    op.create_table(
        'purchase_invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_no', sa.String(50), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('po_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('invoice_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='DRAFT'),
        sa.Column('currency', sa.String(10), nullable=False, server_default='KES'),
        sa.Column('subtotal', sa.Numeric(16, 4), nullable=False, server_default='0'),
        sa.Column('tax_amount', sa.Numeric(16, 4), nullable=False, server_default='0'),
        sa.Column('total_amount', sa.Numeric(16, 4), nullable=False, server_default='0'),
        sa.Column('paid_amount', sa.Numeric(16, 4), nullable=False, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['po_id'], ['purchase_orders.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invoice_no'),
    )
    op.create_index('ix_purchase_invoices_invoice_no', 'purchase_invoices', ['invoice_no'])

    # purchase_invoice_lines table
    op.create_table(
        'purchase_invoice_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('material_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('quantity', sa.Numeric(14, 3), nullable=False),
        sa.Column('unit', sa.String(20), nullable=False, server_default='KG'),
        sa.Column('unit_price', sa.Numeric(14, 4), nullable=False, server_default='0'),
        sa.Column('tax_rate', sa.Numeric(6, 4), nullable=False, server_default='0'),
        sa.Column('line_total', sa.Numeric(16, 4), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['invoice_id'], ['purchase_invoices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # purchase_payments table
    op.create_table(
        'purchase_payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(16, 4), nullable=False),
        sa.Column('method', sa.String(20), nullable=False, server_default='bank'),
        sa.Column('reference', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['invoice_id'], ['purchase_invoices.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Add method column to payments table (customer payments)
    op.add_column('payments', sa.Column('method', sa.String(20), nullable=False, server_default='cash'))


def downgrade() -> None:
    op.drop_column('payments', 'method')
    op.drop_table('purchase_payments')
    op.drop_table('purchase_invoice_lines')
    op.drop_index('ix_purchase_invoices_invoice_no', 'purchase_invoices')
    op.drop_table('purchase_invoices')
