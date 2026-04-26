"""supplier_portal

Revision ID: b1c2d3e4f5a6
Revises: a9b0c1d2e3f4
Create Date: 2026-04-26 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b1c2d3e4f5a6'
down_revision = 'a9b0c1d2e3f4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sp_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('suppliers.id'), nullable=False, unique=True),
        sa.Column('portal_status', sa.String(30), nullable=False, server_default='PENDING'),
        sa.Column('default_currency', sa.String(10), nullable=False, server_default='KES'),
        sa.Column('preferred_language', sa.String(20), nullable=False, server_default='en'),
        sa.Column('allowed_modules_mask', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('primary_contact_name', sa.String(200), nullable=True),
        sa.Column('primary_contact_email', sa.String(200), nullable=True),
        sa.Column('primary_contact_phone', sa.String(50), nullable=True),
        sa.Column('timezone', sa.String(60), nullable=False, server_default='Africa/Nairobi'),
        sa.Column('can_view_prices', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('can_view_payment', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'sp_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sp_accounts.id'), nullable=False),
        sa.Column('full_name', sa.String(200), nullable=False),
        sa.Column('email', sa.String(200), nullable=False),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('login_identifier', sa.String(200), nullable=True),
        sa.Column('password_hash', sa.String(200), nullable=True),
        sa.Column('role_type', sa.String(30), nullable=False, server_default='VIEWER'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('invited_by', sa.String(200), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('email', name='uq_sp_user_email'),
    )

    op.create_table(
        'sp_permission_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('role_type', sa.String(30), nullable=False),
        sa.Column('can_view_po', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('can_acknowledge_po', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_propose_delivery', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_upload_invoice', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_upload_delivery_docs', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_upload_quality_docs', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_view_payment_status', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_manage_users', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_update_profile', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('role_type', name='uq_sp_perm_role'),
    )

    op.create_table(
        'sp_activity_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sp_accounts.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sp_users.id'), nullable=True),
        sa.Column('activity_type', sa.String(40), nullable=False),
        sa.Column('reference_type', sa.String(80), nullable=True),
        sa.Column('reference_id', sa.String(80), nullable=True),
        sa.Column('activity_datetime', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ip_or_session', sa.String(120), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
    )

    op.create_table(
        'sp_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sp_accounts.id'), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('suppliers.id'), nullable=False),
        sa.Column('upload_type', sa.String(40), nullable=False),
        sa.Column('linked_po_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('linked_grn_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('linked_invoice_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('file_name', sa.String(300), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('file_size_kb', sa.Integer(), nullable=True),
        sa.Column('uploaded_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sp_users.id'), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('review_status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('reviewed_by', sa.String(200), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'sp_po_responses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sp_accounts.id'), nullable=False),
        sa.Column('po_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('purchase_orders.id'), nullable=False),
        sa.Column('responded_by_user', postgresql.UUID(as_uuid=True), sa.ForeignKey('sp_users.id'), nullable=True),
        sa.Column('response_status', sa.String(40), nullable=False, server_default='PENDING_RESPONSE'),
        sa.Column('accepted_qty_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('supplier_comment', sa.Text(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('proposed_eta', sa.Date(), nullable=True),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('account_id', 'po_id', name='uq_sp_po_response'),
    )

    op.create_table(
        'sp_eta_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sp_accounts.id'), nullable=False),
        sa.Column('po_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('purchase_orders.id'), nullable=False),
        sa.Column('proposed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('sp_users.id'), nullable=True),
        sa.Column('original_date', sa.Date(), nullable=True),
        sa.Column('proposed_date', sa.Date(), nullable=False),
        sa.Column('eta_status', sa.String(20), nullable=False, server_default='REVISED'),
        sa.Column('revision_no', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('supplier_reason', sa.Text(), nullable=True),
        sa.Column('buyer_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.String(200), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'sp_ai_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sp_accounts.id'), nullable=True),
        sa.Column('agent_type', sa.String(40), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False, server_default='INFO'),
        sa.Column('reference_type', sa.String(80), nullable=True),
        sa.Column('reference_id', sa.String(80), nullable=True),
        sa.Column('actioned_by', sa.String(200), nullable=True),
        sa.Column('actioned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('sp_ai_recommendations')
    op.drop_table('sp_eta_logs')
    op.drop_table('sp_po_responses')
    op.drop_table('sp_documents')
    op.drop_table('sp_activity_logs')
    op.drop_table('sp_permission_profiles')
    op.drop_table('sp_users')
    op.drop_table('sp_accounts')
