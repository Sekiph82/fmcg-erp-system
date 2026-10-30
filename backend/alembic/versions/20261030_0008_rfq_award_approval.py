"""Add RFQ award allocation proposals and configured approval routing.

Revision ID: 20261030_0008
Revises: 20261030_0007
Create Date: 2026-10-30
"""

from __future__ import annotations

import re

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261030_0008"
down_revision = "20261030_0007"
branch_labels = None
depends_on = None

OWNERSHIP_TABLE = "rfq_award_migration_ownership"
AWARD_STATUS = "rfqawardstatus"
APPROVAL_STATUS = "rfqawardapprovalstatus"
AWARD_ENUM = postgresql.ENUM("PENDING_APPROVAL", "APPROVED", "REJECTED", name=AWARD_STATUS)
APPROVAL_ENUM = postgresql.ENUM("PENDING", "APPROVED", "REJECTED", "SKIPPED", name=APPROVAL_STATUS)


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return _inspector().has_table(name)


def _normalize_check(expression: str) -> str:
    normalized = expression.lower().replace('"', "").replace("'", "")
    normalized = re.sub(r"::[a-z_][a-z0-9_]*", "", normalized)
    return re.sub(r"[\s()]", "", normalized)


def _validate_column(table: str, name: str, kind: str, nullable: bool) -> None:
    columns = {item["name"]: item for item in _inspector().get_columns(table)}
    column = columns.get(name)
    if column is None or column["nullable"] != nullable:
        raise RuntimeError(f"Existing {table} is missing compatible column {name}.")
    actual = column["type"]
    if kind == "uuid" and not isinstance(actual, postgresql.UUID):
        raise RuntimeError(f"Existing {table}.{name} must use PostgreSQL UUID.")
    if kind.startswith("string_"):
        length = int(kind.split("_", 1)[1])
        if not isinstance(actual, sa.String) or actual.length != length:
            raise RuntimeError(f"Existing {table}.{name} must be VARCHAR({length}).")
    if kind.startswith("numeric_"):
        precision, scale = (int(value) for value in kind.split("_")[1:])
        if not isinstance(actual, sa.Numeric) or actual.precision != precision or actual.scale != scale:
            raise RuntimeError(f"Existing {table}.{name} must be NUMERIC({precision}, {scale}).")
    if kind == "integer" and not isinstance(actual, sa.Integer):
        raise RuntimeError(f"Existing {table}.{name} must be INTEGER.")
    if kind == "boolean" and not isinstance(actual, sa.Boolean):
        raise RuntimeError(f"Existing {table}.{name} must be BOOLEAN.")
    if kind == "timestamp" and not (isinstance(actual, sa.DateTime) and actual.timezone):
        raise RuntimeError(f"Existing {table}.{name} must be timezone-aware TIMESTAMP.")
    if kind.startswith("enum_"):
        enum_name = kind.split("_", 1)[1]
        if not isinstance(actual, postgresql.ENUM) or actual.name != enum_name:
            raise RuntimeError(f"Existing {table}.{name} must use enum {enum_name}.")


def _validate_table(
    table: str,
    columns: dict[str, tuple[str, bool]],
    checks: dict[str, str],
    uniques: dict[str, tuple[str, ...]],
    indexes: dict[str, tuple[str, ...]],
    primary_key: tuple[str, ...],
    foreign_keys: set[tuple[str, str, str, str]],
) -> None:
    inspector = _inspector()
    actual_columns = {item["name"] for item in inspector.get_columns(table)}
    if actual_columns != set(columns):
        raise RuntimeError(f"Existing {table} has an incompatible column set.")
    for name, (kind, nullable) in columns.items():
        _validate_column(table, name, kind, nullable)
    actual_checks = {
        item["name"]: _normalize_check(item["sqltext"] or "")
        for item in inspector.get_check_constraints(table)
    }
    actual_uniques = {
        item["name"]: tuple(item["column_names"] or [])
        for item in inspector.get_unique_constraints(table)
    }
    actual_indexes = {
        item["name"]: tuple(item["column_names"] or [])
        for item in inspector.get_indexes(table)
    }
    actual_pk = tuple(inspector.get_pk_constraint(table).get("constrained_columns") or [])
    actual_fks = {
        (source, item["referred_table"], target, (item.get("options") or {}).get("ondelete", "").upper())
        for item in inspector.get_foreign_keys(table)
        for source, target in zip(item["constrained_columns"], item["referred_columns"])
    }
    if any(actual_checks.get(name) != _normalize_check(expr) for name, expr in checks.items()):
        raise RuntimeError(f"Existing {table} has missing or incompatible CHECK constraints.")
    if any(actual_uniques.get(name) != cols for name, cols in uniques.items()):
        raise RuntimeError(f"Existing {table} has missing or incompatible unique constraints.")
    if any(actual_indexes.get(name) != cols for name, cols in indexes.items()):
        raise RuntimeError(f"Existing {table} has missing or incompatible indexes.")
    if actual_pk != primary_key:
        raise RuntimeError(f"Existing {table} has an incompatible primary key.")
    if not foreign_keys.issubset(actual_fks):
        raise RuntimeError(f"Existing {table} has missing or incompatible foreign keys.")


