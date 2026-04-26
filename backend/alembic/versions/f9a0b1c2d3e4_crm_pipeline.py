"""crm_pipeline

Revision ID: f9a0b1c2d3e4
Revises: e7f8a9b0c1d2
Create Date: 2026-04-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'f9a0b1c2d3e4'
down_revision = 'e7f8a9b0c1d2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # crm_pipeline_stages
    op.create_table(
        'crm_pipeline_stages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stage_code', sa.String(50), nullable=False),
        sa.Column('stage_name', sa.String(100), nullable=False),
        sa.Column('stage_type', sa.Enum('LEAD', 'OPPORTUNITY', 'TERMINAL', 'NURTURING', name='crmstagetyp'), nullable=False),
        sa.Column('default_probability', sa.Numeric(5, 2), nullable=True),
        sa.Column('sequence_no', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('active_flag', sa.Boolean(), server_default='true'),
        sa.Column('color_code', sa.String(20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stage_code'),
    )

    # crm_records
    op.create_table(
        'crm_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('record_type', sa.Enum('LEAD', 'OPPORTUNITY', name='crmrecordtyp'), nullable=False),
        sa.Column('lead_code', sa.String(50), nullable=True),
        sa.Column('opportunity_code', sa.String(50), nullable=True),
        sa.Column('account_type', sa.Enum('PROSPECT', 'CUSTOMER', 'DISTRIBUTOR', 'RETAILER', 'MODERN_TRADE', 'INSTITUTIONAL', 'SUPPLIER_XSELL', 'OTHER', name='crmaccountt'), nullable=True),
        sa.Column('company_name', sa.String(200), nullable=False),
        sa.Column('contact_person_name', sa.String(200), nullable=True),
        sa.Column('contact_email', sa.String(200), nullable=True),
        sa.Column('contact_phone', sa.String(50), nullable=True),
        sa.Column('alternate_contact', sa.String(200), nullable=True),
        sa.Column('customer_id', sa.String(50), nullable=True),
        sa.Column('distributor_id', sa.String(50), nullable=True),
        sa.Column('source_type', sa.Enum('WEBSITE', 'REFERRAL', 'FIELD_SALES', 'EVENT', 'OUTBOUND', 'INBOUND', 'CAMPAIGN', 'MANUAL', 'IMPORT', name='crmsourcety'), nullable=True),
        sa.Column('source_detail', sa.String(200), nullable=True),
        sa.Column('region_id', sa.String(50), nullable=True),
        sa.Column('country_id', sa.String(50), nullable=True),
        sa.Column('channel_id', sa.String(50), nullable=True),
        sa.Column('industry_segment', sa.String(100), nullable=True),
        sa.Column('assigned_rep_id', sa.String(50), nullable=True),
        sa.Column('assigned_team_id', sa.String(50), nullable=True),
        sa.Column('stage_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('crm_pipeline_stages.id'), nullable=True),
        sa.Column('probability_pct', sa.Numeric(5, 2), nullable=True),
        sa.Column('probability_override', sa.Boolean(), server_default='false'),
        sa.Column('expected_close_date', sa.Date(), nullable=True),
        sa.Column('expected_revenue', sa.Numeric(18, 2), nullable=True),
        sa.Column('expected_margin', sa.Numeric(18, 2), nullable=True),
        sa.Column('currency', sa.String(10), server_default='KES'),
        sa.Column('lead_score', sa.Integer(), server_default='0'),
        sa.Column('temperature', sa.Enum('COLD', 'WARM', 'HOT', name='crmtemperatu'), nullable=True),
        sa.Column('next_action_date', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum('OPEN', 'WON', 'LOST', 'ON_HOLD', 'ARCHIVED', name='crmstatus'), nullable=True),
        sa.Column('qualified_flag', sa.Boolean(), server_default='false'),
        sa.Column('qualified_date', sa.Date(), nullable=True),
        sa.Column('converted_date', sa.Date(), nullable=True),
        sa.Column('linked_quotation_id', sa.String(50), nullable=True),
        sa.Column('linked_order_id', sa.String(50), nullable=True),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lead_code'),
        sa.UniqueConstraint('opportunity_code'),
    )

    # crm_interest_lines
    op.create_table(
        'crm_interest_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('crm_record_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('crm_records.id'), nullable=False),
        sa.Column('item_id', sa.String(50), nullable=True),
        sa.Column('item_name', sa.String(200), nullable=True),
        sa.Column('category_id', sa.String(50), nullable=True),
        sa.Column('brand_id', sa.String(50), nullable=True),
        sa.Column('expected_qty', sa.Numeric(18, 3), nullable=True),
        sa.Column('expected_frequency', sa.String(50), nullable=True),
        sa.Column('expected_value', sa.Numeric(18, 2), nullable=True),
        sa.Column('competitive_brand', sa.String(200), nullable=True),
        sa.Column('competitor_price', sa.Numeric(18, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # crm_activities
    op.create_table(
        'crm_activities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('crm_record_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('crm_records.id'), nullable=False),
        sa.Column('activity_type', sa.Enum('CALL', 'EMAIL', 'MEETING', 'WHATSAPP', 'VISIT', 'TASK', 'NOTE', 'DEMO', 'SAMPLE_SENT', 'QUOTATION_SENT', 'NEGOTIATION', 'COMPLAINT_FOLLOWUP', 'OTHER', name='crmactivityt'), nullable=False),
        sa.Column('subject', sa.String(300), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('activity_datetime', sa.DateTime(), nullable=True),
        sa.Column('due_datetime', sa.DateTime(), nullable=True),
        sa.Column('completed_datetime', sa.DateTime(), nullable=True),
        sa.Column('assigned_to', sa.String(50), nullable=True),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('result_status', sa.Enum('PLANNED', 'COMPLETED', 'NO_RESPONSE', 'RESCHEDULED', 'CANCELLED', name='crmactivityr'), nullable=True),
        sa.Column('outcome_code', sa.String(100), nullable=True),
        sa.Column('next_step', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # crm_competitors
    op.create_table(
        'crm_competitors',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('crm_record_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('crm_records.id'), nullable=False),
        sa.Column('competitor_name', sa.String(200), nullable=False),
        sa.Column('competitor_product', sa.String(200), nullable=True),
        sa.Column('offer_type', sa.String(100), nullable=True),
        sa.Column('competitor_price', sa.Numeric(18, 2), nullable=True),
        sa.Column('competitor_strength', sa.Text(), nullable=True),
        sa.Column('competitor_weakness', sa.Text(), nullable=True),
        sa.Column('risk_level', sa.String(20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # crm_win_loss
    op.create_table(
        'crm_win_loss',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('crm_record_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('crm_records.id'), nullable=False),
        sa.Column('final_status', sa.String(10), nullable=False),
        sa.Column('close_date', sa.Date(), nullable=True),
        sa.Column('final_revenue', sa.Numeric(18, 2), nullable=True),
        sa.Column('final_margin', sa.Numeric(18, 2), nullable=True),
        sa.Column('loss_reason_code', sa.Enum('PRICE_TOO_HIGH', 'COMPETITOR_RELATION', 'PRODUCT_MISMATCH', 'TIMELINE_ISSUE', 'NO_BUDGET', 'NO_RESPONSE', 'COMPETITOR_PROMO', 'DISTRIBUTOR_CONFLICT', 'CAPACITY_SUPPLY', 'INTERNAL_FOLLOWUP', 'OTHER', name='crmlossreason'), nullable=True),
        sa.Column('win_reason_code', sa.Enum('BETTER_PRICE', 'BETTER_PRODUCT_FIT', 'FASTER_RESPONSE', 'STRONGER_RELATION', 'AVAILABILITY', 'TECHNICAL_SUPPORT', 'PROMOTION_SUPPORT', 'OTHER', name='crmwinreason'), nullable=True),
        sa.Column('competitor_name', sa.String(200), nullable=True),
        sa.Column('narrative', sa.Text(), nullable=True),
        sa.Column('recorded_by', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('crm_record_id'),
    )

    # crm_ai_recommendations
    op.create_table(
        'crm_ai_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_type', sa.Enum('LEAD_PRIORITIZATION', 'PIPELINE_RISK', 'WIN_LOSS_INSIGHT', name='crmaiagentt'), nullable=False),
        sa.Column('crm_record_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('crm_records.id'), nullable=True),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('priority', sa.String(20), nullable=True),
        sa.Column('action_label', sa.String(100), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'ACKNOWLEDGED', 'ACTIONED', 'DISMISSED', name='crmairectst'), nullable=True),
        sa.Column('acknowledged_by', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('crm_ai_recommendations')
    op.drop_table('crm_win_loss')
    op.drop_table('crm_competitors')
    op.drop_table('crm_activities')
    op.drop_table('crm_interest_lines')
    op.drop_table('crm_records')
    op.drop_table('crm_pipeline_stages')
    op.execute("DROP TYPE IF EXISTS crmairectst")
    op.execute("DROP TYPE IF EXISTS crmaiagentt")
    op.execute("DROP TYPE IF EXISTS crmwinreason")
    op.execute("DROP TYPE IF EXISTS crmlossreason")
    op.execute("DROP TYPE IF EXISTS crmactivityr")
    op.execute("DROP TYPE IF EXISTS crmactivityt")
    op.execute("DROP TYPE IF EXISTS crmstatus")
    op.execute("DROP TYPE IF EXISTS crmtemperatu")
    op.execute("DROP TYPE IF EXISTS crmsourcety")
    op.execute("DROP TYPE IF EXISTS crmaccountt")
    op.execute("DROP TYPE IF EXISTS crmrecordtyp")
    op.execute("DROP TYPE IF EXISTS crmstagetyp")
