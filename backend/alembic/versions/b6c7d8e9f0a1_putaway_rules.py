"""putaway_rules

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-05-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b6c7d8e9f0a1'
down_revision = 'a5b6c7d8e9f0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enums
    putaway_rule_type = postgresql.ENUM(
        'FIXED', 'ZONE', 'CATEGORY', 'RANDOM', 'NEAREST',
        name='putawayruletype',
    )
    putaway_task_status = postgresql.ENUM(
        'PENDING', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED',
        name='putawaytaskstatus',
    )
    location_type = postgresql.ENUM(
        'RACK', 'BIN', 'FLOOR', 'COLD_STORAGE',
        name='locationtype',
    )
    putaway_rule_type.create(op.get_bind(), checkfirst=True)
    putaway_task_status.create(op.get_bind(), checkfirst=True)
    location_type.create(op.get_bind(), checkfirst=True)

    # Add columns to storage_locations
    op.add_column('storage_locations',
        sa.Column('location_type', sa.Enum('RACK', 'BIN', 'FLOOR', 'COLD_STORAGE', name='locationtype'), nullable=True)
    )
    op.add_column('storage_locations',
        sa.Column('current_utilization_pct', sa.Numeric(5, 2), nullable=True, server_default='0')
    )

    # putaway_rules
    op.create_table(
        'putaway_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('rule_code', sa.String(50), nullable=False, unique=True),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rule_type', sa.Enum('FIXED', 'ZONE', 'CATEGORY', 'RANDOM', 'NEAREST', name='putawayruletype'), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouse_zones.id', ondelete='SET NULL'), nullable=True),
        sa.Column('location_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('storage_locations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_putaway_rules_warehouse_id', 'putaway_rules', ['warehouse_id'])
    op.create_index('ix_putaway_rules_rule_code', 'putaway_rules', ['rule_code'])

    # putaway_tasks
    op.create_table(
        'putaway_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_no', sa.String(50), nullable=False, unique=True),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True),
        sa.Column('material_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('materials.id', ondelete='SET NULL'), nullable=True),
        sa.Column('lot_number', sa.String(100), nullable=True),
        sa.Column('quantity', sa.Numeric(14, 3), nullable=False),
        sa.Column('weight_kg', sa.Numeric(10, 2), nullable=True),
        sa.Column('volume_m3', sa.Numeric(10, 4), nullable=True),
        sa.Column('suggested_location_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('storage_locations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', name='putawaytaskstatus'),
                  nullable=False, server_default='PENDING'),
        sa.Column('receipt_ref', sa.String(100), nullable=True),
        sa.Column('override_reason', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_putaway_tasks_warehouse_id', 'putaway_tasks', ['warehouse_id'])
    op.create_index('ix_putaway_tasks_task_no', 'putaway_tasks', ['task_no'])

    # putaway_executions
    op.create_table(
        'putaway_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('putaway_tasks.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('actual_location_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('storage_locations.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('executed_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_variance', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_putaway_executions_task_id', 'putaway_executions', ['task_id'])


def downgrade() -> None:
    op.drop_table('putaway_executions')
    op.drop_table('putaway_tasks')
    op.drop_table('putaway_rules')
    op.drop_column('storage_locations', 'current_utilization_pct')
    op.drop_column('storage_locations', 'location_type')
    op.execute("DROP TYPE IF EXISTS putawayruletype")
    op.execute("DROP TYPE IF EXISTS putawaytaskstatus")
    op.execute("DROP TYPE IF EXISTS locationtype")
