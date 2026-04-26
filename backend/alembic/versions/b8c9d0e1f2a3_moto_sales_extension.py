"""moto_sales_mpesa_fraud_performance

Revision ID: b8c9d0e1f2a3
Revises: a6b7c8d9e0f1
Create Date: 2026-04-26 18:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b8c9d0e1f2a3'
down_revision = 'a6b7c8d9e0f1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'van_mpesa_payments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('txn_id', sa.UUID(), nullable=False),
        sa.Column('van_payment_id', sa.UUID(), nullable=True),
        sa.Column('phone_number', sa.String(20), nullable=False),
        sa.Column('amount', sa.Numeric(14, 2), nullable=False),
        sa.Column('merchant_request_id', sa.String(100), nullable=True),
        sa.Column('checkout_request_id', sa.String(100), nullable=True),
        sa.Column('mpesa_receipt_no', sa.String(50), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='PENDING'),
        sa.Column('result_code', sa.String(10), nullable=True),
        sa.Column('result_desc', sa.Text(), nullable=True),
        sa.Column('request_time', sa.DateTime(), nullable=False),
        sa.Column('callback_time', sa.DateTime(), nullable=True),
        sa.Column('raw_callback', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['txn_id'], ['van_sales_txns.id']),
        sa.ForeignKeyConstraint(['van_payment_id'], ['van_payments.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('merchant_request_id'),
        sa.UniqueConstraint('checkout_request_id'),
    )

    op.create_table(
        'van_fraud_alerts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('txn_id', sa.UUID(), nullable=True),
        sa.Column('van_id', sa.UUID(), nullable=True),
        sa.Column('driver_id', sa.UUID(), nullable=True),
        sa.Column('fraud_type', sa.String(50), nullable=False),
        sa.Column('risk_score', sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('severity', sa.String(20), nullable=False, server_default='LOW'),
        sa.Column('status', sa.String(30), nullable=False, server_default='OPEN'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('reviewed_by', sa.UUID(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['txn_id'], ['van_sales_txns.id']),
        sa.ForeignKeyConstraint(['van_id'], ['vans.id']),
        sa.ForeignKeyConstraint(['driver_id'], ['users.id']),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'van_rider_performance',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('driver_id', sa.UUID(), nullable=False),
        sa.Column('van_id', sa.UUID(), nullable=True),
        sa.Column('route_id', sa.UUID(), nullable=True),
        sa.Column('perf_date', sa.Date(), nullable=False),
        sa.Column('total_sales', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('total_orders', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_visits', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completed_visits', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('missed_visits', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('route_completion_pct', sa.Numeric(5, 2), nullable=True),
        sa.Column('collection_rate_pct', sa.Numeric(5, 2), nullable=True),
        sa.Column('expected_cash', sa.Numeric(14, 2), nullable=True),
        sa.Column('actual_cash', sa.Numeric(14, 2), nullable=True),
        sa.Column('cash_variance', sa.Numeric(14, 2), nullable=True),
        sa.Column('stock_variance_pct', sa.Numeric(7, 3), nullable=True),
        sa.Column('fraud_flag_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('performance_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['driver_id'], ['users.id']),
        sa.ForeignKeyConstraint(['van_id'], ['vans.id']),
        sa.ForeignKeyConstraint(['route_id'], ['sales_routes.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('driver_id', 'perf_date', name='uq_rider_perf_date'),
    )


def downgrade():
    op.drop_table('van_rider_performance')
    op.drop_table('van_fraud_alerts')
    op.drop_table('van_mpesa_payments')
