"""Add weighted technical/commercial RFQ bid evaluation matrices.

Revision ID: 20261030_0007
Revises: 20261030_0006
Create Date: 2026-10-30
"""

from __future__ import annotations

import re

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261030_0007"
down_revision = "20261030_0006"
branch_labels = None
depends_on = None

OWNERSHIP_TABLE = "rfq_evaluation_migration_ownership"
DIMENSION_TYPE = "rfqevaluationdimension"
STATUS_TYPE = "rfqevaluationstatus"


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return _inspector().has_table(name)


def _validate_enum(name: str, expected: list[str]) -> None:
    enums = {item["name"]: item["labels"] for item in _inspector().get_enums(schema="public")}
    if enums.get(name) != expected:
        raise RuntimeError(f"Existing PostgreSQL enum {name} has an incompatible or incomplete label set.")


def _validate_column(table: str, name: str, expected_type, nullable: bool) -> None:
    columns = {item["name"]: item for item in _inspector().get_columns(table)}
    column = columns.get(name)
    if column is None:
        raise RuntimeError(f"Existing {table} is missing required evaluation column {name}.")
    if column["nullable"] != nullable:
        raise RuntimeError(f"Existing {table}.{name} has incompatible nullability.")
    actual_type = column["type"]
    if expected_type == "uuid" and not isinstance(actual_type, postgresql.UUID):
        raise RuntimeError(f"Existing {table}.{name} must be PostgreSQL UUID.")
    if expected_type.startswith("string_"):
        expected_length = int(expected_type.split("_", 1)[1])
        if not isinstance(actual_type, sa.String) or actual_type.length != expected_length:
            raise RuntimeError(f"Existing {table}.{name} must be VARCHAR({expected_length}).")
    if expected_type == "enum" and (
        not isinstance(actual_type, postgresql.ENUM) or actual_type.name != DIMENSION_TYPE
    ):
        raise RuntimeError(f"Existing {table}.{name} must use enum {DIMENSION_TYPE}.")
    if expected_type == "status_enum" and (
        not isinstance(actual_type, postgresql.ENUM) or actual_type.name != STATUS_TYPE
    ):
        raise RuntimeError(f"Existing {table}.{name} must use enum {STATUS_TYPE}.")
    if expected_type == "numeric" and (
        not isinstance(actual_type, sa.Numeric)
        or actual_type.precision != 5
        or actual_type.scale != 2
    ):
        raise RuntimeError(f"Existing {table}.{name} must be NUMERIC(5, 2).")
    if expected_type == "boolean" and not isinstance(actual_type, sa.Boolean):
        raise RuntimeError(f"Existing {table}.{name} must be BOOLEAN.")
    if expected_type == "integer" and not isinstance(actual_type, sa.Integer):
        raise RuntimeError(f"Existing {table}.{name} must be INTEGER.")
    if expected_type == "timestamp" and not (
        isinstance(actual_type, sa.DateTime) and actual_type.timezone
    ):
        raise RuntimeError(f"Existing {table}.{name} must be a timezone-aware timestamp.")


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
    for name, (kind, nullable) in columns.items():
        _validate_column(table, name, kind, nullable)
    present_checks = {
        item["name"]: _normalize_check(item["sqltext"] or "")
        for item in inspector.get_check_constraints(table)
    }
    present_uniques = {
        item["name"]: tuple(item["column_names"] or []) for item in inspector.get_unique_constraints(table)
    }
    present_indexes = {item["name"]: tuple(item["column_names"] or []) for item in inspector.get_indexes(table)}
    present_primary_key = tuple(inspector.get_pk_constraint(table).get("constrained_columns") or [])
    present_fks = {
        (source, item["referred_table"], target, (item.get("options") or {}).get("ondelete", "").upper())
        for item in inspector.get_foreign_keys(table)
        for source, target in zip(item["constrained_columns"], item["referred_columns"])
    }
    if any(present_checks.get(name) != expression for name, expression in checks.items()):
        raise RuntimeError(f"Existing {table} has missing or incompatible evaluation check constraints.")
    if any(present_uniques.get(name) != columns for name, columns in uniques.items()):
        raise RuntimeError(f"Existing {table} is missing required evaluation uniqueness constraints.")
    if any(present_indexes.get(name) != columns for name, columns in indexes.items()):
        raise RuntimeError(f"Existing {table} is missing required evaluation indexes.")
    if present_primary_key != primary_key:
        raise RuntimeError(f"Existing {table} has an incompatible primary key.")
    if not foreign_keys.issubset(present_fks):
        raise RuntimeError(f"Existing {table} is missing required evaluation foreign keys.")


