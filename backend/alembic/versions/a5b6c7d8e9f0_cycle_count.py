"""cycle_count

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-05-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a5b6c7d8e9f0'
down_revision = 'f4a5b6c7d8e9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name, vals in [
        ('ccplantype',       ['abc', 'random', 'location', 'item', 'frequency']),
        ('ccplanstatus',     ['draft', 'active', 'paused', 'completed']),
        ('cctaskstatus',     ['pending', 'in_progress', 'completed', 'approved', 'rejected']),
        ('ccabcclass',       ['A', 'B', 'C']),
        ('ccadjstatus',      ['pending', 'approved', 'rejected', 'posted']),
    ]:
        en = postgresql.ENUM(*vals, name=name)
        en.create(op.get_bind(), checkfirst=True)

    # ── cc_plans ──────────────────────────────────────────────────────────────
    op.create_table(
        'cc_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('plan_code', sa.String(50), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('warehouses.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('plan_type', sa.Enum('abc', 'random', 'location', 'item', 'frequency', name='ccplantype'), nullable=False),
        sa.Column('status', sa.Enum('draft', 'active', 'paused', 'completed', name='ccplanstatus'), nullable=False, server_default='draft'),
        sa.Column('frequency_days', sa.Integer, nullable=True),
        sa.Column('abc_classes', sa.String(10), nullable=True),
        sa.Column('variance_tolerance_pct', sa.Numeric(5, 2), nullable=False, server_default='2.0'),
        sa.Column('auto_approve_within_tolerance', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('start_date', sa.Date, nullable=True),
        sa.Column('end_date', sa.Date, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_cc_plans_warehouse_id', 'cc_plans', ['warehouse_id'])
    op.create_index('ix_cc_plans_status', 'cc_plans', ['status'])

    # ── cc_tasks ──────────────────────────────────────────────────────────────
    op.create_table(
        'cc_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_no', sa.String(50), nullable=False, unique=True),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cc_plans.id', ondelete='CASCADE'), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('warehouses.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('location_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('storage_locations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True),
        sa.Column('material_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('materials.id', ondelete='SET NULL'), nullable=True),
        sa.Column('abc_class', sa.Enum('A', 'B', 'C', name='ccabcclass'), nullable=True),
        sa.Column('scheduled_date', sa.Date, nullable=False),
        sa.Column('assigned_to_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.Enum('pending', 'in_progress', 'completed', 'approved', 'rejected', name='cctaskstatus'), nullable=False, server_default='pending'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_cc_tasks_plan_id', 'cc_tasks', ['plan_id'])
    op.create_index('ix_cc_tasks_status', 'cc_tasks', ['status'])

    # ── cc_count_entries ──────────────────────────────────────────────────────
    op.create_table(
        'cc_count_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cc_tasks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True),
        sa.Column('material_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('materials.id', ondelete='SET NULL'), nullable=True),
        sa.Column('lot_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('lots.id', ondelete='SET NULL'), nullable=True),
        sa.Column('location_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('storage_locations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('system_qty', sa.Numeric(14, 3), nullable=False),
        sa.Column('counted_qty', sa.Numeric(14, 3), nullable=False),
        sa.Column('variance_qty', sa.Numeric(14, 3), nullable=False),
        sa.Column('variance_pct', sa.Numeric(8, 4), nullable=True),
        sa.Column('unit_cost', sa.Numeric(14, 4), nullable=True),
        sa.Column('variance_value', sa.Numeric(16, 4), nullable=True),
        sa.Column('unit', sa.String(20), nullable=False, server_default='KG'),
        sa.Column('within_tolerance', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('root_cause', sa.Text, nullable=True),
        sa.Column('counted_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('counted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_cc_count_entries_task_id', 'cc_count_entries', ['task_id'])

    # ── cc_adjustments ────────────────────────────────────────────────────────
    op.create_table(
        'cc_adjustments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('entry_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cc_count_entries.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', 'posted', name='ccadjstatus'), nullable=False, server_default='pending'),
        sa.Column('adjustment_qty', sa.Numeric(14, 3), nullable=False),
        sa.Column('adjustment_value', sa.Numeric(16, 4), nullable=True),
        sa.Column('approved_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text, nullable=True),
        sa.Column('posted_flag', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('stock_movement_ref', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_cc_adjustments_status', 'cc_adjustments', ['status'])

    # ── cc_abc_classifications ────────────────────────────────────────────────
    op.create_table(
        'cc_abc_classifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=True),
        sa.Column('material_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('materials.id', ondelete='CASCADE'), nullable=True),
        sa.Column('abc_class', sa.Enum('A', 'B', 'C', name='ccabcclass'), nullable=False),
        sa.Column('stock_value', sa.Numeric(16, 4), nullable=True),
        sa.Column('annual_movements', sa.Integer, nullable=True),
        sa.Column('classification_date', sa.Date, nullable=False),
        sa.Column('count_frequency_days', sa.Integer, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_cc_abc_classifications_warehouse_id', 'cc_abc_classifications', ['warehouse_id'])


def downgrade() -> None:
    op.drop_table('cc_abc_classifications')
    op.drop_table('cc_adjustments')
    op.drop_table('cc_count_entries')
    op.drop_table('cc_tasks')
    op.drop_table('cc_plans')
    for name in ['ccadjstatus', 'ccabcclass', 'cctaskstatus', 'ccplanstatus', 'ccplantype']:
        op.execute(f"DROP TYPE IF EXISTS {name}")
