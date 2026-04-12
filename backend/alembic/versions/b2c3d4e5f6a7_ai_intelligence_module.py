"""ai intelligence module - predictions, recommendations, formulations, scenarios

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-10 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ai_requests
    op.create_table(
        'ai_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('request_type', sa.String(30), nullable=False),
        sa.Column('provider', sa.String(20), nullable=False),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('input_data', postgresql.JSON(), nullable=True),
        sa.Column('output_data', postgresql.JSON(), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # ai_predictions
    op.create_table(
        'ai_predictions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('request_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('prediction_type', sa.String(50), nullable=False),
        sa.Column('subject_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('subject_name', sa.String(255), nullable=True),
        sa.Column('period', sa.String(20), nullable=True),
        sa.Column('forecast_value', sa.Numeric(18, 4), nullable=True),
        sa.Column('confidence_score', sa.Numeric(5, 4), nullable=True),
        sa.Column('risk_level', sa.String(20), nullable=True),
        sa.Column('trend', sa.String(20), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('details', postgresql.JSON(), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['ai_requests.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # ai_recommendations
    op.create_table(
        'ai_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('request_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('expected_impact', sa.Text(), nullable=True),
        sa.Column('confidence_level', sa.String(20), nullable=True),
        sa.Column('priority', sa.String(20), nullable=True),
        sa.Column('action_data', postgresql.JSON(), nullable=True),
        sa.Column('is_actioned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_dismissed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['ai_requests.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # ai_formulations
    op.create_table(
        'ai_formulations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('request_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('product_category', sa.String(100), nullable=False),
        sa.Column('version', sa.String(50), nullable=False, server_default='standard'),
        sa.Column('target_properties', postgresql.JSON(), nullable=True),
        sa.Column('cost_target', sa.Numeric(14, 4), nullable=True),
        sa.Column('performance_priority', sa.String(20), nullable=True),
        sa.Column('formulation_data', postgresql.JSON(), nullable=False),
        sa.Column('estimated_cost_per_kg', sa.Numeric(14, 4), nullable=True),
        sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_favorite', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['ai_requests.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # ai_scenarios
    op.create_table(
        'ai_scenarios',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('request_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('scenario_type', sa.String(50), nullable=False),
        sa.Column('input_parameters', postgresql.JSON(), nullable=True),
        sa.Column('expected_impact', sa.Text(), nullable=True),
        sa.Column('risks', postgresql.JSON(), nullable=True),
        sa.Column('opportunities', postgresql.JSON(), nullable=True),
        sa.Column('simulation_data', postgresql.JSON(), nullable=False),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['ai_requests.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('ai_scenarios')
    op.drop_table('ai_formulations')
    op.drop_table('ai_recommendations')
    op.drop_table('ai_predictions')
    op.drop_table('ai_requests')
