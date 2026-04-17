"""utility management module — full utility infrastructure schema

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-16 00:00:00.000000

Creates tables for:
  utility_asset_categories, utility_assets, utility_devices,
  utility_tariffs, utility_alarm_rules,
  utility_readings, utility_transactions,
  soft_water_records, boiler_steam_records, compressor_records,
  solar_records, treatment_chemical_records, wastewater_records,
  utility_bills, utility_cost_allocations,
  utility_alarm_events, machine_utility_mappings
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TS = lambda: sa.DateTime(timezone=True)


def upgrade() -> None:

    # ── utility_asset_categories ───────────────────────────────────────────────
    op.create_table(
        'utility_asset_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('utility_type', sa.String(30), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_index('ix_util_asset_cat_code', 'utility_asset_categories', ['code'])
    op.create_index('ix_util_asset_cat_type', 'utility_asset_categories', ['utility_type'])

    # ── utility_assets ─────────────────────────────────────────────────────────
    op.create_table(
        'utility_assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('asset_no', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('utility_type', sa.String(30), nullable=False),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('building_area', sa.String(100), nullable=True),
        sa.Column('department', sa.String(100), nullable=True),
        sa.Column('manufacturer', sa.String(255), nullable=True),
        sa.Column('model', sa.String(255), nullable=True),
        sa.Column('serial_no', sa.String(100), nullable=True),
        sa.Column('install_date', sa.Date(), nullable=True),
        sa.Column('warranty_expiry', sa.Date(), nullable=True),
        sa.Column('rated_capacity', sa.Numeric(14, 3), nullable=True),
        sa.Column('capacity_unit', sa.String(30), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='ACTIVE'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('maintenance_asset_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['utility_asset_categories.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['maintenance_asset_id'], ['assets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_no'),
    )
    op.create_index('ix_utility_assets_asset_no', 'utility_assets', ['asset_no'])
    op.create_index('ix_utility_assets_category_id', 'utility_assets', ['category_id'])
    op.create_index('ix_utility_assets_utility_type', 'utility_assets', ['utility_type'])
    op.create_index('ix_utility_assets_status', 'utility_assets', ['status'])
    op.create_index('ix_utility_assets_building_area', 'utility_assets', ['building_area'])
    op.create_index('ix_utility_assets_department', 'utility_assets', ['department'])

    # ── utility_devices ────────────────────────────────────────────────────────
    op.create_table(
        'utility_devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('device_type', sa.String(30), nullable=False),
        sa.Column('utility_type', sa.String(30), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('building_area', sa.String(100), nullable=True),
        sa.Column('department', sa.String(100), nullable=True),
        sa.Column('manufacturer', sa.String(255), nullable=True),
        sa.Column('model', sa.String(255), nullable=True),
        sa.Column('serial_no', sa.String(100), nullable=True),
        sa.Column('install_date', sa.Date(), nullable=True),
        sa.Column('last_calibration_date', sa.Date(), nullable=True),
        sa.Column('next_calibration_date', sa.Date(), nullable=True),
        sa.Column('unit_of_measure', sa.String(30), nullable=False),
        sa.Column('min_value', sa.Numeric(14, 4), nullable=True),
        sa.Column('max_value', sa.Numeric(14, 4), nullable=True),
        sa.Column('pulse_factor', sa.Numeric(14, 6), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['utility_assets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('device_code'),
    )
    op.create_index('ix_utility_devices_device_code', 'utility_devices', ['device_code'])
    op.create_index('ix_utility_devices_utility_type', 'utility_devices', ['utility_type'])
    op.create_index('ix_utility_devices_asset_id', 'utility_devices', ['asset_id'])
    op.create_index('ix_utility_devices_next_cal', 'utility_devices', ['next_calibration_date'])

    # ── utility_tariffs ────────────────────────────────────────────────────────
    op.create_table(
        'utility_tariffs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tariff_code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('utility_type', sa.String(30), nullable=False),
        sa.Column('tariff_type', sa.String(30), nullable=False, server_default='FLAT'),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('unit', sa.String(30), nullable=False),
        sa.Column('currency_code', sa.String(10), nullable=False, server_default='USD'),
        sa.Column('base_rate', sa.Numeric(14, 6), nullable=False),
        sa.Column('demand_rate', sa.Numeric(14, 6), nullable=True),
        sa.Column('fixed_charge', sa.Numeric(14, 4), nullable=True),
        sa.Column('tax_rate_pct', sa.Numeric(7, 4), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tariff_code'),
    )
    op.create_index('ix_utility_tariffs_tariff_code', 'utility_tariffs', ['tariff_code'])
    op.create_index('ix_utility_tariffs_utility_type', 'utility_tariffs', ['utility_type'])

    # ── utility_alarm_rules ────────────────────────────────────────────────────
    op.create_table(
        'utility_alarm_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rule_code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('utility_type', sa.String(30), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('parameter', sa.String(100), nullable=False),
        sa.Column('operator', sa.String(20), nullable=False),
        sa.Column('threshold_value', sa.Numeric(16, 4), nullable=False),
        sa.Column('threshold_unit', sa.String(30), nullable=True),
        sa.Column('severity', sa.String(20), nullable=False, server_default='WARNING'),
        sa.Column('cooldown_minutes', sa.Integer(), nullable=False, server_default='15'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notification_emails', sa.Text(), nullable=True),
        sa.Column('notification_channel', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['device_id'], ['utility_devices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['asset_id'], ['utility_assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rule_code'),
    )
    op.create_index('ix_util_alarm_rules_rule_code', 'utility_alarm_rules', ['rule_code'])
    op.create_index('ix_util_alarm_rules_device_id', 'utility_alarm_rules', ['device_id'])
    op.create_index('ix_util_alarm_rules_asset_id', 'utility_alarm_rules', ['asset_id'])
    op.create_index('ix_util_alarm_rules_utility_type', 'utility_alarm_rules', ['utility_type'])

    # ── utility_readings ───────────────────────────────────────────────────────
    op.create_table(
        'utility_readings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reading_no', sa.String(50), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reading_datetime', _TS(), nullable=False),
        sa.Column('raw_value', sa.Numeric(18, 4), nullable=False),
        sa.Column('adjusted_value', sa.Numeric(18, 4), nullable=True),
        sa.Column('unit_of_measure', sa.String(30), nullable=False),
        sa.Column('cumulative_value', sa.Numeric(20, 4), nullable=True),
        sa.Column('interval_consumption', sa.Numeric(18, 4), nullable=True),
        sa.Column('source_method', sa.String(20), nullable=False, server_default='MANUAL'),
        sa.Column('quality', sa.String(20), nullable=False, server_default='GOOD'),
        sa.Column('is_anomaly', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('anomaly_note', sa.Text(), nullable=True),
        sa.Column('department', sa.String(100), nullable=True),
        sa.Column('building_area', sa.String(100), nullable=True),
        sa.Column('shift_ref', sa.String(50), nullable=True),
        sa.Column('entered_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['device_id'], ['utility_devices.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['asset_id'], ['utility_assets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['entered_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reading_no'),
    )
    op.create_index('ix_utility_readings_reading_no', 'utility_readings', ['reading_no'])
    op.create_index('ix_utility_readings_device_dt', 'utility_readings', ['device_id', 'reading_datetime'])
    op.create_index('ix_utility_readings_datetime', 'utility_readings', ['reading_datetime'])
    op.create_index('ix_utility_readings_device_id', 'utility_readings', ['device_id'])
    op.create_index('ix_utility_readings_asset_id', 'utility_readings', ['asset_id'])
    op.create_index('ix_utility_readings_department', 'utility_readings', ['department'])

    # ── utility_transactions ───────────────────────────────────────────────────
    op.create_table(
        'utility_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_no', sa.String(50), nullable=False),
        sa.Column('utility_type', sa.String(30), nullable=False),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('period_start', _TS(), nullable=True),
        sa.Column('period_end', _TS(), nullable=True),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('department', sa.String(100), nullable=True),
        sa.Column('building_area', sa.String(100), nullable=True),
        sa.Column('production_line', sa.String(100), nullable=True),
        sa.Column('machine_ref', sa.String(100), nullable=True),
        sa.Column('shift_ref', sa.String(50), nullable=True),
        sa.Column('production_order_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('batch_no', sa.String(100), nullable=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('quantity', sa.Numeric(18, 4), nullable=False),
        sa.Column('unit_of_measure', sa.String(30), nullable=False),
        sa.Column('tariff_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('cost_rate', sa.Numeric(14, 6), nullable=True),
        sa.Column('total_cost', sa.Numeric(16, 4), nullable=True),
        sa.Column('currency_code', sa.String(10), nullable=True, server_default='USD'),
        sa.Column('source_method', sa.String(20), nullable=False, server_default='MANUAL'),
        sa.Column('quality', sa.String(20), nullable=False, server_default='GOOD'),
        sa.Column('is_estimated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_anomaly', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('anomaly_note', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['device_id'], ['utility_devices.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['asset_id'], ['utility_assets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['production_order_id'], ['production_orders.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tariff_id'], ['utility_tariffs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('transaction_no'),
    )
    op.create_index('ix_utility_tx_no', 'utility_transactions', ['transaction_no'])
    op.create_index('ix_utility_tx_type_date', 'utility_transactions', ['utility_type', 'transaction_date'])
    op.create_index('ix_utility_tx_dept_date', 'utility_transactions', ['department', 'transaction_date'])
    op.create_index('ix_utility_tx_prod_order', 'utility_transactions', ['production_order_id'])
    op.create_index('ix_utility_tx_batch_no', 'utility_transactions', ['batch_no'])
    op.create_index('ix_utility_tx_prod_line', 'utility_transactions', ['production_line'])
    op.create_index('ix_utility_tx_machine_ref', 'utility_transactions', ['machine_ref'])

    # ── soft_water_records ─────────────────────────────────────────────────────
    op.create_table(
        'soft_water_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('record_no', sa.String(50), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('record_datetime', _TS(), nullable=False),
        sa.Column('feed_water_hardness_ppm', sa.Numeric(10, 2), nullable=True),
        sa.Column('product_water_hardness_ppm', sa.Numeric(10, 2), nullable=True),
        sa.Column('feed_water_tds_ppm', sa.Numeric(10, 2), nullable=True),
        sa.Column('product_water_tds_ppm', sa.Numeric(10, 2), nullable=True),
        sa.Column('feed_ph', sa.Numeric(5, 2), nullable=True),
        sa.Column('product_ph', sa.Numeric(5, 2), nullable=True),
        sa.Column('flow_rate_lpm', sa.Numeric(10, 3), nullable=True),
        sa.Column('volume_treated_m3', sa.Numeric(14, 3), nullable=True),
        sa.Column('salt_consumed_kg', sa.Numeric(10, 3), nullable=True),
        sa.Column('resin_volume_litres', sa.Numeric(10, 3), nullable=True),
        sa.Column('regeneration_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('service_run_hours', sa.Numeric(10, 2), nullable=True),
        sa.Column('efficiency_pct', sa.Numeric(7, 3), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='ONLINE'),
        sa.Column('source_method', sa.String(20), nullable=False, server_default='MANUAL'),
        sa.Column('is_anomaly', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('anomaly_note', sa.Text(), nullable=True),
        sa.Column('shift_ref', sa.String(50), nullable=True),
        sa.Column('entered_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['utility_assets.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['entered_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('record_no'),
    )
    op.create_index('ix_soft_water_records_record_no', 'soft_water_records', ['record_no'])
    op.create_index('ix_soft_water_asset_dt', 'soft_water_records', ['asset_id', 'record_datetime'])

    # ── boiler_steam_records ───────────────────────────────────────────────────
    op.create_table(
        'boiler_steam_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('record_no', sa.String(50), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('record_datetime', _TS(), nullable=False),
        sa.Column('steam_pressure_bar', sa.Numeric(8, 3), nullable=True),
        sa.Column('steam_temp_c', sa.Numeric(8, 2), nullable=True),
        sa.Column('steam_flow_kgh', sa.Numeric(10, 3), nullable=True),
        sa.Column('steam_quality_pct', sa.Numeric(7, 3), nullable=True),
        sa.Column('feed_water_temp_c', sa.Numeric(8, 2), nullable=True),
        sa.Column('feed_water_flow_lpm', sa.Numeric(10, 3), nullable=True),
        sa.Column('feed_water_ph', sa.Numeric(5, 2), nullable=True),
        sa.Column('feed_water_tds_ppm', sa.Numeric(10, 2), nullable=True),
        sa.Column('blowdown_pct', sa.Numeric(7, 3), nullable=True),
        sa.Column('blowdown_volume_litres', sa.Numeric(12, 3), nullable=True),
        sa.Column('fuel_type', sa.String(50), nullable=True),
        sa.Column('fuel_consumption', sa.Numeric(14, 4), nullable=True),
        sa.Column('fuel_unit', sa.String(20), nullable=True),
        sa.Column('boiler_efficiency_pct', sa.Numeric(7, 3), nullable=True),
        sa.Column('flue_gas_temp_c', sa.Numeric(8, 2), nullable=True),
        sa.Column('o2_pct', sa.Numeric(7, 3), nullable=True),
        sa.Column('co2_pct', sa.Numeric(7, 3), nullable=True),
        sa.Column('co_ppm', sa.Numeric(10, 2), nullable=True),
        sa.Column('boiler_tds_ppm', sa.Numeric(10, 2), nullable=True),
        sa.Column('boiler_ph', sa.Numeric(5, 2), nullable=True),
        sa.Column('boiler_hardness_ppm', sa.Numeric(10, 2), nullable=True),
        sa.Column('conductivity_uscm', sa.Numeric(10, 2), nullable=True),
        sa.Column('running_hours_cumulative', sa.Numeric(12, 2), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='RUNNING'),
        sa.Column('source_method', sa.String(20), nullable=False, server_default='MANUAL'),
        sa.Column('is_anomaly', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('anomaly_note', sa.Text(), nullable=True),
        sa.Column('shift_ref', sa.String(50), nullable=True),
        sa.Column('entered_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['utility_assets.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['entered_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('record_no'),
    )
    op.create_index('ix_boiler_steam_records_record_no', 'boiler_steam_records', ['record_no'])
    op.create_index('ix_boiler_asset_dt', 'boiler_steam_records', ['asset_id', 'record_datetime'])

    # ── compressor_records ─────────────────────────────────────────────────────
    op.create_table(
        'compressor_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('record_no', sa.String(50), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('record_datetime', _TS(), nullable=False),
        sa.Column('inlet_pressure_bar', sa.Numeric(8, 3), nullable=True),
        sa.Column('discharge_pressure_bar', sa.Numeric(8, 3), nullable=True),
        sa.Column('system_pressure_bar', sa.Numeric(8, 3), nullable=True),
        sa.Column('flow_rate_m3h', sa.Numeric(12, 3), nullable=True),
        sa.Column('power_kw', sa.Numeric(10, 3), nullable=True),
        sa.Column('specific_energy_kwh_m3', sa.Numeric(10, 4), nullable=True),
        sa.Column('load_pct', sa.Numeric(7, 3), nullable=True),
        sa.Column('running_hours_cumulative', sa.Numeric(12, 2), nullable=True),
        sa.Column('loaded_hours_cumulative', sa.Numeric(12, 2), nullable=True),
        sa.Column('air_temperature_c', sa.Numeric(8, 2), nullable=True),
        sa.Column('dew_point_c', sa.Numeric(8, 2), nullable=True),
        sa.Column('pressure_dew_point_c', sa.Numeric(8, 2), nullable=True),
        sa.Column('oil_pressure_bar', sa.Numeric(8, 3), nullable=True),
        sa.Column('oil_temp_c', sa.Numeric(8, 2), nullable=True),
        sa.Column('filter_dp_bar', sa.Numeric(8, 4), nullable=True),
        sa.Column('oil_level', sa.String(20), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='RUNNING'),
        sa.Column('source_method', sa.String(20), nullable=False, server_default='MANUAL'),
        sa.Column('is_anomaly', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('anomaly_note', sa.Text(), nullable=True),
        sa.Column('shift_ref', sa.String(50), nullable=True),
        sa.Column('entered_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['utility_assets.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['entered_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('record_no'),
    )
    op.create_index('ix_compressor_records_record_no', 'compressor_records', ['record_no'])
    op.create_index('ix_compressor_asset_dt', 'compressor_records', ['asset_id', 'record_datetime'])

    # ── solar_records ──────────────────────────────────────────────────────────
    op.create_table(
        'solar_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('record_no', sa.String(50), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('record_datetime', _TS(), nullable=False),
        sa.Column('irradiance_wm2', sa.Numeric(10, 3), nullable=True),
        sa.Column('panel_temp_c', sa.Numeric(8, 2), nullable=True),
        sa.Column('ambient_temp_c', sa.Numeric(8, 2), nullable=True),
        sa.Column('dc_voltage_v', sa.Numeric(10, 3), nullable=True),
        sa.Column('dc_current_a', sa.Numeric(10, 3), nullable=True),
        sa.Column('dc_power_kw', sa.Numeric(12, 4), nullable=True),
        sa.Column('ac_power_kw', sa.Numeric(12, 4), nullable=True),
        sa.Column('energy_generated_kwh', sa.Numeric(14, 4), nullable=True),
        sa.Column('grid_export_kwh', sa.Numeric(14, 4), nullable=True),
        sa.Column('self_consumption_kwh', sa.Numeric(14, 4), nullable=True),
        sa.Column('inverter_efficiency_pct', sa.Numeric(7, 3), nullable=True),
        sa.Column('pr_ratio', sa.Numeric(7, 4), nullable=True),
        sa.Column('availability_pct', sa.Numeric(7, 3), nullable=True),
        sa.Column('capacity_factor_pct', sa.Numeric(7, 3), nullable=True),
        sa.Column('source_method', sa.String(20), nullable=False, server_default='IOT'),
        sa.Column('is_anomaly', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('anomaly_note', sa.Text(), nullable=True),
        sa.Column('entered_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['utility_assets.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['entered_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('record_no'),
    )
    op.create_index('ix_solar_records_record_no', 'solar_records', ['record_no'])
    op.create_index('ix_solar_asset_dt', 'solar_records', ['asset_id', 'record_datetime'])

    # ── treatment_chemical_records ─────────────────────────────────────────────
    op.create_table(
        'treatment_chemical_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('record_no', sa.String(50), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('record_datetime', _TS(), nullable=False),
        sa.Column('treatment_type', sa.String(30), nullable=False),
        sa.Column('material_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('chemical_name', sa.String(255), nullable=False),
        sa.Column('quantity_dosed', sa.Numeric(14, 4), nullable=False),
        sa.Column('unit', sa.String(20), nullable=False),
        sa.Column('target_dose_ppm', sa.Numeric(10, 4), nullable=True),
        sa.Column('actual_dose_ppm', sa.Numeric(10, 4), nullable=True),
        sa.Column('water_volume_m3', sa.Numeric(14, 3), nullable=True),
        sa.Column('feed_ph', sa.Numeric(5, 2), nullable=True),
        sa.Column('product_ph', sa.Numeric(5, 2), nullable=True),
        sa.Column('feed_turbidity_ntu', sa.Numeric(10, 3), nullable=True),
        sa.Column('product_turbidity_ntu', sa.Numeric(10, 3), nullable=True),
        sa.Column('residual_chlorine_ppm', sa.Numeric(10, 3), nullable=True),
        sa.Column('tds_feed_ppm', sa.Numeric(10, 2), nullable=True),
        sa.Column('tds_product_ppm', sa.Numeric(10, 2), nullable=True),
        sa.Column('source_method', sa.String(20), nullable=False, server_default='MANUAL'),
        sa.Column('is_anomaly', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('anomaly_note', sa.Text(), nullable=True),
        sa.Column('shift_ref', sa.String(50), nullable=True),
        sa.Column('entered_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['utility_assets.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['entered_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('record_no'),
    )
    op.create_index('ix_treatment_chem_record_no', 'treatment_chemical_records', ['record_no'])
    op.create_index('ix_treatment_asset_dt', 'treatment_chemical_records', ['asset_id', 'record_datetime'])
    op.create_index('ix_treatment_type', 'treatment_chemical_records', ['treatment_type'])

    # ── wastewater_records ─────────────────────────────────────────────────────
    op.create_table(
        'wastewater_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('record_no', sa.String(50), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('record_datetime', _TS(), nullable=False),
        sa.Column('process_stage', sa.String(30), nullable=False, server_default='SECONDARY'),
        sa.Column('influent_flow_m3h', sa.Numeric(12, 3), nullable=True),
        sa.Column('effluent_flow_m3h', sa.Numeric(12, 3), nullable=True),
        sa.Column('influent_cod_mgl', sa.Numeric(10, 3), nullable=True),
        sa.Column('effluent_cod_mgl', sa.Numeric(10, 3), nullable=True),
        sa.Column('influent_bod_mgl', sa.Numeric(10, 3), nullable=True),
        sa.Column('effluent_bod_mgl', sa.Numeric(10, 3), nullable=True),
        sa.Column('influent_tss_mgl', sa.Numeric(10, 3), nullable=True),
        sa.Column('effluent_tss_mgl', sa.Numeric(10, 3), nullable=True),
        sa.Column('influent_ph', sa.Numeric(5, 2), nullable=True),
        sa.Column('effluent_ph', sa.Numeric(5, 2), nullable=True),
        sa.Column('do_mgl', sa.Numeric(8, 3), nullable=True),
        sa.Column('mlss_mgl', sa.Numeric(10, 3), nullable=True),
        sa.Column('mlvss_mgl', sa.Numeric(10, 3), nullable=True),
        sa.Column('svi', sa.Numeric(10, 3), nullable=True),
        sa.Column('srt_days', sa.Numeric(8, 2), nullable=True),
        sa.Column('sludge_produced_kg', sa.Numeric(12, 3), nullable=True),
        sa.Column('sludge_dewatered_pct', sa.Numeric(7, 3), nullable=True),
        sa.Column('power_consumed_kwh', sa.Numeric(14, 4), nullable=True),
        sa.Column('aeration_runtime_hours', sa.Numeric(10, 2), nullable=True),
        sa.Column('compliance_status', sa.String(20), nullable=False, server_default='COMPLIANT'),
        sa.Column('source_method', sa.String(20), nullable=False, server_default='MANUAL'),
        sa.Column('is_anomaly', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('anomaly_note', sa.Text(), nullable=True),
        sa.Column('shift_ref', sa.String(50), nullable=True),
        sa.Column('entered_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['utility_assets.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['entered_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('record_no'),
    )
    op.create_index('ix_wastewater_records_record_no', 'wastewater_records', ['record_no'])
    op.create_index('ix_wastewater_asset_dt', 'wastewater_records', ['asset_id', 'record_datetime'])
    op.create_index('ix_wastewater_compliance', 'wastewater_records', ['compliance_status'])
    op.create_index('ix_wastewater_process_stage', 'wastewater_records', ['process_stage'])

    # ── utility_bills ──────────────────────────────────────────────────────────
    op.create_table(
        'utility_bills',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bill_no', sa.String(50), nullable=False),
        sa.Column('utility_type', sa.String(30), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tariff_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('bill_reference', sa.String(100), nullable=True),
        sa.Column('billing_period_from', sa.Date(), nullable=False),
        sa.Column('billing_period_to', sa.Date(), nullable=False),
        sa.Column('invoice_date', sa.Date(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('consumption_quantity', sa.Numeric(18, 4), nullable=True),
        sa.Column('consumption_unit', sa.String(30), nullable=True),
        sa.Column('base_charge', sa.Numeric(14, 4), nullable=True),
        sa.Column('energy_charge', sa.Numeric(14, 4), nullable=True),
        sa.Column('demand_charge', sa.Numeric(14, 4), nullable=True),
        sa.Column('tax_amount', sa.Numeric(14, 4), nullable=True),
        sa.Column('total_amount', sa.Numeric(16, 4), nullable=False),
        sa.Column('currency_code', sa.String(10), nullable=False, server_default='USD'),
        sa.Column('status', sa.String(20), nullable=False, server_default='RECEIVED'),
        sa.Column('payment_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('verified_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tariff_id'], ['utility_tariffs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['verified_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('bill_no'),
    )
    op.create_index('ix_utility_bills_bill_no', 'utility_bills', ['bill_no'])
    op.create_index('ix_utility_bills_type_period', 'utility_bills', ['utility_type', 'billing_period_from'])
    op.create_index('ix_utility_bills_status', 'utility_bills', ['status'])
    op.create_index('ix_utility_bills_due_date', 'utility_bills', ['due_date'])

    # ── utility_cost_allocations ───────────────────────────────────────────────
    op.create_table(
        'utility_cost_allocations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('allocation_no', sa.String(50), nullable=False),
        sa.Column('utility_type', sa.String(30), nullable=False),
        sa.Column('allocation_date', sa.Date(), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=True),
        sa.Column('period_end', sa.Date(), nullable=True),
        sa.Column('allocation_method', sa.String(20), nullable=False, server_default='METERED'),
        sa.Column('department', sa.String(100), nullable=True),
        sa.Column('production_line', sa.String(100), nullable=True),
        sa.Column('building_area', sa.String(100), nullable=True),
        sa.Column('machine_ref', sa.String(100), nullable=True),
        sa.Column('production_order_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('batch_no', sa.String(100), nullable=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('allocated_quantity', sa.Numeric(18, 4), nullable=True),
        sa.Column('quantity_unit', sa.String(30), nullable=True),
        sa.Column('production_volume_kg', sa.Numeric(18, 3), nullable=True),
        sa.Column('total_cost', sa.Numeric(16, 4), nullable=False),
        sa.Column('allocated_cost', sa.Numeric(16, 4), nullable=False),
        sa.Column('currency_code', sa.String(10), nullable=False, server_default='USD'),
        sa.Column('cost_per_unit', sa.Numeric(14, 6), nullable=True),
        sa.Column('cost_per_ton', sa.Numeric(14, 6), nullable=True),
        sa.Column('bill_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('source_method', sa.String(20), nullable=False, server_default='CALCULATED'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['production_order_id'], ['production_orders.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['bill_id'], ['utility_bills.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('allocation_no'),
    )
    op.create_index('ix_util_cost_alloc_no', 'utility_cost_allocations', ['allocation_no'])
    op.create_index('ix_util_cost_alloc_type_date', 'utility_cost_allocations', ['utility_type', 'allocation_date'])
    op.create_index('ix_util_cost_alloc_dept', 'utility_cost_allocations', ['department', 'allocation_date'])
    op.create_index('ix_util_cost_alloc_prod_order', 'utility_cost_allocations', ['production_order_id'])
    op.create_index('ix_util_cost_alloc_batch', 'utility_cost_allocations', ['batch_no'])
    op.create_index('ix_util_cost_alloc_prod_line', 'utility_cost_allocations', ['production_line'])

    # ── utility_alarm_events ───────────────────────────────────────────────────
    op.create_table(
        'utility_alarm_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_no', sa.String(50), nullable=False),
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('triggered_at', _TS(), nullable=False),
        sa.Column('acknowledged_at', _TS(), nullable=True),
        sa.Column('resolved_at', _TS(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='ACTIVE'),
        sa.Column('severity', sa.String(20), nullable=False, server_default='WARNING'),
        sa.Column('triggered_value', sa.Numeric(18, 4), nullable=True),
        sa.Column('threshold_value', sa.Numeric(18, 4), nullable=True),
        sa.Column('threshold_unit', sa.String(30), nullable=True),
        sa.Column('parameter', sa.String(100), nullable=True),
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('corrective_action', sa.Text(), nullable=True),
        sa.Column('acknowledged_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resolved_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['rule_id'], ['utility_alarm_rules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['device_id'], ['utility_devices.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['asset_id'], ['utility_assets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['acknowledged_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['resolved_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_no'),
    )
    op.create_index('ix_util_alarm_events_event_no', 'utility_alarm_events', ['event_no'])
    op.create_index('ix_alarm_events_status', 'utility_alarm_events', ['status'])
    op.create_index('ix_alarm_events_rule_dt', 'utility_alarm_events', ['rule_id', 'triggered_at'])
    op.create_index('ix_alarm_events_triggered_at', 'utility_alarm_events', ['triggered_at'])
    op.create_index('ix_alarm_events_device_id', 'utility_alarm_events', ['device_id'])
    op.create_index('ix_alarm_events_asset_id', 'utility_alarm_events', ['asset_id'])

    # ── machine_utility_mappings ───────────────────────────────────────────────
    op.create_table(
        'machine_utility_mappings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('machine_ref', sa.String(100), nullable=False),
        sa.Column('machine_name', sa.String(255), nullable=False),
        sa.Column('department', sa.String(100), nullable=True),
        sa.Column('production_line', sa.String(100), nullable=True),
        sa.Column('building_area', sa.String(100), nullable=True),
        sa.Column('utility_type', sa.String(30), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('allocation_pct', sa.Numeric(7, 4), nullable=True),
        sa.Column('rated_consumption', sa.Numeric(14, 4), nullable=True),
        sa.Column('rated_unit', sa.String(30), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', _TS(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['device_id'], ['utility_devices.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['asset_id'], ['utility_assets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('machine_ref', 'utility_type', 'device_id', name='uq_machine_utility_device'),
    )
    op.create_index('ix_machine_util_map_machine_ref', 'machine_utility_mappings', ['machine_ref'])
    op.create_index('ix_machine_util_map_utility_type', 'machine_utility_mappings', ['utility_type'])
    op.create_index('ix_machine_util_map_dept_line', 'machine_utility_mappings', ['department', 'production_line'])


def downgrade() -> None:
    # Drop in reverse FK dependency order
    op.drop_index('ix_machine_util_map_dept_line', table_name='machine_utility_mappings')
    op.drop_index('ix_machine_util_map_utility_type', table_name='machine_utility_mappings')
    op.drop_index('ix_machine_util_map_machine_ref', table_name='machine_utility_mappings')
    op.drop_table('machine_utility_mappings')

    op.drop_index('ix_alarm_events_asset_id', table_name='utility_alarm_events')
    op.drop_index('ix_alarm_events_device_id', table_name='utility_alarm_events')
    op.drop_index('ix_alarm_events_triggered_at', table_name='utility_alarm_events')
    op.drop_index('ix_alarm_events_rule_dt', table_name='utility_alarm_events')
    op.drop_index('ix_alarm_events_status', table_name='utility_alarm_events')
    op.drop_index('ix_util_alarm_events_event_no', table_name='utility_alarm_events')
    op.drop_table('utility_alarm_events')

    op.drop_index('ix_util_cost_alloc_prod_line', table_name='utility_cost_allocations')
    op.drop_index('ix_util_cost_alloc_batch', table_name='utility_cost_allocations')
    op.drop_index('ix_util_cost_alloc_prod_order', table_name='utility_cost_allocations')
    op.drop_index('ix_util_cost_alloc_dept', table_name='utility_cost_allocations')
    op.drop_index('ix_util_cost_alloc_type_date', table_name='utility_cost_allocations')
    op.drop_index('ix_util_cost_alloc_no', table_name='utility_cost_allocations')
    op.drop_table('utility_cost_allocations')

    op.drop_index('ix_utility_bills_due_date', table_name='utility_bills')
    op.drop_index('ix_utility_bills_status', table_name='utility_bills')
    op.drop_index('ix_utility_bills_type_period', table_name='utility_bills')
    op.drop_index('ix_utility_bills_bill_no', table_name='utility_bills')
    op.drop_table('utility_bills')

    op.drop_index('ix_wastewater_process_stage', table_name='wastewater_records')
    op.drop_index('ix_wastewater_compliance', table_name='wastewater_records')
    op.drop_index('ix_wastewater_asset_dt', table_name='wastewater_records')
    op.drop_index('ix_wastewater_records_record_no', table_name='wastewater_records')
    op.drop_table('wastewater_records')

    op.drop_index('ix_treatment_type', table_name='treatment_chemical_records')
    op.drop_index('ix_treatment_asset_dt', table_name='treatment_chemical_records')
    op.drop_index('ix_treatment_chem_record_no', table_name='treatment_chemical_records')
    op.drop_table('treatment_chemical_records')

    op.drop_index('ix_solar_asset_dt', table_name='solar_records')
    op.drop_index('ix_solar_records_record_no', table_name='solar_records')
    op.drop_table('solar_records')

    op.drop_index('ix_compressor_asset_dt', table_name='compressor_records')
    op.drop_index('ix_compressor_records_record_no', table_name='compressor_records')
    op.drop_table('compressor_records')

    op.drop_index('ix_boiler_asset_dt', table_name='boiler_steam_records')
    op.drop_index('ix_boiler_steam_records_record_no', table_name='boiler_steam_records')
    op.drop_table('boiler_steam_records')

    op.drop_index('ix_soft_water_asset_dt', table_name='soft_water_records')
    op.drop_index('ix_soft_water_records_record_no', table_name='soft_water_records')
    op.drop_table('soft_water_records')

    op.drop_index('ix_utility_tx_machine_ref', table_name='utility_transactions')
    op.drop_index('ix_utility_tx_prod_line', table_name='utility_transactions')
    op.drop_index('ix_utility_tx_batch_no', table_name='utility_transactions')
    op.drop_index('ix_utility_tx_prod_order', table_name='utility_transactions')
    op.drop_index('ix_utility_tx_dept_date', table_name='utility_transactions')
    op.drop_index('ix_utility_tx_type_date', table_name='utility_transactions')
    op.drop_index('ix_utility_tx_no', table_name='utility_transactions')
    op.drop_table('utility_transactions')

    op.drop_index('ix_utility_readings_department', table_name='utility_readings')
    op.drop_index('ix_utility_readings_asset_id', table_name='utility_readings')
    op.drop_index('ix_utility_readings_device_id', table_name='utility_readings')
    op.drop_index('ix_utility_readings_datetime', table_name='utility_readings')
    op.drop_index('ix_utility_readings_device_dt', table_name='utility_readings')
    op.drop_index('ix_utility_readings_reading_no', table_name='utility_readings')
    op.drop_table('utility_readings')

    op.drop_index('ix_util_alarm_rules_utility_type', table_name='utility_alarm_rules')
    op.drop_index('ix_util_alarm_rules_asset_id', table_name='utility_alarm_rules')
    op.drop_index('ix_util_alarm_rules_device_id', table_name='utility_alarm_rules')
    op.drop_index('ix_util_alarm_rules_rule_code', table_name='utility_alarm_rules')
    op.drop_table('utility_alarm_rules')

    op.drop_index('ix_utility_tariffs_utility_type', table_name='utility_tariffs')
    op.drop_index('ix_utility_tariffs_tariff_code', table_name='utility_tariffs')
    op.drop_table('utility_tariffs')

    op.drop_index('ix_utility_devices_next_cal', table_name='utility_devices')
    op.drop_index('ix_utility_devices_asset_id', table_name='utility_devices')
    op.drop_index('ix_utility_devices_utility_type', table_name='utility_devices')
    op.drop_index('ix_utility_devices_device_code', table_name='utility_devices')
    op.drop_table('utility_devices')

    op.drop_index('ix_utility_assets_department', table_name='utility_assets')
    op.drop_index('ix_utility_assets_building_area', table_name='utility_assets')
    op.drop_index('ix_utility_assets_status', table_name='utility_assets')
    op.drop_index('ix_utility_assets_utility_type', table_name='utility_assets')
    op.drop_index('ix_utility_assets_category_id', table_name='utility_assets')
    op.drop_index('ix_utility_assets_asset_no', table_name='utility_assets')
    op.drop_table('utility_assets')

    op.drop_index('ix_util_asset_cat_type', table_name='utility_asset_categories')
    op.drop_index('ix_util_asset_cat_code', table_name='utility_asset_categories')
    op.drop_table('utility_asset_categories')
