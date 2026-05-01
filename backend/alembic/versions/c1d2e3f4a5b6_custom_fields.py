"""custom_fields

Revision ID: c1d2e3f4a5b6
Revises: b0c1d2e3f4a5
Create Date: 2026-05-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'c1d2e3f4a5b6'
down_revision = 'b0c1d2e3f4a5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'cf_definitions',
        sa.Column('custom_field_id', sa.String(36), primary_key=True),
        sa.Column('field_code', sa.String(100), nullable=False),
        sa.Column('field_label', sa.String(200), nullable=False),
        sa.Column('entity_type', sa.String(30), nullable=False),
        sa.Column('field_type', sa.String(30), nullable=False),
        sa.Column('help_text', sa.Text()),
        sa.Column('placeholder', sa.String(200)),
        sa.Column('default_value', sa.String(500)),
        sa.Column('required_flag', sa.Boolean(), default=False),
        sa.Column('unique_flag', sa.Boolean(), default=False),
        sa.Column('searchable_flag', sa.Boolean(), default=True),
        sa.Column('filterable_flag', sa.Boolean(), default=True),
        sa.Column('reportable_flag', sa.Boolean(), default=True),
        sa.Column('importable_flag', sa.Boolean(), default=True),
        sa.Column('exportable_flag', sa.Boolean(), default=True),
        sa.Column('sensitive_flag', sa.Boolean(), default=False),
        sa.Column('active_flag', sa.Boolean(), default=True),
        sa.Column('display_order', sa.Integer(), default=0),
        sa.Column('section_label', sa.String(100)),
        sa.Column('reference_entity', sa.String(50)),
        sa.Column('formula', sa.Text()),
        sa.Column('created_by', sa.String(100)),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
        sa.UniqueConstraint('field_code', 'entity_type', name='uq_cf_code_entity'),
    )
    op.create_index('ix_cf_definitions_entity', 'cf_definitions', ['entity_type'])

    op.create_table(
        'cf_options',
        sa.Column('option_id', sa.String(36), primary_key=True),
        sa.Column('custom_field_id', sa.String(36),
                  sa.ForeignKey('cf_definitions.custom_field_id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('option_value', sa.String(100), nullable=False),
        sa.Column('option_label', sa.String(200), nullable=False),
        sa.Column('display_order', sa.Integer(), default=0),
        sa.Column('active_flag', sa.Boolean(), default=True),
    )
    op.create_index('ix_cf_options_field', 'cf_options', ['custom_field_id'])

    op.create_table(
        'cf_validation_rules',
        sa.Column('validation_rule_id', sa.String(36), primary_key=True),
        sa.Column('custom_field_id', sa.String(36),
                  sa.ForeignKey('cf_definitions.custom_field_id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('rule_type', sa.String(30), nullable=False),
        sa.Column('rule_value', sa.String(500)),
        sa.Column('error_message', sa.String(300)),
        sa.Column('active_flag', sa.Boolean(), default=True),
    )
    op.create_index('ix_cf_rules_field', 'cf_validation_rules', ['custom_field_id'])

    op.create_table(
        'cf_values',
        sa.Column('value_id', sa.String(36), primary_key=True),
        sa.Column('custom_field_id', sa.String(36),
                  sa.ForeignKey('cf_definitions.custom_field_id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('entity_type', sa.String(30), nullable=False),
        sa.Column('entity_id', sa.String(36), nullable=False),
        sa.Column('value_text', sa.Text()),
        sa.Column('value_number', sa.Float()),
        sa.Column('value_date', sa.DateTime()),
        sa.Column('value_boolean', sa.Boolean()),
        sa.Column('value_json', sa.JSON()),
        sa.Column('file_ref', sa.String(500)),
        sa.Column('updated_by', sa.String(100)),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
        sa.UniqueConstraint('custom_field_id', 'entity_id', name='uq_cf_value'),
    )
    op.create_index('ix_cf_values_entity', 'cf_values', ['entity_type', 'entity_id'])
    op.create_index('ix_cf_values_field', 'cf_values', ['custom_field_id'])

    op.create_table(
        'cf_ai_recommendations',
        sa.Column('rec_id', sa.String(36), primary_key=True),
        sa.Column('agent_type', sa.String(30), nullable=False),
        sa.Column('entity_type', sa.String(50)),
        sa.Column('title', sa.String(300)),
        sa.Column('body', sa.Text()),
        sa.Column('score', sa.Float()),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('rec_metadata', sa.JSON()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )


def downgrade():
    op.drop_table('cf_ai_recommendations')
    op.drop_index('ix_cf_values_field', 'cf_values')
    op.drop_index('ix_cf_values_entity', 'cf_values')
    op.drop_table('cf_values')
    op.drop_index('ix_cf_rules_field', 'cf_validation_rules')
    op.drop_table('cf_validation_rules')
    op.drop_index('ix_cf_options_field', 'cf_options')
    op.drop_table('cf_options')
    op.drop_index('ix_cf_definitions_entity', 'cf_definitions')
    op.drop_table('cf_definitions')
