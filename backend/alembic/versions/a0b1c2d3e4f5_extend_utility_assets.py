"""extend utility asset categories and utility assets with additional fields

Revision ID: a0b1c2d3e4f5
Revises: f6a7b8c9d0e1
Create Date: 2026-04-16 01:00:00.000000

Adds:
  utility_asset_categories.default_unit
  utility_assets.subsystem, parent_asset_id, line_id, machine_id,
              rated_power, rated_power_unit, flow_capacity,
              pressure_capacity, temperature_range, lifecycle_status,
              criticality_level, maintenance_strategy
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a0b1c2d3e4f5'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── utility_asset_categories — add default_unit ────────────────────────────
    op.add_column('utility_asset_categories',
        sa.Column('default_unit', sa.String(30), nullable=True))

    # ── utility_assets — add extended fields ──────────────────────────────────
    op.add_column('utility_assets',
        sa.Column('subsystem', sa.String(100), nullable=True))
    op.add_column('utility_assets',
        sa.Column('parent_asset_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('utility_assets',
        sa.Column('line_id', sa.String(100), nullable=True))
    op.add_column('utility_assets',
        sa.Column('machine_id', sa.String(100), nullable=True))
    op.add_column('utility_assets',
        sa.Column('rated_power', sa.Numeric(14, 3), nullable=True))
    op.add_column('utility_assets',
        sa.Column('rated_power_unit', sa.String(30), nullable=True))
    op.add_column('utility_assets',
        sa.Column('flow_capacity', sa.Numeric(14, 3), nullable=True))
    op.add_column('utility_assets',
        sa.Column('pressure_capacity', sa.Numeric(14, 3), nullable=True))
    op.add_column('utility_assets',
        sa.Column('temperature_range', sa.String(100), nullable=True))
    op.add_column('utility_assets',
        sa.Column('lifecycle_status', sa.String(30), nullable=True))
    op.add_column('utility_assets',
        sa.Column('criticality_level', sa.String(20), nullable=True,
                  server_default='MEDIUM'))
    op.add_column('utility_assets',
        sa.Column('maintenance_strategy', sa.String(100), nullable=True))

    # FK: parent_asset_id → utility_assets.id
    op.create_foreign_key(
        'fk_utility_assets_parent',
        'utility_assets', 'utility_assets',
        ['parent_asset_id'], ['id'],
        ondelete='SET NULL',
    )

    # Indexes for the new filterable columns
    op.create_index('ix_utility_assets_line_id',    'utility_assets', ['line_id'])
    op.create_index('ix_utility_assets_machine_id', 'utility_assets', ['machine_id'])
    op.create_index('ix_utility_assets_lifecycle',  'utility_assets', ['lifecycle_status'])
    op.create_index('ix_utility_assets_criticality','utility_assets', ['criticality_level'])
    op.create_index('ix_utility_assets_subsystem',  'utility_assets', ['subsystem'])


def downgrade() -> None:
    op.drop_index('ix_utility_assets_subsystem',   table_name='utility_assets')
    op.drop_index('ix_utility_assets_criticality', table_name='utility_assets')
    op.drop_index('ix_utility_assets_lifecycle',   table_name='utility_assets')
    op.drop_index('ix_utility_assets_machine_id',  table_name='utility_assets')
    op.drop_index('ix_utility_assets_line_id',     table_name='utility_assets')
    op.drop_constraint('fk_utility_assets_parent', 'utility_assets', type_='foreignkey')
    for col in (
        'maintenance_strategy', 'criticality_level', 'lifecycle_status',
        'temperature_range', 'pressure_capacity', 'flow_capacity',
        'rated_power_unit', 'rated_power', 'machine_id', 'line_id',
        'parent_asset_id', 'subsystem',
    ):
        op.drop_column('utility_assets', col)
    op.drop_column('utility_asset_categories', 'default_unit')
