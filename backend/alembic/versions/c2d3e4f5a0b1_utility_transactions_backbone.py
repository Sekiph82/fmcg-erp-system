"""utility_transactions backbone — add transaction_time, reference linkage, variance columns

Revision ID: c2d3e4f5a0b1
Revises: b1c2d3e4f5a0
Create Date: 2026-04-16 00:00:00.000000

Adds to utility_transactions:
  transaction_time      — TIME(timezone=True), sub-day precision beyond transaction_date
  reference_type        — String(50): READING, BILL, ALLOCATION, BOILER_RECORD, etc.
  reference_id          — String(100): UUID/code of the source record
  variance_from_standard — Numeric(16,4): actual vs standard consumption delta
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c2d3e4f5a0b1'
down_revision: Union[str, None] = 'b1c2d3e4f5a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('utility_transactions',
        sa.Column('transaction_time', sa.Time(timezone=True), nullable=True))
    op.add_column('utility_transactions',
        sa.Column('reference_type', sa.String(50), nullable=True))
    op.add_column('utility_transactions',
        sa.Column('reference_id', sa.String(100), nullable=True))
    op.add_column('utility_transactions',
        sa.Column('variance_from_standard', sa.Numeric(16, 4), nullable=True))

    op.create_index('ix_utility_tx_ref_type',  'utility_transactions', ['reference_type'])
    op.create_index('ix_utility_tx_ref_id',    'utility_transactions', ['reference_id'])
    op.create_index('ix_utility_tx_is_anomaly','utility_transactions', ['is_anomaly'])


def downgrade() -> None:
    op.drop_index('ix_utility_tx_is_anomaly', table_name='utility_transactions')
    op.drop_index('ix_utility_tx_ref_id',     table_name='utility_transactions')
    op.drop_index('ix_utility_tx_ref_type',   table_name='utility_transactions')

    op.drop_column('utility_transactions', 'variance_from_standard')
    op.drop_column('utility_transactions', 'reference_id')
    op.drop_column('utility_transactions', 'reference_type')
    op.drop_column('utility_transactions', 'transaction_time')
