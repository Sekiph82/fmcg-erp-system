"""fleet_management

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-05-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'f4a5b6c7d8e9'
down_revision = 'e3f4a5b6c7d8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enums ─────────────────────────────────────────────────────────────────
    for name, vals in [
        ('fleetvehicletype',   ['truck', 'van', 'motorcycle', 'pickup', 'third_party']),
        ('fleetvehiclestatus', ['active', 'in_service', 'maintenance', 'inactive']),
        ('fleetfueltype',      ['petrol', 'diesel', 'electric', 'hybrid']),
        ('fleettripstatus',    ['planned', 'in_progress', 'completed', 'cancelled']),
        ('fleetmaintenancetype', ['service', 'repair', 'inspection', 'tyre', 'other']),
        ('fleetincidenttype',  ['accident', 'damage', 'theft', 'breakdown', 'other']),
        ('fleetincidentstatus',['open', 'under_review', 'resolved', 'closed']),
        ('fleetdriverstatus',  ['available', 'on_trip', 'off_duty', 'inactive']),
    ]:
        en = postgresql.ENUM(*vals, name=name)
        en.create(op.get_bind(), checkfirst=True)

    # ── fleet_drivers ─────────────────────────────────────────────────────────
    op.create_table(
        'fleet_drivers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('driver_code', sa.String(50), nullable=False, unique=True),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(30), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('license_number', sa.String(100), nullable=False),
        sa.Column('license_class', sa.String(20), nullable=True),
        sa.Column('license_expiry', sa.Date, nullable=True),
        sa.Column('status', sa.Enum('available', 'on_trip', 'off_duty', 'inactive', name='fleetdriverstatus'), nullable=False, server_default='available'),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hr_employees.id', ondelete='SET NULL'), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_fleet_drivers_driver_code', 'fleet_drivers', ['driver_code'])
    op.create_index('ix_fleet_drivers_status', 'fleet_drivers', ['status'])

    # ── fleet_vehicles ────────────────────────────────────────────────────────
    op.create_table(
        'fleet_vehicles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('vehicle_code', sa.String(50), nullable=False, unique=True),
        sa.Column('plate_number', sa.String(50), nullable=False, unique=True),
        sa.Column('vehicle_type', sa.Enum('truck', 'van', 'motorcycle', 'pickup', 'third_party', name='fleetvehicletype'), nullable=False),
        sa.Column('make', sa.String(100), nullable=True),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('year', sa.Integer, nullable=True),
        sa.Column('capacity_weight_kg', sa.Numeric(10, 2), nullable=True),
        sa.Column('capacity_volume_m3', sa.Numeric(10, 2), nullable=True),
        sa.Column('fuel_type', sa.Enum('petrol', 'diesel', 'electric', 'hybrid', name='fleetfueltype'), nullable=False, server_default='diesel'),
        sa.Column('status', sa.Enum('active', 'in_service', 'maintenance', 'inactive', name='fleetvehiclestatus'), nullable=False, server_default='active'),
        sa.Column('purchase_date', sa.Date, nullable=True),
        sa.Column('odometer_km', sa.Numeric(12, 1), nullable=True),
        sa.Column('gps_device_id', sa.String(100), nullable=True),
        sa.Column('assigned_driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('fleet_drivers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('default_warehouse_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('warehouses.id', ondelete='SET NULL'), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_fleet_vehicles_vehicle_code', 'fleet_vehicles', ['vehicle_code'])
    op.create_index('ix_fleet_vehicles_plate_number', 'fleet_vehicles', ['plate_number'])
    op.create_index('ix_fleet_vehicles_status', 'fleet_vehicles', ['status'])

    # ── fleet_trips ───────────────────────────────────────────────────────────
    op.create_table(
        'fleet_trips',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('trip_no', sa.String(50), nullable=False, unique=True),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('fleet_vehicles.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('fleet_drivers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('trip_date', sa.Date, nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('start_location', sa.String(255), nullable=True),
        sa.Column('end_location', sa.String(255), nullable=True),
        sa.Column('planned_distance_km', sa.Numeric(10, 2), nullable=True),
        sa.Column('actual_distance_km', sa.Numeric(10, 2), nullable=True),
        sa.Column('start_odometer', sa.Numeric(12, 1), nullable=True),
        sa.Column('end_odometer', sa.Numeric(12, 1), nullable=True),
        sa.Column('status', sa.Enum('planned', 'in_progress', 'completed', 'cancelled', name='fleettripstatus'), nullable=False, server_default='planned'),
        sa.Column('purpose', sa.String(255), nullable=True),
        sa.Column('delivery_trip_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('delivery_trips.id', ondelete='SET NULL'), nullable=True),
        sa.Column('cargo_weight_kg', sa.Numeric(10, 2), nullable=True),
        sa.Column('fuel_used_liters', sa.Numeric(10, 3), nullable=True),
        sa.Column('trip_cost', sa.Numeric(12, 2), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_fleet_trips_trip_no', 'fleet_trips', ['trip_no'])
    op.create_index('ix_fleet_trips_vehicle_id', 'fleet_trips', ['vehicle_id'])
    op.create_index('ix_fleet_trips_driver_id', 'fleet_trips', ['driver_id'])
    op.create_index('ix_fleet_trips_status', 'fleet_trips', ['status'])

    # ── fleet_fuel_logs ───────────────────────────────────────────────────────
    op.create_table(
        'fleet_fuel_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('fleet_vehicles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('trip_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('fleet_trips.id', ondelete='SET NULL'), nullable=True),
        sa.Column('fuel_date', sa.Date, nullable=False),
        sa.Column('fuel_quantity_liters', sa.Numeric(10, 3), nullable=False),
        sa.Column('fuel_cost', sa.Numeric(12, 2), nullable=False),
        sa.Column('cost_per_liter', sa.Numeric(10, 4), nullable=True),
        sa.Column('odometer_reading', sa.Numeric(12, 1), nullable=True),
        sa.Column('fuel_station', sa.String(255), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_fleet_fuel_logs_vehicle_id', 'fleet_fuel_logs', ['vehicle_id'])

    # ── fleet_maintenance_records ─────────────────────────────────────────────
    op.create_table(
        'fleet_maintenance_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('fleet_vehicles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('maintenance_type', sa.Enum('service', 'repair', 'inspection', 'tyre', 'other', name='fleetmaintenancetype'), nullable=False),
        sa.Column('maintenance_date', sa.Date, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('cost', sa.Numeric(12, 2), nullable=True),
        sa.Column('odometer_at_service', sa.Numeric(12, 1), nullable=True),
        sa.Column('next_due_date', sa.Date, nullable=True),
        sa.Column('next_due_odometer', sa.Numeric(12, 1), nullable=True),
        sa.Column('vendor', sa.String(255), nullable=True),
        sa.Column('downtime_days', sa.Integer, nullable=True),
        sa.Column('completed', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_fleet_maintenance_records_vehicle_id', 'fleet_maintenance_records', ['vehicle_id'])

    # ── fleet_incident_logs ───────────────────────────────────────────────────
    op.create_table(
        'fleet_incident_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('fleet_vehicles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('fleet_drivers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('incident_date', sa.Date, nullable=False),
        sa.Column('incident_type', sa.Enum('accident', 'damage', 'theft', 'breakdown', 'other', name='fleetincidenttype'), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('cost_estimate', sa.Numeric(12, 2), nullable=True),
        sa.Column('insurance_claim_no', sa.String(100), nullable=True),
        sa.Column('status', sa.Enum('open', 'under_review', 'resolved', 'closed', name='fleetincidentstatus'), nullable=False, server_default='open'),
        sa.Column('resolved_date', sa.Date, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_fleet_incident_logs_vehicle_id', 'fleet_incident_logs', ['vehicle_id'])


def downgrade() -> None:
    op.drop_table('fleet_incident_logs')
    op.drop_table('fleet_maintenance_records')
    op.drop_table('fleet_fuel_logs')
    op.drop_table('fleet_trips')
    op.drop_table('fleet_vehicles')
    op.drop_table('fleet_drivers')
    for name in [
        'fleetincidentstatus', 'fleetincidenttype', 'fleetmaintenancetype',
        'fleettripstatus', 'fleetfueltype', 'fleetvehiclestatus', 'fleetvehicletype',
        'fleetdriverstatus',
    ]:
        op.execute(f"DROP TYPE IF EXISTS {name}")
