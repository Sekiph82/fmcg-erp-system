"""operational posting integration foundations

Revision ID: 20260511_0020
Revises: 20260511_0010
Create Date: 2026-05-11 11:05:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260511_0020"
down_revision = "20260511_0010"
branch_labels = None
depends_on = None


OPERATIONAL_POSTING_STATUS = "operational_posting_status"


def _create_enum(enum_name: str, values: tuple[str, ...]) -> None:
    quoted_values = ", ".join(f"'{value}'" for value in values)
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{enum_name}') THEN
                    CREATE TYPE {enum_name} AS ENUM ({quoted_values});
                END IF;
            END
            $$;
            """
        )
    )


def _drop_enum(enum_name: str) -> None:
    op.execute(sa.text(f"DROP TYPE IF EXISTS {enum_name};"))


def _add_posting_link_columns(table_name: str) -> None:
    posting_status = postgresql.ENUM(
        "PENDING", "POSTED", "FAILED", "REVERSED", "NOT_REQUIRED",
        name=OPERATIONAL_POSTING_STATUS,
        create_type=False,
    )
    op.add_column(table_name, sa.Column("posting_batch_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(table_name, sa.Column("journal_entry_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(table_name, sa.Column("accounting_status", posting_status, nullable=True))
    op.add_column(table_name, sa.Column("posting_error", sa.Text(), nullable=True))
    op.create_foreign_key(
        f"fk_{table_name}_posting_batch_id",
        table_name,
        "accounting_posting_batches",
        ["posting_batch_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        f"fk_{table_name}_journal_entry_id",
        table_name,
        "journal_entries",
        ["journal_entry_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(f"ix_{table_name}_posting_batch_id", table_name, ["posting_batch_id"])
    op.create_index(f"ix_{table_name}_journal_entry_id", table_name, ["journal_entry_id"])
    op.create_index(f"ix_{table_name}_accounting_status", table_name, ["accounting_status"])


def _drop_posting_link_columns(table_name: str) -> None:
    op.drop_index(f"ix_{table_name}_accounting_status", table_name=table_name)
    op.drop_index(f"ix_{table_name}_journal_entry_id", table_name=table_name)
    op.drop_index(f"ix_{table_name}_posting_batch_id", table_name=table_name)
    op.drop_constraint(f"fk_{table_name}_journal_entry_id", table_name, type_="foreignkey")
    op.drop_constraint(f"fk_{table_name}_posting_batch_id", table_name, type_="foreignkey")
    op.drop_column(table_name, "posting_error")
    op.drop_column(table_name, "accounting_status")
    op.drop_column(table_name, "journal_entry_id")
    op.drop_column(table_name, "posting_batch_id")


def upgrade() -> None:
    _create_enum(OPERATIONAL_POSTING_STATUS, ("PENDING", "POSTED", "FAILED", "REVERSED", "NOT_REQUIRED"))
    posting_status = postgresql.ENUM(
        "PENDING", "POSTED", "FAILED", "REVERSED", "NOT_REQUIRED",
        name=OPERATIONAL_POSTING_STATUS,
        create_type=False,
    )

    op.create_table(
        "operational_posting_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_module", sa.String(80), nullable=False),
        sa.Column("source_event", sa.String(80), nullable=False),
        sa.Column("source_id", sa.String(80), nullable=False),
        sa.Column("source_line_id", sa.String(80), nullable=True),
        sa.Column("stock_movement_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("posting_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("journal_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", posting_status, nullable=False, server_default="PENDING"),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("idempotency_key", sa.String(220), nullable=False),
        sa.Column("reversal_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["stock_movement_id"], ["stock_movements.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["posting_batch_id"], ["accounting_posting_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["journal_entries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reversal_event_id"], ["operational_posting_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_operational_posting_events_idempotency_key"),
    )
    op.create_index(
        "ix_operational_posting_events_source",
        "operational_posting_events",
        ["source_module", "source_event", "source_id"],
    )
    op.create_index(
        "ix_operational_posting_events_source_line",
        "operational_posting_events",
        ["source_module", "source_event", "source_line_id"],
    )
    op.create_index("ix_operational_posting_events_status", "operational_posting_events", ["status"])
    op.create_index("ix_operational_posting_events_event_date", "operational_posting_events", ["event_date"])
    op.create_index(
        "ix_operational_posting_events_stock_movement_id",
        "operational_posting_events",
        ["stock_movement_id"],
    )
    op.create_index(
        "ix_operational_posting_events_posting_batch_id",
        "operational_posting_events",
        ["posting_batch_id"],
    )
    op.create_index(
        "ix_operational_posting_events_journal_entry_id",
        "operational_posting_events",
        ["journal_entry_id"],
    )

    op.create_table(
        "inventory_account_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stock_type", sa.String(40), nullable=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category_key", sa.String(120), nullable=True),
        sa.Column("valuation_method", sa.String(40), nullable=True),
        sa.Column("inventory_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("wip_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("finished_goods_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cogs_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("grni_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("landed_cost_clearing_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("variance_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scrap_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "product_id IS NOT NULL OR material_id IS NOT NULL OR stock_type IS NOT NULL OR category_key IS NOT NULL",
            name="ck_inventory_account_mappings_scope",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inventory_account_id"], ["chart_of_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["wip_account_id"], ["chart_of_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["finished_goods_account_id"], ["chart_of_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["cogs_account_id"], ["chart_of_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["grni_account_id"], ["chart_of_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["landed_cost_clearing_account_id"], ["chart_of_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["variance_account_id"], ["chart_of_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["scrap_account_id"], ["chart_of_accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_inventory_account_mappings_lookup",
        "inventory_account_mappings",
        ["is_active", "priority", "stock_type", "product_id", "material_id", "category_key"],
    )
    op.create_index("ix_inventory_account_mappings_product_id", "inventory_account_mappings", ["product_id"])
    op.create_index("ix_inventory_account_mappings_material_id", "inventory_account_mappings", ["material_id"])

    _add_posting_link_columns("grn_lines")
    _add_posting_link_columns("material_consumptions")
    _add_posting_link_columns("finished_goods_receipts")
    _add_posting_link_columns("lc_allocation_lines")
    _add_posting_link_columns("lc_inventory_adjustments")

    op.add_column("stock_movements", sa.Column("posting_batch_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("stock_movements", sa.Column("journal_entry_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("stock_movements", sa.Column("accounting_status", posting_status, nullable=True))
    op.add_column("stock_movements", sa.Column("valuation_method", sa.String(40), nullable=True))
    op.add_column("stock_movements", sa.Column("valuation_amount", sa.Numeric(18, 4), nullable=True))
    op.add_column("stock_movements", sa.Column("valuation_currency", sa.String(10), nullable=True))
    op.add_column("stock_movements", sa.Column("posting_error", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_stock_movements_posting_batch_id",
        "stock_movements",
        "accounting_posting_batches",
        ["posting_batch_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_stock_movements_journal_entry_id",
        "stock_movements",
        "journal_entries",
        ["journal_entry_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_stock_movements_posting_batch_id", "stock_movements", ["posting_batch_id"])
    op.create_index("ix_stock_movements_journal_entry_id", "stock_movements", ["journal_entry_id"])
    op.create_index("ix_stock_movements_accounting_status", "stock_movements", ["accounting_status"])
    op.create_index(
        "ix_stock_movements_accounting_scan",
        "stock_movements",
        ["movement_date", "stock_type", "movement_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_stock_movements_accounting_scan", table_name="stock_movements")
    op.drop_index("ix_stock_movements_accounting_status", table_name="stock_movements")
    op.drop_index("ix_stock_movements_journal_entry_id", table_name="stock_movements")
    op.drop_index("ix_stock_movements_posting_batch_id", table_name="stock_movements")
    op.drop_constraint("fk_stock_movements_journal_entry_id", "stock_movements", type_="foreignkey")
    op.drop_constraint("fk_stock_movements_posting_batch_id", "stock_movements", type_="foreignkey")
    op.drop_column("stock_movements", "posting_error")
    op.drop_column("stock_movements", "valuation_currency")
    op.drop_column("stock_movements", "valuation_amount")
    op.drop_column("stock_movements", "valuation_method")
    op.drop_column("stock_movements", "accounting_status")
    op.drop_column("stock_movements", "journal_entry_id")
    op.drop_column("stock_movements", "posting_batch_id")

    _drop_posting_link_columns("lc_inventory_adjustments")
    _drop_posting_link_columns("lc_allocation_lines")
    _drop_posting_link_columns("finished_goods_receipts")
    _drop_posting_link_columns("material_consumptions")
    _drop_posting_link_columns("grn_lines")

    op.drop_index("ix_inventory_account_mappings_material_id", table_name="inventory_account_mappings")
    op.drop_index("ix_inventory_account_mappings_product_id", table_name="inventory_account_mappings")
    op.drop_index("ix_inventory_account_mappings_lookup", table_name="inventory_account_mappings")
    op.drop_table("inventory_account_mappings")

    op.drop_index("ix_operational_posting_events_journal_entry_id", table_name="operational_posting_events")
    op.drop_index("ix_operational_posting_events_posting_batch_id", table_name="operational_posting_events")
    op.drop_index("ix_operational_posting_events_stock_movement_id", table_name="operational_posting_events")
    op.drop_index("ix_operational_posting_events_event_date", table_name="operational_posting_events")
    op.drop_index("ix_operational_posting_events_status", table_name="operational_posting_events")
    op.drop_index("ix_operational_posting_events_source_line", table_name="operational_posting_events")
    op.drop_index("ix_operational_posting_events_source", table_name="operational_posting_events")
    op.drop_table("operational_posting_events")

    _drop_enum(OPERATIONAL_POSTING_STATUS)
