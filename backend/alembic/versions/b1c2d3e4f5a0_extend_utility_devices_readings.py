"""extend utility_devices and utility_readings with device-typing and reading-validation columns

Revision ID: b1c2d3e4f5a0
Revises: f6a7b8c9d0e1
Create Date: 2026-04-16 00:00:00.000000

Adds:
  utility_devices  — reading_type, related_line_id, related_machine_id,
                     reading_source, reading_frequency,
                     min_alarm_limit, max_alarm_limit,
                     calibration_required, calibration_frequency_days
  utility_readings — source_reference, validated_status, validation_notes, batch_id
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b1c2d3e4f5a0'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── utility_devices ────────────────────────────────────────────────────────
    op.add_column('utility_devices', sa.Column('reading_type', sa.String(30), nullable=True))
    op.add_column('utility_devices', sa.Column('related_line_id', sa.String(100), nullable=True))
    op.add_column('utility_devices', sa.Column('related_machine_id', sa.String(100), nullable=True))
    op.add_column('utility_devices', sa.Column('reading_source', sa.String(30), nullable=True))
    op.add_column('utility_devices', sa.Column('reading_frequency', sa.String(50), nullable=True))
    op.add_column('utility_devices', sa.Column('min_alarm_limit', sa.Numeric(14, 4), nullable=True))
    op.add_column('utility_devices', sa.Column('max_alarm_limit', sa.Numeric(14, 4), nullable=True))
    op.add_column('utility_devices', sa.Column(
        'calibration_required', sa.Boolean(), nullable=False, server_default='false'
    ))
    op.add_column('utility_devices', sa.Column('calibration_frequency_days', sa.Integer(), nullable=True))

    op.create_index('ix_utility_devices_related_line',    'utility_devices', ['related_line_id'])
    op.create_index('ix_utility_devices_related_machine', 'utility_devices', ['related_machine_id'])

    # ── utility_readings ───────────────────────────────────────────────────────
    op.add_column('utility_readings', sa.Column('source_reference', sa.String(255), nullable=True))
    op.add_column('utility_readings', sa.Column(
        'validated_status', sa.String(20), nullable=False, server_default='PENDING'
    ))
    op.add_column('utility_readings', sa.Column('validation_notes', sa.Text(), nullable=True))
    op.add_column('utility_readings', sa.Column('batch_id', sa.String(100), nullable=True))

    op.create_index('ix_utility_readings_validated_status', 'utility_readings', ['validated_status'])
    op.create_index('ix_utility_readings_batch_id',         'utility_readings', ['batch_id'])


def downgrade() -> None:
    op.drop_index('ix_utility_readings_batch_id',         table_name='utility_readings')
    op.drop_index('ix_utility_readings_validated_status', table_name='utility_readings')
    op.drop_column('utility_readings', 'batch_id')
    op.drop_column('utility_readings', 'validation_notes')
    op.drop_column('utility_readings', 'validated_status')
    op.drop_column('utility_readings', 'source_reference')

    op.drop_index('ix_utility_devices_related_machine', table_name='utility_devices')
    op.drop_index('ix_utility_devices_related_line',    table_name='utility_devices')
    op.drop_column('utility_devices', 'calibration_frequency_days')
    op.drop_column('utility_devices', 'calibration_required')
    op.drop_column('utility_devices', 'max_alarm_limit')
    op.drop_column('utility_devices', 'min_alarm_limit')
    op.drop_column('utility_devices', 'reading_frequency')
    op.drop_column('utility_devices', 'reading_source')
    op.drop_column('utility_devices', 'related_machine_id')
    op.drop_column('utility_devices', 'related_line_id')
    op.drop_column('utility_devices', 'reading_type')
