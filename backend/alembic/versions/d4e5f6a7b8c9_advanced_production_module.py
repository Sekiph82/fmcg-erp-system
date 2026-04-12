"""Advanced Production Module — 11 sub-modules

Revision ID: d4e5f6a7b8c9
Revises: b2c3d4e5f6a7
Create Date: 2026-04-12

Tables added:
  work_centers, routings, routing_steps,
  work_orders, shifts, production_schedules,
  time_tracking, downtime_events,
  qc_inspections, qc_results,
  waste_records, batch_lots,
  labor_logs, oee_records
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision  = 'd4e5f6a7b8c9'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # ── Work Centers ────────────────────────────────────────────────────────
    op.create_table(
        'work_centers',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('work_center_id', sa.String(50), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False, server_default='MACHINE'),
        sa.Column('capacity', sa.Numeric(14, 3), nullable=True),
        sa.Column('capacity_uom', sa.String(20), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('department', sa.String(100), nullable=True),
        sa.Column('setup_time_min', sa.Integer, nullable=True),
        sa.Column('ideal_cycle_time_sec', sa.Numeric(10, 3), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_work_centers_work_center_id', 'work_centers', ['work_center_id'])

    # ── Routings ────────────────────────────────────────────────────────────
    op.create_table(
        'routings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('routing_id', sa.String(50), nullable=False, unique=True),
        sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_routings_routing_id', 'routings', ['routing_id'])
    op.create_index('ix_routings_product_id', 'routings', ['product_id'])

    # ── Routing Steps ───────────────────────────────────────────────────────
    op.create_table(
        'routing_steps',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('routing_id', UUID(as_uuid=True), sa.ForeignKey('routings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_number', sa.Integer, nullable=False),
        sa.Column('operation', sa.String(255), nullable=False),
        sa.Column('work_center_id', UUID(as_uuid=True), sa.ForeignKey('work_centers.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('standard_time_minutes', sa.Integer, nullable=False, server_default='0'),
        sa.Column('setup_time_minutes', sa.Integer, nullable=True),
        sa.Column('is_parallel', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('routing_id', 'step_number', name='uq_routing_step'),
    )
    op.create_index('ix_routing_steps_routing_id', 'routing_steps', ['routing_id'])

    # ── Shifts ──────────────────────────────────────────────────────────────
    op.create_table(
        'shifts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('shift_code', sa.String(50), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('start_time_str', sa.String(8), nullable=False),
        sa.Column('end_time_str', sa.String(8), nullable=False),
        sa.Column('duration_hours', sa.Numeric(4, 2), nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Work Orders ─────────────────────────────────────────────────────────
    op.create_table(
        'work_orders',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('work_order_id', sa.String(50), nullable=False, unique=True),
        sa.Column('production_order_id', UUID(as_uuid=True), sa.ForeignKey('production_orders.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('routing_step_id', UUID(as_uuid=True), sa.ForeignKey('routing_steps.id', ondelete='SET NULL'), nullable=True),
        sa.Column('work_center_id', UUID(as_uuid=True), sa.ForeignKey('work_centers.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('operation', sa.String(255), nullable=False),
        sa.Column('operator', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='planned'),
        sa.Column('planned_quantity', sa.Numeric(14, 3), nullable=True),
        sa.Column('actual_quantity', sa.Numeric(14, 3), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('planned_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('planned_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_work_orders_work_order_id', 'work_orders', ['work_order_id'])
    op.create_index('ix_work_orders_production_order_id', 'work_orders', ['production_order_id'])

    # ── Production Schedules ────────────────────────────────────────────────
    op.create_table(
        'production_schedules',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('schedule_id', sa.String(50), nullable=False, unique=True),
        sa.Column('production_order_id', UUID(as_uuid=True), sa.ForeignKey('production_orders.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('work_center_id', UUID(as_uuid=True), sa.ForeignKey('work_centers.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('shift_id', UUID(as_uuid=True), sa.ForeignKey('shifts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('shift_name', sa.String(100), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='planned'),
        sa.Column('priority', sa.String(50), nullable=False, server_default='medium'),
        sa.Column('conflict_flag', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_production_schedules_schedule_id', 'production_schedules', ['schedule_id'])
    op.create_index('ix_production_schedules_work_center_id', 'production_schedules', ['work_center_id'])

    # ── Time Tracking ───────────────────────────────────────────────────────
    op.create_table(
        'time_tracking',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('log_id', sa.String(50), nullable=False, unique=True),
        sa.Column('work_order_id', UUID(as_uuid=True), sa.ForeignKey('work_orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actual_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actual_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_actual_min', sa.Integer, nullable=True),
        sa.Column('duration_planned_min', sa.Integer, nullable=True),
        sa.Column('downtime_minutes', sa.Integer, nullable=True),
        sa.Column('category', sa.String(50), nullable=False, server_default='productive'),
        sa.Column('reason', sa.String(500), nullable=True),
        sa.Column('efficiency_pct', sa.Numeric(6, 2), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_time_tracking_log_id', 'time_tracking', ['log_id'])
    op.create_index('ix_time_tracking_work_order_id', 'time_tracking', ['work_order_id'])

    # ── Downtime Events ─────────────────────────────────────────────────────
    op.create_table(
        'downtime_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('downtime_id', sa.String(50), nullable=False, unique=True),
        sa.Column('work_center_id', UUID(as_uuid=True), sa.ForeignKey('work_centers.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('work_order_id', UUID(as_uuid=True), sa.ForeignKey('work_orders.id', ondelete='SET NULL'), nullable=True),
        sa.Column('machine_id', sa.String(100), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_min', sa.Integer, nullable=True),
        sa.Column('reason', sa.String(500), nullable=False),
        sa.Column('category', sa.String(50), nullable=False, server_default='unplanned'),
        sa.Column('reported_by', sa.String(255), nullable=True),
        sa.Column('impact_units', sa.Integer, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_downtime_events_downtime_id', 'downtime_events', ['downtime_id'])
    op.create_index('ix_downtime_events_work_center_id', 'downtime_events', ['work_center_id'])

    # ── QC Inspections ──────────────────────────────────────────────────────
    op.create_table(
        'adv_qc_inspections',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('qc_id', sa.String(50), nullable=False, unique=True),
        sa.Column('production_order_id', UUID(as_uuid=True), sa.ForeignKey('production_orders.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('work_order_id', UUID(as_uuid=True), sa.ForeignKey('work_orders.id', ondelete='SET NULL'), nullable=True),
        sa.Column('inspection_type', sa.String(50), nullable=False, server_default='inline'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('checked_by', sa.String(255), nullable=True),
        sa.Column('inspected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('batch_ref', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_adv_qc_inspections_qc_id', 'adv_qc_inspections', ['qc_id'])
    op.create_index('ix_adv_qc_inspections_production_order_id', 'adv_qc_inspections', ['production_order_id'])

    # ── QC Results ──────────────────────────────────────────────────────────
    op.create_table(
        'adv_qc_results',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('inspection_id', UUID(as_uuid=True), sa.ForeignKey('adv_qc_inspections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('test_type', sa.String(100), nullable=False),
        sa.Column('actual_value', sa.Numeric(14, 4), nullable=True),
        sa.Column('min_value', sa.Numeric(14, 4), nullable=True),
        sa.Column('max_value', sa.Numeric(14, 4), nullable=True),
        sa.Column('unit', sa.String(50), nullable=True),
        sa.Column('result', sa.String(20), nullable=False, server_default='pass'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_adv_qc_results_inspection_id', 'adv_qc_results', ['inspection_id'])

    # ── Waste Records ───────────────────────────────────────────────────────
    op.create_table(
        'waste_records',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('waste_id', sa.String(50), nullable=False, unique=True),
        sa.Column('production_order_id', UUID(as_uuid=True), sa.ForeignKey('production_orders.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('work_order_id', UUID(as_uuid=True), sa.ForeignKey('work_orders.id', ondelete='SET NULL'), nullable=True),
        sa.Column('material_id', UUID(as_uuid=True), sa.ForeignKey('materials.id', ondelete='SET NULL'), nullable=True),
        sa.Column('material_code', sa.String(100), nullable=True),
        sa.Column('waste_type', sa.String(50), nullable=False, server_default='MATERIAL'),
        sa.Column('waste_category', sa.String(50), nullable=False, server_default='normal'),
        sa.Column('expected_qty', sa.Numeric(14, 4), nullable=False),
        sa.Column('actual_qty', sa.Numeric(14, 4), nullable=False),
        sa.Column('loss_qty', sa.Numeric(14, 4), nullable=False, server_default='0'),
        sa.Column('loss_pct', sa.Numeric(6, 3), nullable=True),
        sa.Column('uom', sa.String(20), nullable=True),
        sa.Column('reason', sa.String(500), nullable=True),
        sa.Column('is_anomaly', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_waste_records_waste_id', 'waste_records', ['waste_id'])
    op.create_index('ix_waste_records_production_order_id', 'waste_records', ['production_order_id'])

    # ── Batch Lots ──────────────────────────────────────────────────────────
    op.create_table(
        'batch_lots',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('batch_id', sa.String(100), nullable=False, unique=True),
        sa.Column('production_order_id', UUID(as_uuid=True), sa.ForeignKey('production_orders.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('product_sku', sa.String(100), nullable=True),
        sa.Column('quantity', sa.Numeric(14, 3), nullable=False),
        sa.Column('uom', sa.String(20), nullable=False, server_default='KG'),
        sa.Column('manufacture_date', sa.Date, nullable=True),
        sa.Column('expiry_date', sa.Date, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='quarantine'),
        sa.Column('traceability_code', sa.String(255), nullable=True),
        sa.Column('warehouse_id', UUID(as_uuid=True), sa.ForeignKey('warehouses.id', ondelete='SET NULL'), nullable=True),
        sa.Column('quarantine_reason', sa.String(500), nullable=True),
        sa.Column('released_by', sa.String(255), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_batch_lots_batch_id', 'batch_lots', ['batch_id'])
    op.create_index('ix_batch_lots_production_order_id', 'batch_lots', ['production_order_id'])
    op.create_index('ix_batch_lots_product_id', 'batch_lots', ['product_id'])
    op.create_index('ix_batch_lots_traceability_code', 'batch_lots', ['traceability_code'])

    # ── Labor Logs ──────────────────────────────────────────────────────────
    op.create_table(
        'labor_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('labor_id', sa.String(50), nullable=False, unique=True),
        sa.Column('work_order_id', UUID(as_uuid=True), sa.ForeignKey('work_orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('employee_id', UUID(as_uuid=True), nullable=True),
        sa.Column('employee_code', sa.String(50), nullable=True),
        sa.Column('operator_name', sa.String(255), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('hours_worked', sa.Numeric(6, 2), nullable=True),
        sa.Column('role', sa.String(100), nullable=True),
        sa.Column('activity_type', sa.String(50), nullable=False, server_default='production'),
        sa.Column('pieces_produced', sa.Integer, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_labor_logs_labor_id', 'labor_logs', ['labor_id'])
    op.create_index('ix_labor_logs_work_order_id', 'labor_logs', ['work_order_id'])

    # ── OEE Records ─────────────────────────────────────────────────────────
    op.create_table(
        'oee_records',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('oee_id', sa.String(50), nullable=False, unique=True),
        sa.Column('work_center_id', UUID(as_uuid=True), sa.ForeignKey('work_centers.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('machine_id', sa.String(100), nullable=True),
        sa.Column('shift_id', UUID(as_uuid=True), sa.ForeignKey('shifts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('record_date', sa.Date, nullable=False),
        sa.Column('planned_production_time_min', sa.Integer, nullable=False),
        sa.Column('actual_production_time_min', sa.Integer, nullable=True),
        sa.Column('downtime_min', sa.Integer, nullable=True),
        sa.Column('ideal_cycle_time_sec', sa.Numeric(10, 3), nullable=True),
        sa.Column('total_units_produced', sa.Integer, nullable=True),
        sa.Column('good_units_produced', sa.Integer, nullable=True),
        sa.Column('availability', sa.Numeric(6, 4), nullable=True),
        sa.Column('performance', sa.Numeric(6, 4), nullable=True),
        sa.Column('quality', sa.Numeric(6, 4), nullable=True),
        sa.Column('oee_score', sa.Numeric(6, 4), nullable=True),
        sa.Column('is_low_oee', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_high_downtime', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('work_center_id', 'record_date', 'shift_id', name='uq_oee_center_date_shift'),
    )
    op.create_index('ix_oee_records_oee_id', 'oee_records', ['oee_id'])
    op.create_index('ix_oee_record_date', 'oee_records', ['record_date'])
    op.create_index('ix_oee_records_work_center_id', 'oee_records', ['work_center_id'])


def downgrade() -> None:
    op.drop_table('oee_records')
    op.drop_table('labor_logs')
    op.drop_table('batch_lots')
    op.drop_table('waste_records')
    op.drop_table('adv_qc_results')
    op.drop_table('adv_qc_inspections')
    op.drop_table('downtime_events')
    op.drop_table('time_tracking')
    op.drop_table('production_schedules')
    op.drop_table('work_orders')
    op.drop_table('routing_steps')
    op.drop_table('routings')
    op.drop_table('shifts')
    op.drop_table('work_centers')
