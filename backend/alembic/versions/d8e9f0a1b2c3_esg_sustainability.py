"""esg_sustainability_reporting

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-05-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'd8e9f0a1b2c3'
down_revision = 'c7d8e9f0a1b2'
branch_labels = None
depends_on = None

SOURCE_TYPES = ['FUEL_DIESEL', 'FUEL_PETROL', 'FUEL_LPG', 'ELECTRICITY_GRID', 'ELECTRICITY_SOLAR',
                'TRANSPORT_ROAD', 'TRANSPORT_AIR', 'MATERIAL', 'WATER',
                'WASTE_GENERAL', 'WASTE_HAZARDOUS', 'WASTE_RECYCLED']
SCOPES = ['SCOPE1', 'SCOPE2', 'SCOPE3']
METRIC_TYPES = ['ENERGY', 'WATER', 'WASTE', 'RECYCLING', 'EMISSIONS']


def upgrade() -> None:
    source_type_enum = postgresql.ENUM(*SOURCE_TYPES, name='sourcetype')
    emission_scope_enum = postgresql.ENUM(*SCOPES, name='emissionscope')
    metric_type_enum = postgresql.ENUM(*METRIC_TYPES, name='esgmetrictype')
    source_type_enum.create(op.get_bind(), checkfirst=True)
    emission_scope_enum.create(op.get_bind(), checkfirst=True)
    metric_type_enum.create(op.get_bind(), checkfirst=True)

    # esg_activities
    op.create_table(
        'esg_activities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_type', sa.Enum(*SOURCE_TYPES, name='sourcetype'), nullable=False),
        sa.Column('source_reference', sa.String(200), nullable=True),
        sa.Column('activity_date', sa.Date(), nullable=False),
        sa.Column('quantity', sa.Numeric(18, 4), nullable=False),
        sa.Column('unit', sa.String(20), nullable=False),
        sa.Column('location_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='SET NULL'), nullable=True),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('suppliers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_auto_imported', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_esg_activities_source_type', 'esg_activities', ['source_type'])
    op.create_index('ix_esg_activities_activity_date', 'esg_activities', ['activity_date'])

    # esg_emission_factors
    op.create_table(
        'esg_emission_factors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('factor_code', sa.String(50), nullable=False, unique=True),
        sa.Column('source_type', sa.Enum(*SOURCE_TYPES, name='sourcetype'), nullable=False),
        sa.Column('region', sa.String(10), nullable=False, server_default='KE'),
        sa.Column('valid_from', sa.Date(), nullable=False),
        sa.Column('valid_to', sa.Date(), nullable=True),
        sa.Column('factor_value', sa.Numeric(18, 8), nullable=False),
        sa.Column('unit', sa.String(50), nullable=False),
        sa.Column('scope', sa.Enum(*SCOPES, name='emissionscope'), nullable=False),
        sa.Column('source_reference', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_esg_emission_factors_source_type', 'esg_emission_factors', ['source_type'])
    op.create_index('ix_esg_emission_factors_factor_code', 'esg_emission_factors', ['factor_code'])

    # esg_emission_records
    op.create_table(
        'esg_emission_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('activity_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('esg_activities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('factor_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('esg_emission_factors.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('calculated_emission_kgco2e', sa.Numeric(18, 4), nullable=False),
        sa.Column('scope', sa.Enum(*SCOPES, name='emissionscope'), nullable=False),
        sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_esg_emission_records_activity_id', 'esg_emission_records', ['activity_id'])
    op.create_index('ix_esg_emission_records_scope', 'esg_emission_records', ['scope'])

    # esg_resource_metrics
    op.create_table(
        'esg_resource_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('metric_type', sa.Enum(*METRIC_TYPES, name='esgmetrictype'), nullable=False),
        sa.Column('quantity', sa.Numeric(18, 4), nullable=False),
        sa.Column('unit', sa.String(20), nullable=False),
        sa.Column('location_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('warehouses.id', ondelete='SET NULL'), nullable=True),
        sa.Column('period_from', sa.Date(), nullable=False),
        sa.Column('period_to', sa.Date(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_esg_resource_metrics_metric_type', 'esg_resource_metrics', ['metric_type'])

    # esg_targets
    op.create_table(
        'esg_targets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('metric_type', sa.Enum(*METRIC_TYPES, name='esgmetrictype'), nullable=False),
        sa.Column('scope', sa.Enum(*SCOPES, name='emissionscope'), nullable=True),
        sa.Column('baseline_year', sa.Integer(), nullable=False),
        sa.Column('baseline_value', sa.Numeric(18, 4), nullable=False),
        sa.Column('target_value', sa.Numeric(18, 4), nullable=False),
        sa.Column('unit', sa.String(20), nullable=False),
        sa.Column('target_date', sa.Date(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('esg_targets')
    op.drop_table('esg_resource_metrics')
    op.drop_table('esg_emission_records')
    op.drop_table('esg_emission_factors')
    op.drop_table('esg_activities')
    op.execute("DROP TYPE IF EXISTS sourcetype")
    op.execute("DROP TYPE IF EXISTS emissionscope")
    op.execute("DROP TYPE IF EXISTS esgmetrictype")
