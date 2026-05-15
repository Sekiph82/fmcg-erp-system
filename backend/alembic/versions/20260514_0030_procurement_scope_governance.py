"""Add procurement scope and supplier governance reconciliation.

Revision ID: 20260514_0030
Revises: 20260514_0020
Create Date: 2026-05-14 23:20:00.000000
"""
from __future__ import annotations

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "20260514_0030"
down_revision = "20260514_0020"
branch_labels = None
depends_on = None


UUID = postgresql.UUID(as_uuid=True)


PROCUREMENT_SCOPE_TABLES = (
    "purchase_requisitions",
    "purchase_orders",
    "goods_receipts",
    "import_shipments",
    "rfq_requests",
    "blanket_purchase_agreements",
    "auto_reorder_policies",
    "supplier_payments",
    "supplier_evaluations",
)


def _has_table(table_name: str) -> bool:
    if context.is_offline_mode():
        return False
    return inspect(op.get_bind()).has_table(table_name)


def _columns(table_name: str) -> set[str]:
    if context.is_offline_mode():
        return set()
    if not _has_table(table_name):
        return set()
    return {col["name"] for col in inspect(op.get_bind()).get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    if context.is_offline_mode():
        return set()
    if not _has_table(table_name):
        return set()
    return {idx["name"] for idx in inspect(op.get_bind()).get_indexes(table_name)}


def _foreign_keys(table_name: str) -> set[str]:
    if context.is_offline_mode():
        return set()
    if not _has_table(table_name):
        return set()
    return {fk["name"] for fk in inspect(op.get_bind()).get_foreign_keys(table_name) if fk.get("name")}


def _add_column_once(table_name: str, column: sa.Column) -> None:
    if context.is_offline_mode() or (_has_table(table_name) and column.name not in _columns(table_name)):
        op.add_column(table_name, column)


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


def _drop_constraint_if_exists(name: str, table_name: str, constraint_type: str = "foreignkey") -> None:
    if _has_table(table_name) and name in _foreign_keys(table_name):
        op.drop_constraint(name, table_name, type_=constraint_type)


def _create_enum(name: str, *values: str) -> None:
    enum = postgresql.ENUM(*values, name=name)
    enum.create(op.get_bind(), checkfirst=True)


def _drop_enum(name: str) -> None:
    op.execute(f"DROP TYPE IF EXISTS {name}")


def _scope_columns() -> list[sa.Column]:
    return [
        sa.Column("company_id", UUID, nullable=True),
        sa.Column("branch_id", UUID, nullable=True),
        sa.Column("cost_center_id", UUID, nullable=True),
        sa.Column("department", sa.String(100), nullable=True),
    ]


def _add_procurement_scope(table_name: str) -> None:
    if not context.is_offline_mode() and not _has_table(table_name):
        return

    for column in _scope_columns():
        _add_column_once(table_name, column)

    _create_fk_once(f"fk_{table_name}_company_id", table_name, "companies", ["company_id"], ["id"], ondelete="SET NULL")
    _create_fk_once(f"fk_{table_name}_branch_id", table_name, "branches", ["branch_id"], ["id"], ondelete="SET NULL")
    _create_fk_once(
        f"fk_{table_name}_cost_center_id",
        table_name,
        "cost_centers",
        ["cost_center_id"],
        ["id"],
        ondelete="SET NULL",
    )
    _create_index_once(f"ix_{table_name}_company_id", table_name, ["company_id"])
    _create_index_once(f"ix_{table_name}_branch_id", table_name, ["branch_id"])
    _create_index_once(f"ix_{table_name}_cost_center_id", table_name, ["cost_center_id"])
    _create_index_once(f"ix_{table_name}_department", table_name, ["department"])


def upgrade() -> None:
    _create_enum("supplier_qualification_status", "PENDING", "APPROVED", "CONDITIONAL", "SUSPENDED", "REJECTED")
    _create_enum("supplier_risk_level", "LOW", "MEDIUM", "HIGH", "CRITICAL")
    _create_enum("procurement_approval_document_type", "PR", "PO", "RFQ", "BPA")

    if context.is_offline_mode() or _has_table("suppliers"):
        _add_column_once("suppliers", sa.Column("supplier_category", sa.String(100), nullable=True))
        _add_column_once(
            "suppliers",
            sa.Column(
                "qualification_status",
                postgresql.ENUM(
                    "PENDING",
                    "APPROVED",
                    "CONDITIONAL",
                    "SUSPENDED",
                    "REJECTED",
                    name="supplier_qualification_status",
                    create_type=False,
                ),
                nullable=True,
            ),
        )
        _add_column_once(
            "suppliers",
            sa.Column(
                "risk_level",
                postgresql.ENUM("LOW", "MEDIUM", "HIGH", "CRITICAL", name="supplier_risk_level", create_type=False),
                nullable=True,
            ),
        )
        _add_column_once("suppliers", sa.Column("approved_from", sa.Date(), nullable=True))
        _add_column_once("suppliers", sa.Column("approved_until", sa.Date(), nullable=True))
        _add_column_once("suppliers", sa.Column("approved_by_id", UUID, nullable=True))
        _add_column_once("suppliers", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
        _create_fk_once("fk_suppliers_approved_by_id", "suppliers", "users", ["approved_by_id"], ["id"], ondelete="SET NULL")
        _create_index_once("ix_suppliers_supplier_category", "suppliers", ["supplier_category"])
        _create_index_once("ix_suppliers_qualification_status", "suppliers", ["qualification_status"])
        _create_index_once("ix_suppliers_risk_level", "suppliers", ["risk_level"])

    for table_name in PROCUREMENT_SCOPE_TABLES:
        _add_procurement_scope(table_name)

    if not _has_table("procurement_approval_rules"):
        op.create_table(
            "procurement_approval_rules",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("rule_name", sa.String(255), nullable=False),
            sa.Column(
                "document_type",
                postgresql.ENUM("PR", "PO", "RFQ", "BPA", name="procurement_approval_document_type", create_type=False),
                nullable=False,
            ),
            sa.Column("company_id", UUID, nullable=True),
            sa.Column("branch_id", UUID, nullable=True),
            sa.Column("cost_center_id", UUID, nullable=True),
            sa.Column("department", sa.String(100), nullable=True),
            sa.Column("supplier_category", sa.String(100), nullable=True),
            sa.Column("product_category", sa.String(100), nullable=True),
            sa.Column("min_amount", sa.Numeric(16, 4), nullable=True),
            sa.Column("max_amount", sa.Numeric(16, 4), nullable=True),
            sa.Column("currency", sa.String(10), nullable=True),
            sa.Column("approval_level", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("approver_user_id", UUID, nullable=True),
            sa.Column("approver_role_id", UUID, nullable=True),
            sa.Column("requires_all_matching_approvers", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("effective_from", sa.Date(), nullable=True),
            sa.Column("effective_to", sa.Date(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["cost_center_id"], ["cost_centers.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["approver_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["approver_role_id"], ["roles.id"], ondelete="SET NULL"),
            sa.CheckConstraint(
                "approver_user_id IS NOT NULL OR approver_role_id IS NOT NULL",
                name="ck_procurement_approval_rules_approver",
            ),
            sa.CheckConstraint(
                "min_amount IS NULL OR max_amount IS NULL OR min_amount <= max_amount",
                name="ck_procurement_approval_rules_amount_range",
            ),
        )
    _create_index_once("ix_procurement_approval_rules_document_type", "procurement_approval_rules", ["document_type"])
    _create_index_once("ix_procurement_approval_rules_company_id", "procurement_approval_rules", ["company_id"])
    _create_index_once("ix_procurement_approval_rules_branch_id", "procurement_approval_rules", ["branch_id"])
    _create_index_once("ix_procurement_approval_rules_cost_center_id", "procurement_approval_rules", ["cost_center_id"])
    _create_index_once("ix_procurement_approval_rules_department", "procurement_approval_rules", ["department"])
    _create_index_once("ix_procurement_approval_rules_supplier_category", "procurement_approval_rules", ["supplier_category"])
    _create_index_once("ix_procurement_approval_rules_product_category", "procurement_approval_rules", ["product_category"])
    _create_index_once("ix_procurement_approval_rules_is_active", "procurement_approval_rules", ["is_active"])


def downgrade() -> None:
    _drop_index_if_exists("ix_procurement_approval_rules_is_active", "procurement_approval_rules")
    _drop_index_if_exists("ix_procurement_approval_rules_product_category", "procurement_approval_rules")
    _drop_index_if_exists("ix_procurement_approval_rules_supplier_category", "procurement_approval_rules")
    _drop_index_if_exists("ix_procurement_approval_rules_department", "procurement_approval_rules")
    _drop_index_if_exists("ix_procurement_approval_rules_cost_center_id", "procurement_approval_rules")
    _drop_index_if_exists("ix_procurement_approval_rules_branch_id", "procurement_approval_rules")
    _drop_index_if_exists("ix_procurement_approval_rules_company_id", "procurement_approval_rules")
    _drop_index_if_exists("ix_procurement_approval_rules_document_type", "procurement_approval_rules")
    if _has_table("procurement_approval_rules"):
        op.drop_table("procurement_approval_rules")

    for table_name in reversed(PROCUREMENT_SCOPE_TABLES):
        if not _has_table(table_name):
            continue
        for index_name in (
            f"ix_{table_name}_department",
            f"ix_{table_name}_cost_center_id",
            f"ix_{table_name}_branch_id",
            f"ix_{table_name}_company_id",
        ):
            _drop_index_if_exists(index_name, table_name)
        for constraint_name in (
            f"fk_{table_name}_cost_center_id",
            f"fk_{table_name}_branch_id",
            f"fk_{table_name}_company_id",
        ):
            _drop_constraint_if_exists(constraint_name, table_name)
        existing = _columns(table_name)
        for column_name in ("department", "cost_center_id", "branch_id", "company_id"):
            if column_name in existing:
                op.drop_column(table_name, column_name)

    if _has_table("suppliers"):
        _drop_index_if_exists("ix_suppliers_risk_level", "suppliers")
        _drop_index_if_exists("ix_suppliers_qualification_status", "suppliers")
        _drop_index_if_exists("ix_suppliers_supplier_category", "suppliers")
        _drop_constraint_if_exists("fk_suppliers_approved_by_id", "suppliers")
        existing = _columns("suppliers")
        for column_name in (
            "approved_at",
            "approved_by_id",
            "approved_until",
            "approved_from",
            "risk_level",
            "qualification_status",
            "supplier_category",
        ):
            if column_name in existing:
                op.drop_column("suppliers", column_name)

    _drop_enum("procurement_approval_document_type")
    _drop_enum("supplier_risk_level")
    _drop_enum("supplier_qualification_status")
