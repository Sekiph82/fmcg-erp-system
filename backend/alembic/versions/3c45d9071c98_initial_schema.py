"""initial schema

Revision ID: 3c45d9071c98
Revises: 
Create Date: 2026-04-09 20:33:49.559337

"""
from typing import Sequence, Union

from alembic import op, context
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '3c45d9071c98'
down_revision: Union[str, None] = '20260517_0000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    if context.is_offline_mode():
        return False
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if context.is_offline_mode() or not _has_table(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    columns = {col['name'] for col in inspector.get_columns(table_name)}
    return column_name in columns


def upgrade() -> None:
    # Only add columns if the table exists; skip if it doesn't (for fresh databases)
    if context.is_offline_mode() or _has_table('sales_orders'):
        if not _has_column('sales_orders', 'campaign_id'):
            op.add_column('sales_orders', sa.Column('campaign_id', postgresql.UUID(), nullable=True))
        if not _has_column('sales_orders', 'promotion_id'):
            op.add_column('sales_orders', sa.Column('promotion_id', postgresql.UUID(), nullable=True))
        if not _has_column('sales_orders', 'crm_segment_id'):
            op.add_column('sales_orders', sa.Column('crm_segment_id', postgresql.UUID(), nullable=True))
        
        # Create indexes if they don't exist
        try:
            op.create_index(op.f('ix_sales_orders_campaign_id'), 'sales_orders', ['campaign_id'], unique=False)
        except Exception:
            pass  # Index already exists
        try:
            op.create_index(op.f('ix_sales_orders_promotion_id'), 'sales_orders', ['promotion_id'], unique=False)
        except Exception:
            pass  # Index already exists


def downgrade() -> None:
    if context.is_offline_mode() or _has_table('sales_orders'):
        if _has_column('sales_orders', 'promotion_id'):
            try:
                op.drop_index(op.f('ix_sales_orders_promotion_id'), table_name='sales_orders')
            except:
                pass
        if _has_column('sales_orders', 'campaign_id'):
            try:
                op.drop_index(op.f('ix_sales_orders_campaign_id'), table_name='sales_orders')
            except:
                pass
        
        if _has_column('sales_orders', 'crm_segment_id'):
            op.drop_column('sales_orders', 'crm_segment_id')
        if _has_column('sales_orders', 'promotion_id'):
            op.drop_column('sales_orders', 'promotion_id')
        if _has_column('sales_orders', 'campaign_id'):
            op.drop_column('sales_orders', 'campaign_id')
