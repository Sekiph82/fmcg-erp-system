"""customer_distributor_portal

Revision ID: a9b0c1d2e3f4
Revises: f9a0b1c2d3e4
Create Date: 2026-04-26 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a9b0c1d2e3f4'
down_revision = 'f9a0b1c2d3e4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'portal_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_code', sa.String(50), nullable=False),
        sa.Column('account_type', sa.Enum('CUSTOMER', 'DISTRIBUTOR', 'KEY_ACCOUNT', 'RETAILER', 'INSTITUTIONAL', 'MIXED', name='portalaccountt'), nullable=False),
        sa.Column('linked_customer_id', sa.String(50), nullable=True),
        sa.Column('linked_distributor_id', sa.String(50), nullable=True),
        sa.Column('portal_status', sa.Enum('PENDING', 'ACTIVE', 'SUSPENDED', 'CLOSED', name='portalaccounts'), nullable=False),
        sa.Column('default_currency', sa.String(10), server_default='KES'),
        sa.Column('preferred_language', sa.String(10), server_default='en'),
        sa.Column('order_mode', sa.Enum('DIRECT_SUBMIT', 'DRAFT_REQUEST', 'REORDER_ONLY', name='portalorderm'), nullable=True),
        sa.Column('primary_contact_name', sa.String(200), nullable=True),
        sa.Column('primary_contact_email', sa.String(200), nullable=True),
        sa.Column('primary_contact_phone', sa.String(50), nullable=True),
        sa.Column('timezone', sa.String(50), server_default='Africa/Nairobi'),
        sa.Column('can_view_prices', sa.Boolean(), server_default='true'),
        sa.Column('can_view_promotions', sa.Boolean(), server_default='false'),
        sa.Column('can_initiate_payment', sa.Boolean(), server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('account_code'),
    )

    op.create_table(
        'portal_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('portal_account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('portal_accounts.id'), nullable=False),
        sa.Column('full_name', sa.String(200), nullable=False),
        sa.Column('email', sa.String(200), nullable=False),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('login_identifier', sa.String(200), nullable=True),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('role_type', sa.Enum('OWNER', 'FINANCE', 'BUYER', 'LOGISTICS', 'VIEWER', 'CUSTOM', name='portaluserro'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('invited_by', sa.String(200), nullable=True),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('invitation_token', sa.String(255), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('login_identifier'),
    )

    op.create_table(
        'portal_activity_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('portal_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('portal_users.id'), nullable=False),
        sa.Column('portal_account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('portal_accounts.id'), nullable=True),
        sa.Column('activity_type', sa.Enum('LOGIN', 'VIEW_ORDER', 'DOWNLOAD_INVOICE', 'SUBMIT_ORDER', 'INITIATE_PAYMENT', 'SUBMIT_RETURN', 'SUBMIT_CLAIM', 'DOWNLOAD_STATEMENT', 'VIEW_SHIPMENT', 'DOWNLOAD_DOCUMENT', 'INVITE_USER', 'OTHER', name='portalactivit'), nullable=False),
        sa.Column('reference_type', sa.String(50), nullable=True),
        sa.Column('reference_id', sa.String(50), nullable=True),
        sa.Column('activity_datetime', sa.DateTime(), nullable=False),
        sa.Column('ip_or_session_ref', sa.String(200), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'portal_claims',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('claim_no', sa.String(50), nullable=False),
        sa.Column('portal_account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('portal_accounts.id'), nullable=False),
        sa.Column('submitted_by', sa.String(50), nullable=True),
        sa.Column('claim_type', sa.Enum('RETURN_REQUEST', 'SHORTAGE_CLAIM', 'DAMAGE_CLAIM', 'DELIVERY_DISCREPANCY', 'PRICING_DISPUTE', 'PRODUCT_COMPLAINT', 'INVOICE_DISPUTE', 'OTHER', name='portalclaimt'), nullable=False),
        sa.Column('linked_order_id', sa.String(50), nullable=True),
        sa.Column('linked_invoice_id', sa.String(50), nullable=True),
        sa.Column('linked_shipment_id', sa.String(50), nullable=True),
        sa.Column('linked_lot_id', sa.String(50), nullable=True),
        sa.Column('quantity_involved', sa.Numeric(18, 3), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('SUBMITTED', 'UNDER_REVIEW', 'RESOLVED', 'REJECTED', 'CLOSED', name='portalclaims'), nullable=False),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('resolved_by', sa.String(50), nullable=True),
        sa.Column('resolved_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('claim_no'),
    )

    op.create_table(
        'portal_draft_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('draft_no', sa.String(50), nullable=False),
        sa.Column('portal_account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('portal_accounts.id'), nullable=False),
        sa.Column('submitted_by', sa.String(50), nullable=True),
        sa.Column('source_order_id', sa.String(50), nullable=True),
        sa.Column('requested_delivery_date', sa.Date(), nullable=True),
        sa.Column('delivery_address', sa.Text(), nullable=True),
        sa.Column('order_comments', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED', 'CONVERTED', name='portaldrafts'), nullable=False),
        sa.Column('total_amount', sa.Numeric(18, 2), nullable=True),
        sa.Column('currency', sa.String(10), server_default='KES'),
        sa.Column('converted_order_id', sa.String(50), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('draft_no'),
    )

    op.create_table(
        'portal_draft_order_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('draft_order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('portal_draft_orders.id'), nullable=False),
        sa.Column('product_id', sa.String(50), nullable=True),
        sa.Column('product_name', sa.String(200), nullable=True),
        sa.Column('product_sku', sa.String(100), nullable=True),
        sa.Column('quantity', sa.Numeric(18, 3), nullable=False),
        sa.Column('unit', sa.String(20), server_default='PCS'),
        sa.Column('unit_price', sa.Numeric(14, 4), nullable=True),
        sa.Column('line_total', sa.Numeric(18, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'portal_ai_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_type', sa.Enum('SUPPORT_ASSISTANT', 'FRICTION_MONITOR', 'COMMERCIAL_OPPORTUNITY', name='portalaiagentt'), nullable=False),
        sa.Column('portal_account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('portal_accounts.id'), nullable=True),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('priority', sa.String(20), nullable=True),
        sa.Column('action_label', sa.String(100), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'ACKNOWLEDGED', 'ACTIONED', 'DISMISSED', name='portalairect'), nullable=True),
        sa.Column('acknowledged_by', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('portal_ai_recommendations')
    op.drop_table('portal_draft_order_lines')
    op.drop_table('portal_draft_orders')
    op.drop_table('portal_claims')
    op.drop_table('portal_activity_logs')
    op.drop_table('portal_users')
    op.drop_table('portal_accounts')
    op.execute("DROP TYPE IF EXISTS portalairect")
    op.execute("DROP TYPE IF EXISTS portalaiagentt")
    op.execute("DROP TYPE IF EXISTS portaldrafts")
    op.execute("DROP TYPE IF EXISTS portalclaims")
    op.execute("DROP TYPE IF EXISTS portalclaimt")
    op.execute("DROP TYPE IF EXISTS portalactivit")
    op.execute("DROP TYPE IF EXISTS portaluserro")
    op.execute("DROP TYPE IF EXISTS portalaccounts")
    op.execute("DROP TYPE IF EXISTS portalaccountt")
    op.execute("DROP TYPE IF EXISTS portalorderm")