def _normalize_check(expression: str) -> str:
    normalized = expression.lower().replace("::numeric", "").replace('"', "").replace("'", "")
    return re.sub(r"[\s()]", "", normalized)


def _criteria_shape() -> None:
    _validate_table(
        "rfq_evaluation_criteria",
        {
            "id": ("uuid", False),
            "rfq_id": ("uuid", False),
            "code": ("string_50", False),
            "name": ("string_200", False),
            "dimension": ("enum", False),
            "weight_percent": ("numeric", False),
            "is_mandatory": ("boolean", False),
            "created_by_id": ("uuid", True),
            "created_at": ("timestamp", False),
            "updated_at": ("timestamp", False),
        },
        {
            "ck_rfq_evaluation_criterion_weight_range": _normalize_check(
                "weight_percent > 0 AND weight_percent <= 100 "
                "AND weight_percent <> ALL (ARRAY['NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric])"
            )
        },
        {"uq_rfq_evaluation_criterion_code": ("rfq_id", "code")},
        {"ix_rfq_evaluation_criteria_rfq_id": ("rfq_id",)},
        ("id",),
        {("rfq_id", "rfq_requests", "id", "CASCADE"), ("created_by_id", "users", "id", "SET NULL")},
    )


def _evaluations_shape() -> None:
    _validate_table(
        "rfq_response_evaluations",
        {
            "id": ("uuid", False),
            "response_id": ("uuid", False),
            "criterion_id": ("uuid", False),
            "revision_no": ("integer", False),
            "score": ("numeric", False),
            "passes_gate": ("boolean", True),
            "comments": ("string_1000", True),
            "evaluator_id": ("uuid", True),
            "evaluated_at": ("timestamp", False),
            "created_at": ("timestamp", False),
            "updated_at": ("timestamp", False),
        },
        {
            "ck_rfq_response_evaluation_score_range": _normalize_check(
                "score >= 0 AND score <= 100 "
                "AND score <> ALL (ARRAY['NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric])"
            ),
            "ck_rfq_response_evaluation_revision_positive": _normalize_check("revision_no >= 1"),
        },
        {"uq_rfq_response_evaluation_revision": ("response_id", "criterion_id", "revision_no")},
        {
            "ix_rfq_response_evaluations_response_id": ("response_id",),
            "ix_rfq_response_evaluations_criterion_id": ("criterion_id",),
        },
        ("id",),
        {
            ("response_id", "rfq_responses", "id", "CASCADE"),
            ("criterion_id", "rfq_evaluation_criteria", "id", "CASCADE"),
            ("evaluator_id", "users", "id", "SET NULL"),
        },
    )


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_table("rfq_responses") or not _has_table("rfq_requests") or not _has_table("users"):
        raise RuntimeError("Expected the existing RFQ and user aggregates; refusing parallel procurement tables.")
    if _has_table(OWNERSHIP_TABLE):
        raise RuntimeError("Evaluation migration ownership marker already exists; refusing ambiguous adoption.")

    inspector = _inspector()
    enums_before = {item["name"] for item in inspector.get_enums(schema="public")}
    dimension_type = postgresql.ENUM("TECHNICAL", "COMMERCIAL", name=DIMENSION_TYPE)
    status_type = postgresql.ENUM("NOT_EVALUATED", "QUALIFIED", "DISQUALIFIED", name=STATUS_TYPE)
    dimension_type.create(bind, checkfirst=True)
    status_type.create(bind, checkfirst=True)
    _validate_enum(DIMENSION_TYPE, ["TECHNICAL", "COMMERCIAL"])
    _validate_enum(STATUS_TYPE, ["NOT_EVALUATED", "QUALIFIED", "DISQUALIFIED"])

    response_columns = {column["name"]: column for column in _inspector().get_columns("rfq_responses")}
    created_status_column = "evaluation_status" not in response_columns
    if created_status_column:
        op.add_column(
            "rfq_responses",
            sa.Column("evaluation_status", status_type, nullable=False, server_default="NOT_EVALUATED"),
        )
        op.alter_column(
            "rfq_responses",
            "evaluation_status",
            existing_type=status_type,
            existing_nullable=False,
            server_default=None,
        )
    else:
        _validate_column("rfq_responses", "evaluation_status", "status_enum", False)

    created_criteria_table = not _has_table("rfq_evaluation_criteria")
    if created_criteria_table:
        op.create_table(
            "rfq_evaluation_criteria",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("rfq_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("code", sa.String(50), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("dimension", dimension_type, nullable=False),
            sa.Column("weight_percent", sa.Numeric(5, 2), nullable=False),
            sa.Column("is_mandatory", sa.Boolean(), nullable=False),
            sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint(
                "weight_percent > 0 AND weight_percent <= 100 AND weight_percent NOT IN ('NaN', 'Infinity', '-Infinity')",
                name="ck_rfq_evaluation_criterion_weight_range",
            ),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["rfq_id"], ["rfq_requests.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("rfq_id", "code", name="uq_rfq_evaluation_criterion_code"),
        )
        op.create_index("ix_rfq_evaluation_criteria_rfq_id", "rfq_evaluation_criteria", ["rfq_id"])
    _criteria_shape()

    created_evaluations_table = not _has_table("rfq_response_evaluations")
    if created_evaluations_table:
        op.create_table(
            "rfq_response_evaluations",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("response_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("criterion_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("revision_no", sa.Integer(), nullable=False),
            sa.Column("score", sa.Numeric(5, 2), nullable=False),
            sa.Column("passes_gate", sa.Boolean(), nullable=True),
            sa.Column("comments", sa.String(1000), nullable=True),
            sa.Column("evaluator_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint(
                "score >= 0 AND score <= 100 AND score NOT IN ('NaN', 'Infinity', '-Infinity')",
                name="ck_rfq_response_evaluation_score_range",
            ),
            sa.CheckConstraint("revision_no >= 1", name="ck_rfq_response_evaluation_revision_positive"),
            sa.ForeignKeyConstraint(["criterion_id"], ["rfq_evaluation_criteria.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["evaluator_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["response_id"], ["rfq_responses.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "response_id", "criterion_id", "revision_no", name="uq_rfq_response_evaluation_revision"
            ),
        )
        op.create_index("ix_rfq_response_evaluations_response_id", "rfq_response_evaluations", ["response_id"])
        op.create_index("ix_rfq_response_evaluations_criterion_id", "rfq_response_evaluations", ["criterion_id"])
    _evaluations_shape()

    op.create_table(
        OWNERSHIP_TABLE,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_dimension_enum", sa.Boolean(), nullable=False),
        sa.Column("created_status_enum", sa.Boolean(), nullable=False),
        sa.Column("created_status_column", sa.Boolean(), nullable=False),
        sa.Column("created_criteria_table", sa.Boolean(), nullable=False),
        sa.Column("created_evaluations_table", sa.Boolean(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_rfq_evaluation_migration_ownership_singleton"),
        sa.PrimaryKeyConstraint("id"),
    )
    bind.execute(
        sa.text(
            f"INSERT INTO {OWNERSHIP_TABLE} "
            "(id, created_dimension_enum, created_status_enum, created_status_column, "
            "created_criteria_table, created_evaluations_table) "
            "VALUES (1, :dimension_enum, :status_enum, :status_column, :criteria_table, :evaluations_table)"
        ),
        {
            "dimension_enum": DIMENSION_TYPE not in enums_before,
            "status_enum": STATUS_TYPE not in enums_before,
            "status_column": created_status_column,
            "criteria_table": created_criteria_table,
            "evaluations_table": created_evaluations_table,
        },
    )


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_table(OWNERSHIP_TABLE):
        raise RuntimeError("Cannot downgrade: evaluation migration ownership metadata is missing.")
    ownership = bind.execute(sa.text(f"SELECT * FROM {OWNERSHIP_TABLE} WHERE id = 1")).mappings().one_or_none()
    if ownership is None:
        raise RuntimeError("Cannot downgrade: evaluation migration ownership metadata is incomplete.")

    if ownership["created_evaluations_table"] and _has_table("rfq_response_evaluations"):
        if bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM rfq_response_evaluations)")).scalar():
            raise RuntimeError("Cannot downgrade: RFQ bid evaluation history created by this migration would be destroyed.")
        op.drop_table("rfq_response_evaluations")
    if ownership["created_criteria_table"] and _has_table("rfq_evaluation_criteria"):
        if bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM rfq_evaluation_criteria)")).scalar():
            raise RuntimeError("Cannot downgrade: evaluation criteria created by this migration would be destroyed.")
        op.drop_table("rfq_evaluation_criteria")

    if ownership["created_status_column"]:
        if bind.execute(
            sa.text("SELECT EXISTS (SELECT 1 FROM rfq_responses WHERE evaluation_status <> 'NOT_EVALUATED')")
        ).scalar():
            raise RuntimeError("Cannot downgrade: evaluated bid status created by this migration would be discarded.")
        op.drop_column("rfq_responses", "evaluation_status")
    if ownership["created_status_enum"]:
        postgresql.ENUM(name=STATUS_TYPE).drop(bind, checkfirst=True)
    if ownership["created_dimension_enum"]:
        postgresql.ENUM(name=DIMENSION_TYPE).drop(bind, checkfirst=True)
    op.drop_table(OWNERSHIP_TABLE)
