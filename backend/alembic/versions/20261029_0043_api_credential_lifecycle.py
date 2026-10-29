"""add application-linked API keys and one-time OAuth client secret records"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261029_0043"
down_revision = "20261029_0042"
branch_labels = None
depends_on = None


KEY_TABLE = "dev_api_keys"
KEY_COLUMN = "application_id"
SECRET_TABLE = "api_oauth_client_secrets"
KEY_FK = "fk_dev_api_keys_application_id_api_client_applications"
KEY_INDEX = "ix_dev_api_keys_application_id"
SECRET_FK = "fk_api_oauth_secrets_application_id_apps"
SECRET_INDEX = "ix_api_oauth_client_secrets_application_id"
SECRET_UNIQUE = "uq_api_oauth_client_secrets_secret_hash"

EXPECTED_SECRET_COLUMNS = {
    "secret_id": ("uuid", False),
    "application_id": ("uuid", False),
    "secret_name": ("string", False),
    "secret_prefix": ("string", False),
    "secret_hash": ("string", False),
    "is_active": ("boolean", False),
    "created_at": ("datetime_tz", False),
    "expires_at": ("datetime_tz", True),
}
EXPECTED_SECRET_DEFAULTS = {"is_active": "true", "created_at": "now()"}


def _normalize_default(value):
    if value is None:
        return None
    normalized = str(value).lower().strip()
    normalized = normalized.replace("::boolean", "").replace("::timestamp with time zone", "")
    while normalized.startswith("(") and normalized.endswith(")"):
        normalized = normalized[1:-1].strip()
    return normalized


def _assert_key_application_column(bind):
    inspector = sa.inspect(bind)
    if not inspector.has_table(KEY_TABLE):
        raise RuntimeError(f"Refusing to adopt credential lifecycle without existing {KEY_TABLE}.")
    columns = {column["name"]: column for column in inspector.get_columns(KEY_TABLE)}
    column = columns.get(KEY_COLUMN)
    if (
        column is None
        or not isinstance(column["type"], postgresql.UUID)
        or not column["type"].as_uuid
        or column["nullable"] is not True
    ):
        raise RuntimeError(f"Refusing to adopt incompatible {KEY_TABLE}.{KEY_COLUMN} definition.")

    foreign_keys = [
        item for item in inspector.get_foreign_keys(KEY_TABLE)
        if item.get("constrained_columns") == [KEY_COLUMN]
    ]
    if len(foreign_keys) != 1:
        raise RuntimeError(f"Refusing to adopt {KEY_TABLE}.{KEY_COLUMN} without its exact application foreign key.")
    foreign_key = foreign_keys[0]
    if (
        foreign_key.get("name") != KEY_FK
        or foreign_key.get("referred_table") != "api_client_applications"
        or foreign_key.get("referred_columns") != ["client_id"]
        or (foreign_key.get("options") or {}).get("ondelete", "").upper() != "SET NULL"
    ):
        raise RuntimeError(f"Refusing to adopt {KEY_TABLE}.{KEY_COLUMN} with an incompatible foreign key.")
    if not any(
        index.get("name") == KEY_INDEX and index.get("column_names") == [KEY_COLUMN] and not index.get("unique")
        for index in inspector.get_indexes(KEY_TABLE)
    ):
        raise RuntimeError(f"Refusing to adopt {KEY_TABLE}.{KEY_COLUMN} without the expected lookup index.")


def _assert_secret_table(bind):
    inspector = sa.inspect(bind)
    if not inspector.has_table(SECRET_TABLE):
        raise RuntimeError(f"Refusing to adopt missing {SECRET_TABLE}.")
    columns = {column["name"]: column for column in inspector.get_columns(SECRET_TABLE)}
    if set(columns) != set(EXPECTED_SECRET_COLUMNS):
        raise RuntimeError(f"Refusing to adopt incompatible {SECRET_TABLE} columns: {sorted(columns)}")

    for name, (kind, nullable) in EXPECTED_SECRET_COLUMNS.items():
        column = columns[name]
        column_type = column["type"]
        if kind == "uuid":
            compatible = isinstance(column_type, postgresql.UUID) and column_type.as_uuid
        elif kind == "string":
            length = 160 if name == "secret_name" else 16 if name == "secret_prefix" else 64
            compatible = isinstance(column_type, sa.String) and column_type.length == length
        elif kind == "boolean":
            compatible = isinstance(column_type, sa.Boolean)
        else:
            compatible = isinstance(column_type, sa.DateTime) and column_type.timezone
        if not compatible or column["nullable"] != nullable:
            raise RuntimeError(f"Refusing to adopt incompatible {SECRET_TABLE}.{name} definition.")

    for name, expected in EXPECTED_SECRET_DEFAULTS.items():
        if _normalize_default(columns[name].get("default")) != expected:
            raise RuntimeError(f"Refusing to adopt {SECRET_TABLE} with an incompatible {name} default.")
    if inspector.get_pk_constraint(SECRET_TABLE).get("constrained_columns") != ["secret_id"]:
        raise RuntimeError(f"Refusing to adopt {SECRET_TABLE} without its expected primary key.")

    unique_constraints = inspector.get_unique_constraints(SECRET_TABLE)
    if not any(
        item.get("name") == SECRET_UNIQUE and item.get("column_names") == ["secret_hash"]
        for item in unique_constraints
    ):
        raise RuntimeError(f"Refusing to adopt {SECRET_TABLE} without a unique secret hash constraint.")
    foreign_keys = inspector.get_foreign_keys(SECRET_TABLE)
    if len(foreign_keys) != 1 or not any(
        item.get("name") == SECRET_FK
        and item.get("constrained_columns") == ["application_id"]
        and item.get("referred_table") == "api_client_applications"
        and item.get("referred_columns") == ["client_id"]
        and (item.get("options") or {}).get("ondelete", "").upper() == "CASCADE"
        for item in foreign_keys
    ):
        raise RuntimeError(f"Refusing to adopt {SECRET_TABLE} without its expected application foreign key.")
    if not any(
        item.get("name") == SECRET_INDEX and item.get("column_names") == ["application_id"] and not item.get("unique")
        for item in inspector.get_indexes(SECRET_TABLE)
    ):
        raise RuntimeError(f"Refusing to adopt {SECRET_TABLE} without its expected application index.")


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(KEY_TABLE):
        raise RuntimeError(f"Refusing to create credential lifecycle without {KEY_TABLE}.")

    if KEY_COLUMN not in {item["name"] for item in inspector.get_columns(KEY_TABLE)}:
        op.add_column(KEY_TABLE, sa.Column(KEY_COLUMN, postgresql.UUID(as_uuid=True), nullable=True))
    inspector = sa.inspect(bind)
    if not any(
        item.get("name") == KEY_FK
        for item in inspector.get_foreign_keys(KEY_TABLE)
    ):
        op.create_foreign_key(
            KEY_FK,
            KEY_TABLE,
            "api_client_applications",
            [KEY_COLUMN],
            ["client_id"],
            ondelete="SET NULL",
        )
    if not any(item.get("name") == KEY_INDEX for item in inspector.get_indexes(KEY_TABLE)):
        op.create_index(KEY_INDEX, KEY_TABLE, [KEY_COLUMN], unique=False)
    _assert_key_application_column(bind)

    if not sa.inspect(bind).has_table(SECRET_TABLE):
        op.create_table(
            SECRET_TABLE,
            sa.Column("secret_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("secret_name", sa.String(length=160), nullable=False),
            sa.Column("secret_prefix", sa.String(length=16), nullable=False),
            sa.Column("secret_hash", sa.String(length=64), nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["application_id"], ["api_client_applications.client_id"],
                name=SECRET_FK, ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("secret_id"),
            sa.UniqueConstraint("secret_hash", name=SECRET_UNIQUE),
        )
        op.create_index(SECRET_INDEX, SECRET_TABLE, ["application_id"], unique=False)
    _assert_secret_table(bind)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(KEY_TABLE) or KEY_COLUMN not in {
        item["name"] for item in inspector.get_columns(KEY_TABLE)
    }:
        raise RuntimeError(f"Refusing to downgrade: expected {KEY_TABLE}.{KEY_COLUMN} is missing.")
    _assert_key_application_column(bind)
    _assert_secret_table(bind)

    bind.execute(sa.text(f'LOCK TABLE "{SECRET_TABLE}" IN ACCESS EXCLUSIVE MODE'))
    secret_count = bind.execute(sa.text(f'SELECT COUNT(*) FROM "{SECRET_TABLE}"')).scalar_one()
    if secret_count:
        raise RuntimeError(f"Refusing to downgrade {SECRET_TABLE}: {secret_count} credential record(s) would be lost.")
    bind.execute(sa.text(f'LOCK TABLE "{KEY_TABLE}" IN ACCESS EXCLUSIVE MODE'))
    linked_key_count = bind.execute(
        sa.text(f'SELECT COUNT(*) FROM "{KEY_TABLE}" WHERE "{KEY_COLUMN}" IS NOT NULL')
    ).scalar_one()
    if linked_key_count:
        raise RuntimeError(
            f"Refusing to downgrade {KEY_TABLE}.{KEY_COLUMN}: {linked_key_count} application link(s) would be lost."
        )

    op.drop_index(SECRET_INDEX, table_name=SECRET_TABLE)
    op.drop_table(SECRET_TABLE)
    op.drop_index(KEY_INDEX, table_name=KEY_TABLE)
    op.drop_constraint(KEY_FK, KEY_TABLE, type_="foreignkey")
    op.drop_column(KEY_TABLE, KEY_COLUMN)
