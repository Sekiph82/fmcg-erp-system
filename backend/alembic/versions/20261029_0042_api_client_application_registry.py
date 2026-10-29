"""add owner-scoped API client application registry"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import re


revision = "20261029_0042"
down_revision = "20261029_0041"
branch_labels = None
depends_on = None


TABLE = "api_client_applications"
EXPECTED_COLUMNS = {
    "client_id": ("uuid", False),
    "owner_user_id": ("uuid", False),
    "name": ("string", False),
    "description": ("text", True),
    "environment": ("string", False),
    "is_active": ("boolean", False),
    "created_at": ("datetime", False),
    "updated_at": ("datetime", False),
}
EXPECTED_SERVER_DEFAULTS = {
    "environment": "'development'",
    "is_active": "true",
    "created_at": "now()",
    "updated_at": "now()",
}
EXPECTED_ENVIRONMENT_CHECK_TABLE = "_expected_api_client_applications_environment_check"


def _normalize_server_default(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.lower().strip()
    normalized = normalized.replace("::character varying", "").replace("::text", "")
    while normalized.startswith("(") and normalized.endswith(")"):
        normalized = normalized[1:-1].strip()
    return normalized


def _constraint_expression(bind, relation: str) -> str | None:
    expression = bind.execute(
        sa.text(
            "SELECT pg_get_expr(constraint_row.conbin, constraint_row.conrelid) "
            "FROM pg_constraint AS constraint_row "
            "WHERE constraint_row.conrelid = to_regclass(:relation) AND constraint_row.contype = 'c'"
        ),
        {"relation": relation},
    ).scalar_one_or_none()
    return re.sub(r"\s+", " ", expression.strip().lower()) if expression else None


def _assert_compatible_table(bind) -> None:
    inspector = sa.inspect(bind)
    columns = {column["name"]: column for column in inspector.get_columns(TABLE)}
    if set(columns) != set(EXPECTED_COLUMNS):
        raise RuntimeError(f"Refusing to adopt incompatible {TABLE} columns: {sorted(columns)}")

    for name, (kind, nullable) in EXPECTED_COLUMNS.items():
        column = columns[name]
        column_type = column["type"]
        if kind == "uuid":
            compatible_type = isinstance(column_type, postgresql.UUID) and column_type.as_uuid
        elif kind == "string":
            length = 160 if name == "name" else 20
            compatible_type = isinstance(column_type, sa.String) and column_type.length == length
        elif kind == "text":
            compatible_type = isinstance(column_type, sa.Text)
        elif kind == "boolean":
            compatible_type = isinstance(column_type, sa.Boolean)
        else:
            compatible_type = isinstance(column_type, sa.DateTime) and column_type.timezone
        if not compatible_type or column["nullable"] != nullable:
            raise RuntimeError(f"Refusing to adopt incompatible {TABLE}.{name} definition")

    for name, expected_default in EXPECTED_SERVER_DEFAULTS.items():
        actual_default = _normalize_server_default(columns[name].get("default"))
        if actual_default != expected_default:
            raise RuntimeError(f"Refusing to adopt incompatible {TABLE}.{name} server default")

    if inspector.get_pk_constraint(TABLE).get("constrained_columns") != ["client_id"]:
        raise RuntimeError(f"Refusing to adopt {TABLE} without the expected primary key")

    unique_constraints = inspector.get_unique_constraints(TABLE)
    if len(unique_constraints) != 1 or not any(
        item.get("name") == "uq_api_client_applications_owner_name_environment"
        and item.get("column_names") == ["owner_user_id", "name", "environment"]
        for item in unique_constraints
    ):
        raise RuntimeError(f"Refusing to adopt {TABLE} without the expected unique constraint")

    foreign_keys = inspector.get_foreign_keys(TABLE)
    if len(foreign_keys) != 1 or not any(
        item.get("constrained_columns") == ["owner_user_id"]
        and item.get("referred_table") == "users"
        and item.get("referred_columns") == ["id"]
        and (item.get("options") or {}).get("ondelete", "").upper() == "CASCADE"
        for item in foreign_keys
    ):
        raise RuntimeError(f"Refusing to adopt {TABLE} without the expected owner foreign key")

    check_constraints = inspector.get_check_constraints(TABLE)
    if len(check_constraints) != 1:
        raise RuntimeError(f"Refusing to adopt {TABLE} without the expected environment check")
    if check_constraints[0].get("name") != "ck_api_client_applications_environment":
        raise RuntimeError(f"Refusing to adopt {TABLE} with an incompatible environment check")

    bind.execute(
        sa.text(
            f"CREATE TEMP TABLE {EXPECTED_ENVIRONMENT_CHECK_TABLE} ("
            "environment VARCHAR(20), "
            "CONSTRAINT ck_expected_api_client_applications_environment "
            "CHECK (environment IN ('development', 'sandbox', 'production')))"
        )
    )
    try:
        expected_expression = _constraint_expression(bind, f"pg_temp.{EXPECTED_ENVIRONMENT_CHECK_TABLE}")
        actual_expression = _constraint_expression(bind, TABLE)
    finally:
        bind.execute(sa.text(f"DROP TABLE pg_temp.{EXPECTED_ENVIRONMENT_CHECK_TABLE}"))
    if not expected_expression or actual_expression != expected_expression:
        raise RuntimeError(f"Refusing to adopt {TABLE} with an incompatible environment check")

    indexes = [
        item for item in inspector.get_indexes(TABLE)
        if item.get("duplicates_constraint") is None and not item.get("unique")
    ]
    if len(indexes) != 1 or not any(
        item.get("name") == "ix_api_client_applications_owner_user_id"
        and item.get("column_names") == ["owner_user_id"]
        for item in indexes
    ):
        raise RuntimeError(f"Refusing to adopt {TABLE} without the expected owner index")


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table(TABLE):
        _assert_compatible_table(bind)
        return

    op.create_table(
        TABLE,
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("environment", sa.String(length=20), server_default="development", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "environment IN ('development', 'sandbox', 'production')",
            name="ck_api_client_applications_environment",
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("client_id"),
        sa.UniqueConstraint(
            "owner_user_id", "name", "environment",
            name="uq_api_client_applications_owner_name_environment",
        ),
    )
    op.create_index(
        "ix_api_client_applications_owner_user_id",
        TABLE,
        ["owner_user_id"],
    )
    _assert_compatible_table(bind)


def downgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(TABLE):
        return
    _assert_compatible_table(bind)
    # Block new registrations between the row check and DROP so a concurrent
    # insert cannot commit after the empty-table check and be silently deleted.
    bind.execute(sa.text(f'LOCK TABLE "{TABLE}" IN ACCESS EXCLUSIVE MODE'))
    row_count = bind.execute(sa.text(f'SELECT COUNT(*) FROM "{TABLE}"')).scalar_one()
    if row_count:
        raise RuntimeError(
            f"Refusing to downgrade {TABLE}: {row_count} application record(s) would be lost."
        )
    op.drop_index("ix_api_client_applications_owner_user_id", table_name=TABLE)
    op.drop_table(TABLE)