def _ensure_table(table: str, create, **shape) -> bool:
    created = not _has_table(table)
    if created:
        create()
    _validate_table(table, **shape)
    return created


def _create_awards() -> None:
    op.create_table(
        "rfq_awards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rfq_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("status", AWARD_ENUM, nullable=False),
        sa.Column("total_amount", sa.Numeric(30, 7), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("justification", sa.String(1000), nullable=False),
        sa.Column("requested_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("revision_no >= 1", name="ck_rfq_award_revision_positive"),
        sa.CheckConstraint(
            "total_amount >= 0 AND total_amount NOT IN ('NaN', 'Infinity', '-Infinity')",
            name="ck_rfq_award_total_amount_nonnegative",
        ),
        sa.ForeignKeyConstraint(["rfq_id"], ["rfq_requests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rfq_id", "revision_no", name="uq_rfq_award_revision"),
    )
    op.create_index("ix_rfq_awards_rfq_id", "rfq_awards", ["rfq_id"])


def _create_line_quotes() -> None:
    op.create_table(
        "rfq_response_line_quotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("response_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rfq_line_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quoted_unit_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("quoted_currency", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "quoted_unit_price > 0 AND quoted_unit_price NOT IN ('NaN', 'Infinity', '-Infinity')",
            name="ck_rfq_response_line_quote_price_positive",
        ),
        sa.ForeignKeyConstraint(["response_id"], ["rfq_responses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["rfq_line_id"], ["rfq_request_lines.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("response_id", "rfq_line_id", name="uq_rfq_response_line_quote"),
    )
    op.create_index("ix_rfq_response_line_quotes_response_id", "rfq_response_line_quotes", ["response_id"])


def _create_allocations() -> None:
    op.create_table(
        "rfq_award_allocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("award_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("response_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rfq_line_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "quantity > 0 AND quantity NOT IN ('NaN', 'Infinity', '-Infinity')",
            name="ck_rfq_award_allocation_quantity_positive",
        ),
        sa.ForeignKeyConstraint(["award_id"], ["rfq_awards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["response_id"], ["rfq_responses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["rfq_line_id"], ["rfq_request_lines.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "award_id", "response_id", "rfq_line_id", name="uq_rfq_award_allocation_line_response"
        ),
    )
    op.create_index("ix_rfq_award_allocations_award_id", "rfq_award_allocations", ["award_id"])


def _create_approvals() -> None:
    op.create_table(
        "rfq_award_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("award_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approval_rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approval_level", sa.Integer(), nullable=False),
        sa.Column("rule_name", sa.String(255), nullable=False),
        sa.Column("requires_all_matching_approvers", sa.Boolean(), nullable=False),
        sa.Column("approver_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_status", APPROVAL_ENUM, nullable=False),
        sa.Column("decided_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("comments", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("approval_level >= 1", name="ck_rfq_award_approval_level_positive"),
        sa.CheckConstraint(
            "(decision_status = 'PENDING' AND decided_by_id IS NULL AND decided_at IS NULL) OR "
            "(decision_status <> 'PENDING' AND decided_by_id IS NOT NULL AND decided_at IS NOT NULL)",
            name="ck_rfq_award_approval_decision_attribution",
        ),
        sa.ForeignKeyConstraint(["award_id"], ["rfq_awards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["approval_rule_id"], ["procurement_approval_rules.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["approver_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["decided_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "award_id", "approval_rule_id", "approver_user_id", name="uq_rfq_award_approval_assignee"
        ),
    )
    op.create_index("ix_rfq_award_approvals_award_id", "rfq_award_approvals", ["award_id"])


AWARDS_SHAPE = {
    "columns": {
        "id": ("uuid", False), "rfq_id": ("uuid", False), "revision_no": ("integer", False),
        "status": (f"enum_{AWARD_STATUS}", False), "total_amount": ("numeric_30_7", False),
        "currency": ("string_10", False), "justification": ("string_1000", False),
        "requested_by_id": ("uuid", True), "requested_at": ("timestamp", False),
        "decided_at": ("timestamp", True), "created_at": ("timestamp", False),
        "updated_at": ("timestamp", False),
    },
    "checks": {
        "ck_rfq_award_revision_positive": "revision_no >= 1",
        "ck_rfq_award_total_amount_nonnegative":
            "total_amount >= 0 AND total_amount <> ALL (ARRAY['NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric])",
    },
    "uniques": {"uq_rfq_award_revision": ("rfq_id", "revision_no")},
    "indexes": {"ix_rfq_awards_rfq_id": ("rfq_id",)},
    "primary_key": ("id",),
    "foreign_keys": {("rfq_id", "rfq_requests", "id", "RESTRICT"), ("requested_by_id", "users", "id", "SET NULL")},
}

LINE_QUOTES_SHAPE = {
    "columns": {
        "id": ("uuid", False), "response_id": ("uuid", False), "rfq_line_id": ("uuid", False),
        "quoted_unit_price": ("numeric_14_4", False), "quoted_currency": ("string_10", False),
        "created_at": ("timestamp", False), "updated_at": ("timestamp", False),
    },
    "checks": {
        "ck_rfq_response_line_quote_price_positive":
            "quoted_unit_price > 0 AND quoted_unit_price <> ALL (ARRAY['NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric])",
    },
    "uniques": {"uq_rfq_response_line_quote": ("response_id", "rfq_line_id")},
    "indexes": {"ix_rfq_response_line_quotes_response_id": ("response_id",)},
    "primary_key": ("id",),
    "foreign_keys": {
        ("response_id", "rfq_responses", "id", "RESTRICT"),
        ("rfq_line_id", "rfq_request_lines", "id", "RESTRICT"),
    },
}

ALLOCATIONS_SHAPE = {
    "columns": {
        "id": ("uuid", False), "award_id": ("uuid", False), "response_id": ("uuid", False),
        "rfq_line_id": ("uuid", True), "quantity": ("numeric_14_3", False),
        "created_at": ("timestamp", False), "updated_at": ("timestamp", False),
    },
    "checks": {
        "ck_rfq_award_allocation_quantity_positive":
            "quantity > 0 AND quantity <> ALL (ARRAY['NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric])",
    },
    "uniques": {
        "uq_rfq_award_allocation_line_response": ("award_id", "response_id", "rfq_line_id")
    },
    "indexes": {"ix_rfq_award_allocations_award_id": ("award_id",)},
    "primary_key": ("id",),
    "foreign_keys": {
        ("award_id", "rfq_awards", "id", "CASCADE"),
        ("response_id", "rfq_responses", "id", "RESTRICT"),
        ("rfq_line_id", "rfq_request_lines", "id", "RESTRICT"),
    },
}

APPROVALS_SHAPE = {
    "columns": {
        "id": ("uuid", False), "award_id": ("uuid", False), "approval_rule_id": ("uuid", False),
        "approval_level": ("integer", False), "rule_name": ("string_255", False),
        "requires_all_matching_approvers": ("boolean", False), "approver_user_id": ("uuid", False),
        "decision_status": (f"enum_{APPROVAL_STATUS}", False), "decided_by_id": ("uuid", True),
        "decided_at": ("timestamp", True), "comments": ("string_1000", True),
        "created_at": ("timestamp", False), "updated_at": ("timestamp", False),
    },
    "checks": {
        "ck_rfq_award_approval_level_positive": "approval_level >= 1",
        "ck_rfq_award_approval_decision_attribution":
            "(decision_status = 'PENDING' AND decided_by_id IS NULL AND decided_at IS NULL) OR "
            "(decision_status <> 'PENDING' AND decided_by_id IS NOT NULL AND decided_at IS NOT NULL)",
    },
    "uniques": {
        "uq_rfq_award_approval_assignee": ("award_id", "approval_rule_id", "approver_user_id")
    },
    "indexes": {"ix_rfq_award_approvals_award_id": ("award_id",)},
    "primary_key": ("id",),
    "foreign_keys": {
        ("award_id", "rfq_awards", "id", "CASCADE"),
        ("approval_rule_id", "procurement_approval_rules", "id", "RESTRICT"),
        ("approver_user_id", "users", "id", "RESTRICT"),
        ("decided_by_id", "users", "id", "RESTRICT"),
    },
}


def upgrade() -> None:
    inspector = _inspector()
    required_tables = {"rfq_requests", "rfq_responses", "rfq_request_lines", "procurement_approval_rules", "users"}
    missing = sorted(name for name in required_tables if not inspector.has_table(name))
    if missing:
        raise RuntimeError(f"Required procurement tables are missing: {', '.join(missing)}")
    if inspector.has_table(OWNERSHIP_TABLE):
        raise RuntimeError("RFQ award migration ownership marker already exists; refusing ambiguous re-entry.")

    existing_enums = {item["name"]: item["labels"] for item in inspector.get_enums(schema="public")}
    expected_enums = {
        AWARD_STATUS: ["PENDING_APPROVAL", "APPROVED", "REJECTED"],
        APPROVAL_STATUS: ["PENDING", "APPROVED", "REJECTED", "SKIPPED"],
    }
    for name, labels in expected_enums.items():
        if name in existing_enums and existing_enums[name] != labels:
            raise RuntimeError(f"Existing PostgreSQL enum {name} has incompatible labels.")
    created_award_enum = AWARD_STATUS not in existing_enums
    created_approval_enum = APPROVAL_STATUS not in existing_enums
    AWARD_ENUM.create(op.get_bind(), checkfirst=True)
    APPROVAL_ENUM.create(op.get_bind(), checkfirst=True)

    created_awards = _ensure_table(
        "rfq_awards", _create_awards, **AWARDS_SHAPE
    )
    created_line_quotes = _ensure_table(
        "rfq_response_line_quotes", _create_line_quotes, **LINE_QUOTES_SHAPE
    )
    created_allocations = _ensure_table(
        "rfq_award_allocations", _create_allocations, **ALLOCATIONS_SHAPE
    )
    created_approvals = _ensure_table(
        "rfq_award_approvals", _create_approvals, **APPROVALS_SHAPE
    )

    op.create_table(
        OWNERSHIP_TABLE,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_award_enum", sa.Boolean(), nullable=False),
        sa.Column("created_approval_enum", sa.Boolean(), nullable=False),
        sa.Column("created_awards_table", sa.Boolean(), nullable=False),
        sa.Column("created_line_quotes_table", sa.Boolean(), nullable=False),
        sa.Column("created_allocations_table", sa.Boolean(), nullable=False),
        sa.Column("created_approvals_table", sa.Boolean(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_rfq_award_migration_ownership_singleton"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        sa.text(
            f"INSERT INTO {OWNERSHIP_TABLE} "
            "(id, created_award_enum, created_approval_enum, created_awards_table, "
            "created_line_quotes_table, created_allocations_table, created_approvals_table) "
            "VALUES (1, :award_enum, :approval_enum, :awards, :line_quotes, :allocations, :approvals)"
        ).bindparams(
            award_enum=created_award_enum,
            approval_enum=created_approval_enum,
            awards=created_awards,
            line_quotes=created_line_quotes,
            allocations=created_allocations,
            approvals=created_approvals,
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = _inspector()
    if not inspector.has_table(OWNERSHIP_TABLE):
        raise RuntimeError("Cannot downgrade RFQ awards without migration ownership metadata.")
    ownership = bind.execute(sa.text(f"SELECT * FROM {OWNERSHIP_TABLE} WHERE id = 1")).mappings().one_or_none()
    if ownership is None:
        raise RuntimeError("Cannot downgrade RFQ awards: migration ownership metadata is incomplete.")

    created_tables = {
        "rfq_award_approvals": ownership["created_approvals_table"],
        "rfq_award_allocations": ownership["created_allocations_table"],
        "rfq_response_line_quotes": ownership["created_line_quotes_table"],
        "rfq_awards": ownership["created_awards_table"],
    }
    for table, created in created_tables.items():
        if created and _has_table(table) and bind.execute(
            sa.text(f"SELECT EXISTS (SELECT 1 FROM {table})")
        ).scalar():
            raise RuntimeError(f"Cannot downgrade: migration-owned {table} contains retained history.")
    for table, created in created_tables.items():
        if created and _has_table(table):
            op.drop_table(table)
    op.drop_table(OWNERSHIP_TABLE)

    if ownership["created_award_enum"]:
        AWARD_ENUM.drop(bind, checkfirst=True)
    if ownership["created_approval_enum"]:
        APPROVAL_ENUM.drop(bind, checkfirst=True)
