"""crm sales scope reconciliation

Revision ID: 20260515_0010
Revises: 20260514_0030
Create Date: 2026-05-15 07:08:00.000000

"""
from __future__ import annotations

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260515_0010"
down_revision = "20260514_0030"
branch_labels = None
depends_on = None


UUID = postgresql.UUID(as_uuid=True)


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    if context.is_offline_mode():
        return True
    return table_name in _inspector().get_table_names()


def _columns(table_name: str) -> set[str]:
    if not _has_table(table_name):
        return set()
    return {column["name"] for column in _inspector().get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    if not _has_table(table_name):
        return set()
    return {index["name"] for index in _inspector().get_indexes(table_name)}


def _foreign_keys(table_name: str) -> set[str]:
    if not _has_table(table_name):
        return set()
    return {fk["name"] for fk in _inspector().get_foreign_keys(table_name) if fk.get("name")}


def _add_column_once(table_name: str, column: sa.Column) -> None:
    if context.is_offline_mode() or (_has_table(table_name) and column.name not in _columns(table_name)):
        op.add_column(table_name, column)


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    if _has_table(table_name) and column_name in _columns(table_name):
        op.drop_column(table_name, column_name)


def _create_index_once(name: str, table_name: str, columns: list[str], **kwargs) -> None:
    if context.is_offline_mode() or (_has_table(table_name) and name not in _indexes(table_name)):
        op.create_index(name, table_name, columns, **kwargs)


def _drop_index_if_exists(name: str, table_name: str) -> None:
    if _has_table(table_name) and name in _indexes(table_name):
        op.drop_index(name, table_name=table_name)


def _create_fk_once(
    name: str,
    source_table: str,
    referent_table: str,
    local_cols: list[str],
    remote_cols: list[str],
    **kwargs,
) -> None:
    if context.is_offline_mode() or (_has_table(source_table) and name not in _foreign_keys(source_table)):
        op.create_foreign_key(name, source_table, referent_table, local_cols, remote_cols, **kwargs)


def _drop_fk_if_exists(name: str, table_name: str) -> None:
    if _has_table(table_name) and name in _foreign_keys(table_name):
        op.drop_constraint(name, table_name, type_="foreignkey")


def _create_crm_territories_if_missing() -> None:
    if _has_table("crm_territories") and not context.is_offline_mode():
        return
    op.create_table(
        "crm_territories",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("territory_code", sa.String(50), nullable=False),
        sa.Column("territory_name", sa.String(150), nullable=False),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("parent_territory_id", UUID, nullable=True),
        sa.Column("assigned_rep_ids", sa.String(500), nullable=True),
        sa.Column("active_flag", sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.UniqueConstraint("territory_code", name="uq_crm_territories_territory_code"),
    )


def _add_scope_columns(table_name: str) -> None:
    if not context.is_offline_mode() and not _has_table(table_name):
        return
    _add_column_once(table_name, sa.Column("company_id", UUID, nullable=True))
    _add_column_once(table_name, sa.Column("branch_id", UUID, nullable=True))
    _add_column_once(table_name, sa.Column("sales_region_id", sa.String(100), nullable=True))
    _add_column_once(table_name, sa.Column("sales_team_id", sa.String(100), nullable=True))
    _add_column_once(table_name, sa.Column("customer_group_id", sa.String(100), nullable=True))

    _create_fk_once(f"fk_{table_name}_company_id", table_name, "companies", ["company_id"], ["id"], ondelete="SET NULL")
    _create_fk_once(f"fk_{table_name}_branch_id", table_name, "branches", ["branch_id"], ["id"], ondelete="SET NULL")

    _create_index_once(f"ix_{table_name}_company_id", table_name, ["company_id"])
    _create_index_once(f"ix_{table_name}_branch_id", table_name, ["branch_id"])
    _create_index_once(f"ix_{table_name}_sales_region_id", table_name, ["sales_region_id"])
    _create_index_once(f"ix_{table_name}_sales_team_id", table_name, ["sales_team_id"])
    _create_index_once(f"ix_{table_name}_customer_group_id", table_name, ["customer_group_id"])


def _add_approval_columns(table_name: str) -> None:
    if not context.is_offline_mode() and not _has_table(table_name):
        return
    _add_column_once(table_name, sa.Column("approval_status", sa.String(50), nullable=True))
    _add_column_once(table_name, sa.Column("discount_approval_required", sa.Boolean(), nullable=False, server_default=sa.false()))
    _add_column_once(table_name, sa.Column("discount_approved_by_id", UUID, nullable=True))
    _add_column_once(table_name, sa.Column("discount_approved_at", sa.DateTime(timezone=True), nullable=True))

    _create_fk_once(
        f"fk_{table_name}_discount_approved_by_id",
        table_name,
        "users",
        ["discount_approved_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    _create_index_once(f"ix_{table_name}_approval_status", table_name, ["approval_status"])
    _create_index_once(f"ix_{table_name}_discount_approved_by_id", table_name, ["discount_approved_by_id"])


def upgrade() -> None:
    _create_crm_territories_if_missing()
    _add_scope_columns("crm_territories")
    _create_index_once("ix_crm_territories_region", "crm_territories", ["region"])
    _create_fk_once(
        "fk_crm_territories_parent_territory_id",
        "crm_territories",
        "crm_territories",
        ["parent_territory_id"],
        ["id"],
    )

    _add_scope_columns("customers")
    _add_scope_columns("sales_orders")
    _add_scope_columns("quotations")
    _add_scope_columns("crm_records")

    _add_approval_columns("sales_orders")
    _add_approval_columns("quotations")

    _add_column_once("crm_records", sa.Column("territory_id", UUID, nullable=True))
    _add_column_once("crm_records", sa.Column("assigned_customer_id", UUID, nullable=True))
    _create_fk_once("fk_crm_records_territory_id", "crm_records", "crm_territories", ["territory_id"], ["id"], ondelete="SET NULL")
    _create_fk_once("fk_crm_records_assigned_customer_id", "crm_records", "customers", ["assigned_customer_id"], ["id"], ondelete="SET NULL")
    _create_index_once("ix_crm_records_territory_id", "crm_records", ["territory_id"])
    _create_index_once("ix_crm_records_assigned_customer_id", "crm_records", ["assigned_customer_id"])

    _add_column_once("quotations", sa.Column("crm_record_id", UUID, nullable=True))
    _create_fk_once("fk_quotations_crm_record_id", "quotations", "crm_records", ["crm_record_id"], ["id"], ondelete="SET NULL")
    _create_index_once("ix_quotations_crm_record_id", "quotations", ["crm_record_id"])


def downgrade() -> None:
    for table_name in ("quotations", "sales_orders"):
        _drop_index_if_exists(f"ix_{table_name}_discount_approved_by_id", table_name)
        _drop_index_if_exists(f"ix_{table_name}_approval_status", table_name)
        _drop_fk_if_exists(f"fk_{table_name}_discount_approved_by_id", table_name)
        for column_name in ("discount_approved_at", "discount_approved_by_id", "discount_approval_required", "approval_status"):
            _drop_column_if_exists(table_name, column_name)

    _drop_index_if_exists("ix_quotations_crm_record_id", "quotations")
    _drop_fk_if_exists("fk_quotations_crm_record_id", "quotations")
    _drop_column_if_exists("quotations", "crm_record_id")

    _drop_index_if_exists("ix_crm_records_assigned_customer_id", "crm_records")
    _drop_index_if_exists("ix_crm_records_territory_id", "crm_records")
    _drop_fk_if_exists("fk_crm_records_assigned_customer_id", "crm_records")
    _drop_fk_if_exists("fk_crm_records_territory_id", "crm_records")
    _drop_column_if_exists("crm_records", "assigned_customer_id")
    _drop_column_if_exists("crm_records", "territory_id")

    for table_name in ("crm_records", "quotations", "sales_orders", "customers", "crm_territories"):
        for index_name in (
            f"ix_{table_name}_customer_group_id",
            f"ix_{table_name}_sales_team_id",
            f"ix_{table_name}_sales_region_id",
            f"ix_{table_name}_branch_id",
            f"ix_{table_name}_company_id",
        ):
            _drop_index_if_exists(index_name, table_name)
        _drop_fk_if_exists(f"fk_{table_name}_branch_id", table_name)
        _drop_fk_if_exists(f"fk_{table_name}_company_id", table_name)
        for column_name in ("customer_group_id", "sales_team_id", "sales_region_id", "branch_id", "company_id"):
            _drop_column_if_exists(table_name, column_name)

    _drop_index_if_exists("ix_crm_territories_region", "crm_territories")
    _drop_fk_if_exists("fk_crm_territories_parent_territory_id", "crm_territories")
