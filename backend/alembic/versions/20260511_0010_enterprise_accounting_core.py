"""enterprise accounting core foundations

Revision ID: 20260511_0010
Revises: 20260510_0710
Create Date: 2026-05-11 04:12:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260511_0010"
down_revision = "20260510_0710"
branch_labels = None
depends_on = None


FISCAL_YEAR_STATUS = "finance_fiscal_year_status"
JOURNAL_STATUS = "finance_journal_status"
RECURRING_JOURNAL_FREQUENCY = "finance_recurring_journal_frequency"
RECURRING_JOURNAL_STATUS = "finance_recurring_journal_status"
POSTING_BATCH_STATUS = "finance_posting_batch_status"
PAYMENT_ALLOCATION_PARTY_TYPE = "finance_payment_allocation_party_type"
CURRENCY_REVALUATION_STATUS = "finance_currency_revaluation_status"
ACCOUNTING_CLOSE_CHECK_STATUS = "finance_accounting_close_check_status"


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


def upgrade() -> None:
    _create_enum(FISCAL_YEAR_STATUS, ("OPEN", "CLOSING", "CLOSED", "LOCKED"))
    _create_enum(JOURNAL_STATUS, ("DRAFT", "POSTED", "REVERSED", "VOID"))
    _create_enum(RECURRING_JOURNAL_FREQUENCY, ("MONTHLY", "QUARTERLY", "ANNUALLY", "CUSTOM"))
    _create_enum(RECURRING_JOURNAL_STATUS, ("ACTIVE", "PAUSED", "CLOSED"))
    _create_enum(POSTING_BATCH_STATUS, ("DRAFT", "POSTED", "FAILED", "REVERSED"))
    _create_enum(PAYMENT_ALLOCATION_PARTY_TYPE, ("CUSTOMER", "SUPPLIER"))
    _create_enum(CURRENCY_REVALUATION_STATUS, ("DRAFT", "POSTED", "REVERSED"))
    _create_enum(ACCOUNTING_CLOSE_CHECK_STATUS, ("PENDING", "PASSED", "FAILED", "WAIVED"))

    fiscal_year_status = postgresql.ENUM(
        "OPEN", "CLOSING", "CLOSED", "LOCKED", name=FISCAL_YEAR_STATUS, create_type=False
    )
    journal_status = postgresql.ENUM(
        "DRAFT", "POSTED", "REVERSED", "VOID", name=JOURNAL_STATUS, create_type=False
    )
    recurring_frequency = postgresql.ENUM(
        "MONTHLY", "QUARTERLY", "ANNUALLY", "CUSTOM", name=RECURRING_JOURNAL_FREQUENCY, create_type=False
    )
    recurring_status = postgresql.ENUM(
        "ACTIVE", "PAUSED", "CLOSED", name=RECURRING_JOURNAL_STATUS, create_type=False
    )
    posting_batch_status = postgresql.ENUM(
        "DRAFT", "POSTED", "FAILED", "REVERSED", name=POSTING_BATCH_STATUS, create_type=False
    )
    allocation_party_type = postgresql.ENUM(
        "CUSTOMER", "SUPPLIER", name=PAYMENT_ALLOCATION_PARTY_TYPE, create_type=False
    )
    revaluation_status = postgresql.ENUM(
        "DRAFT", "POSTED", "REVERSED", name=CURRENCY_REVALUATION_STATUS, create_type=False
    )
    close_check_status = postgresql.ENUM(
        "PENDING", "PASSED", "FAILED", "WAIVED", name=ACCOUNTING_CLOSE_CHECK_STATUS, create_type=False
    )

    op.create_table(
        "fiscal_years",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("year_code", sa.String(20), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", fiscal_year_status, nullable=False, server_default="OPEN"),
        sa.Column("base_currency", sa.String(10), nullable=False, server_default="KES"),
        sa.Column("retained_earnings_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("closed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("start_date <= end_date", name="ck_fiscal_years_date_range"),
        sa.ForeignKeyConstraint(["retained_earnings_account_id"], ["chart_of_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["closed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["locked_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("year_code", name="uq_fiscal_years_year_code"),
    )
    op.create_index("ix_fiscal_years_year_code", "fiscal_years", ["year_code"])

    op.add_column("accounting_periods", sa.Column("fiscal_year_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("accounting_periods", sa.Column("period_start", sa.Date(), nullable=True))
    op.add_column("accounting_periods", sa.Column("period_end", sa.Date(), nullable=True))
    op.add_column("accounting_periods", sa.Column("close_notes", sa.Text(), nullable=True))
    op.add_column("accounting_periods", sa.Column("locked_by_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("accounting_periods", sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_accounting_periods_fiscal_year_id",
        "accounting_periods",
        "fiscal_years",
        ["fiscal_year_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_accounting_periods_locked_by_id",
        "accounting_periods",
        "users",
        ["locked_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_accounting_periods_fiscal_year_dates",
        "accounting_periods",
        ["fiscal_year_id", "period_start", "period_end"],
    )

    op.create_table(
        "accounting_period_close_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("check_code", sa.String(80), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("status", close_check_status, nullable=False, server_default="PENDING"),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("checked_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["period_id"], ["accounting_periods.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["checked_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("period_id", "check_code", name="uq_accounting_period_close_check"),
    )

    op.create_table(
        "recurring_journal_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_no", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("frequency", recurring_frequency, nullable=False),
        sa.Column("status", recurring_status, nullable=False, server_default="ACTIVE"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("next_run_date", sa.Date(), nullable=False),
        sa.Column("last_run_date", sa.Date(), nullable=True),
        sa.Column("default_memo", sa.String(255), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("end_date IS NULL OR start_date <= end_date", name="ck_recurring_journals_date_range"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_no", name="uq_recurring_journal_templates_template_no"),
    )
    op.create_index("ix_recurring_journal_templates_next_run", "recurring_journal_templates", ["status", "next_run_date"])

    op.create_table(
        "recurring_journal_template_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("debit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("credit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("cost_center_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("debit >= 0 AND credit >= 0", name="ck_recurring_journal_lines_non_negative"),
        sa.CheckConstraint("NOT (debit > 0 AND credit > 0)", name="ck_recurring_journal_lines_single_side"),
        sa.ForeignKeyConstraint(["template_id"], ["recurring_journal_templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["chart_of_accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cost_center_id"], ["cost_centers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "accounting_posting_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_module", sa.String(80), nullable=False),
        sa.Column("source_event", sa.String(80), nullable=False),
        sa.Column("source_id", sa.String(80), nullable=False),
        sa.Column("source_ref", sa.String(120), nullable=True),
        sa.Column("status", posting_batch_status, nullable=False, server_default="DRAFT"),
        sa.Column("journal_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("posted_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["journal_entries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["posted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_accounting_posting_batches_idempotency_key"),
        sa.UniqueConstraint("source_module", "source_event", "source_id", name="uq_accounting_posting_batches_source"),
    )

    op.create_table(
        "accounting_posting_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_module", sa.String(80), nullable=False),
        sa.Column("source_event", sa.String(80), nullable=False),
        sa.Column("rule_name", sa.String(160), nullable=False),
        sa.Column("debit_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("credit_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tax_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("clearing_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["debit_account_id"], ["chart_of_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["credit_account_id"], ["chart_of_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tax_account_id"], ["chart_of_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["clearing_account_id"], ["chart_of_accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_accounting_posting_rules_source",
        "accounting_posting_rules",
        ["source_module", "source_event", "is_active", "priority"],
    )

    op.add_column("journal_entries", sa.Column("status", journal_status, nullable=True))
    op.add_column("journal_entries", sa.Column("source_event", sa.String(80), nullable=True))
    op.add_column("journal_entries", sa.Column("reversal_of_entry_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("journal_entries", sa.Column("reversed_by_entry_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("journal_entries", sa.Column("posting_batch_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("journal_entries", sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        """
        UPDATE journal_entries
        SET status = CASE WHEN is_posted THEN 'POSTED'::finance_journal_status ELSE 'DRAFT'::finance_journal_status END
        WHERE status IS NULL;
        """
    )
    op.alter_column("journal_entries", "status", nullable=False, server_default="DRAFT")
    op.create_foreign_key(
        "fk_journal_entries_reversal_of_entry_id",
        "journal_entries",
        "journal_entries",
        ["reversal_of_entry_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_journal_entries_reversed_by_entry_id",
        "journal_entries",
        "journal_entries",
        ["reversed_by_entry_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_journal_entries_posting_batch_id",
        "journal_entries",
        "accounting_posting_batches",
        ["posting_batch_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_journal_entries_status_date", "journal_entries", ["status", "entry_date"])
    op.create_index(
        "ix_journal_entries_source",
        "journal_entries",
        ["source_module", "source_event", "source_id"],
    )

    op.create_table(
        "payment_allocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("party_type", allocation_party_type, nullable=False),
        sa.Column("customer_payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("supplier_payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sales_invoice_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("purchase_invoice_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("allocated_amount", sa.Numeric(16, 4), nullable=False),
        sa.Column("allocation_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("allocated_amount > 0", name="ck_payment_allocations_positive_amount"),
        sa.CheckConstraint(
            """
            (
                party_type = 'CUSTOMER'
                AND customer_payment_id IS NOT NULL
                AND sales_invoice_id IS NOT NULL
                AND supplier_payment_id IS NULL
                AND purchase_invoice_id IS NULL
            )
            OR
            (
                party_type = 'SUPPLIER'
                AND supplier_payment_id IS NOT NULL
                AND purchase_invoice_id IS NOT NULL
                AND customer_payment_id IS NULL
                AND sales_invoice_id IS NULL
            )
            """,
            name="ck_payment_allocations_party_refs",
        ),
        sa.ForeignKeyConstraint(["customer_payment_id"], ["payments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supplier_payment_id"], ["purchase_payments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sales_invoice_id"], ["invoices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["purchase_invoice_id"], ["purchase_invoices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payment_allocations_party_date", "payment_allocations", ["party_type", "allocation_date"])

    op.create_table(
        "currency_revaluation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_no", sa.String(50), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("rate_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", revaluation_status, nullable=False, server_default="DRAFT"),
        sa.Column("journal_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("unrealized_gain_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("unrealized_loss_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("posted_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["rate_id"], ["exchange_rates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["journal_entries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["unrealized_gain_account_id"], ["chart_of_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["unrealized_loss_account_id"], ["chart_of_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["posted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_no", name="uq_currency_revaluation_runs_run_no"),
    )
    op.create_index(
        "ix_currency_revaluation_runs_date_currency_status",
        "currency_revaluation_runs",
        ["as_of_date", "currency", "status"],
    )

    op.create_table(
        "currency_revaluation_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("foreign_currency_balance", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("book_base_balance", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("revalued_base_balance", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("gain_loss_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["currency_revaluation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["chart_of_accounts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("currency_revaluation_lines")
    op.drop_index("ix_currency_revaluation_runs_date_currency_status", table_name="currency_revaluation_runs")
    op.drop_table("currency_revaluation_runs")

    op.drop_index("ix_payment_allocations_party_date", table_name="payment_allocations")
    op.drop_table("payment_allocations")

    op.drop_index("ix_journal_entries_source", table_name="journal_entries")
    op.drop_index("ix_journal_entries_status_date", table_name="journal_entries")
    op.drop_constraint("fk_journal_entries_posting_batch_id", "journal_entries", type_="foreignkey")
    op.drop_constraint("fk_journal_entries_reversed_by_entry_id", "journal_entries", type_="foreignkey")
    op.drop_constraint("fk_journal_entries_reversal_of_entry_id", "journal_entries", type_="foreignkey")
    op.drop_column("journal_entries", "locked_at")
    op.drop_column("journal_entries", "posting_batch_id")
    op.drop_column("journal_entries", "reversed_by_entry_id")
    op.drop_column("journal_entries", "reversal_of_entry_id")
    op.drop_column("journal_entries", "source_event")
    op.drop_column("journal_entries", "status")

    op.drop_index("ix_accounting_posting_rules_source", table_name="accounting_posting_rules")
    op.drop_table("accounting_posting_rules")
    op.drop_table("accounting_posting_batches")
    op.drop_table("recurring_journal_template_lines")
    op.drop_index("ix_recurring_journal_templates_next_run", table_name="recurring_journal_templates")
    op.drop_table("recurring_journal_templates")
    op.drop_table("accounting_period_close_checks")

    op.drop_index("ix_accounting_periods_fiscal_year_dates", table_name="accounting_periods")
    op.drop_constraint("fk_accounting_periods_locked_by_id", "accounting_periods", type_="foreignkey")
    op.drop_constraint("fk_accounting_periods_fiscal_year_id", "accounting_periods", type_="foreignkey")
    op.drop_column("accounting_periods", "locked_at")
    op.drop_column("accounting_periods", "locked_by_id")
    op.drop_column("accounting_periods", "close_notes")
    op.drop_column("accounting_periods", "period_end")
    op.drop_column("accounting_periods", "period_start")
    op.drop_column("accounting_periods", "fiscal_year_id")

    op.drop_index("ix_fiscal_years_year_code", table_name="fiscal_years")
    op.drop_table("fiscal_years")

    _drop_enum(ACCOUNTING_CLOSE_CHECK_STATUS)
    _drop_enum(CURRENCY_REVALUATION_STATUS)
    _drop_enum(PAYMENT_ALLOCATION_PARTY_TYPE)
    _drop_enum(POSTING_BATCH_STATUS)
    _drop_enum(RECURRING_JOURNAL_STATUS)
    _drop_enum(RECURRING_JOURNAL_FREQUENCY)
    _drop_enum(JOURNAL_STATUS)
    _drop_enum(FISCAL_YEAR_STATUS)
