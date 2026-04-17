"""utilities module - system configs, uom conversions, number series, currencies

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # system_configs table
    op.create_table(
        'system_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(30), nullable=False, server_default='SYSTEM'),
        sa.Column('is_editable', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('updated_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key'),
    )
    op.create_index('ix_system_configs_key', 'system_configs', ['key'])

    # uom_conversions table
    op.create_table(
        'uom_conversions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('from_uom', sa.String(20), nullable=False),
        sa.Column('to_uom', sa.String(20), nullable=False),
        sa.Column('factor', sa.Numeric(20, 8), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_uom_conversions_from_to', 'uom_conversions', ['from_uom', 'to_uom'])

    # number_series table
    op.create_table(
        'number_series',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('module', sa.String(60), nullable=False),
        sa.Column('label', sa.String(100), nullable=False),
        sa.Column('prefix', sa.String(20), nullable=False),
        sa.Column('suffix', sa.String(20), nullable=True),
        sa.Column('current_number', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('padding', sa.Integer(), nullable=False, server_default='4'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('module'),
    )
    op.create_index('ix_number_series_module', 'number_series', ['module'])

    # currencies table
    op.create_table(
        'currencies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(10), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('symbol', sa.String(10), nullable=False),
        sa.Column('exchange_rate', sa.Numeric(18, 6), nullable=False, server_default='1'),
        sa.Column('is_base', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_index('ix_currencies_code', 'currencies', ['code'])


def downgrade() -> None:
    op.drop_index('ix_currencies_code', table_name='currencies')
    op.drop_table('currencies')
    op.drop_index('ix_number_series_module', table_name='number_series')
    op.drop_table('number_series')
    op.drop_index('ix_uom_conversions_from_to', table_name='uom_conversions')
    op.drop_table('uom_conversions')
    op.drop_index('ix_system_configs_key', table_name='system_configs')
    op.drop_table('system_configs')
