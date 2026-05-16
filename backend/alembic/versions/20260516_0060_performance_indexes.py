"""Add performance indexes for FK/date/status fields

Revision ID: 20260516_0060
Revises: 20260516_0050
Create Date: 2026-05-16
"""
from __future__ import annotations

from alembic import op

revision = "20260516_0060"
down_revision = "20260516_0050"
branch_labels = None
depends_on = None

# (table, column, index_name)
_INDEXES = [
    # Chart of Accounts
    ("chart_of_accounts", "parent_id", "ix_coa_parent_id"),
    # Journal lines
    ("journal_lines", "entry_id", "ix_journal_lines_entry_id"),
    ("journal_lines", "account_id", "ix_journal_lines_account_id"),
    # Journal entries
    ("journal_entries", "entry_date", "ix_journal_entries_entry_date"),
    ("journal_entries", "is_posted", "ix_journal_entries_is_posted"),
    ("journal_entries", "source_module", "ix_journal_entries_source_module"),
    # Cash transactions
    ("cash_transactions", "cash_account_id", "ix_cash_tx_account_id"),
    ("cash_transactions", "transaction_date", "ix_cash_tx_date"),
    ("cash_transactions", "status", "ix_cash_tx_status"),
    ("cash_transactions", "direction", "ix_cash_tx_direction"),
    # Product costs
    ("product_costs", "product_id", "ix_product_costs_product_id"),
    ("product_costs", "period_ym", "ix_product_costs_period_ym"),
    # Production cost entries
    ("production_cost_entries", "product_id", "ix_prod_cost_entries_product_id"),
    ("production_cost_entries", "production_order_id", "ix_prod_cost_entries_order_id"),
    ("production_cost_entries", "period_ym", "ix_prod_cost_entries_period_ym"),
    # Budgets
    ("budgets", "year", "ix_budgets_year"),
    ("budgets", "status", "ix_budgets_status"),
    # Stock movements
    ("stock_movements", "product_id", "ix_stock_mov_product_id"),
    ("stock_movements", "warehouse_id", "ix_stock_mov_warehouse_id"),
    ("stock_movements", "movement_date", "ix_stock_mov_date"),
    # Inventory lots
    ("lots", "product_id", "ix_lots_product_id"),
    ("lots", "warehouse_id", "ix_lots_warehouse_id"),
    # Sales orders
    ("sales_orders", "customer_id", "ix_so_customer_id"),
    ("sales_orders", "status", "ix_so_status"),
    ("sales_orders", "order_date", "ix_so_order_date"),
    # Purchase orders
    ("purchase_orders", "supplier_id", "ix_po_supplier_id"),
    ("purchase_orders", "status", "ix_po_status"),
    ("purchase_orders", "order_date", "ix_po_order_date"),
    # Production orders
    ("production_orders", "product_id", "ix_prod_orders_product_id"),
    ("production_orders", "status", "ix_prod_orders_status"),
    ("production_orders", "planned_start", "ix_prod_orders_planned_start"),
    # Audit logs
    ("audit_logs", "user_id", "ix_audit_logs_user_id"),
    ("audit_logs", "resource_type", "ix_audit_logs_resource_type"),
    ("audit_logs", "created_at", "ix_audit_logs_created_at"),
]


def upgrade() -> None:
    conn = op.get_bind()
    for table, column, idx_name in _INDEXES:
        # Check table exists before creating index (migrations are additive)
        exists = conn.execute(
            __import__("sqlalchemy", fromlist=["text"]).text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name=:t"
            ),
            {"t": table},
        ).fetchone()
        if not exists:
            continue
        col_exists = conn.execute(
            __import__("sqlalchemy", fromlist=["text"]).text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=:t AND column_name=:c"
            ),
            {"t": table, "c": column},
        ).fetchone()
        if not col_exists:
            continue
        idx_exists = conn.execute(
            __import__("sqlalchemy", fromlist=["text"]).text(
                "SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname=:i"
            ),
            {"i": idx_name},
        ).fetchone()
        if not idx_exists:
            op.create_index(idx_name, table, [column])


def downgrade() -> None:
    for _table, _column, idx_name in _INDEXES:
        try:
            op.drop_index(idx_name)
        except Exception:
            pass
