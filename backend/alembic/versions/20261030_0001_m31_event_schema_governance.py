"""Add governed, immutable webhook event schema versions."""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261030_0001"
down_revision = "20261029_0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    definition_columns = {column["name"] for column in inspector.get_columns("webhook_event_definitions")}
    if "schema_version" not in definition_columns:
        op.add_column(
            "webhook_event_definitions",
            sa.Column("schema_version", sa.Integer(), server_default="1", nullable=False),
        )
    definition_checks = {
        constraint["name"] for constraint in sa.inspect(bind).get_check_constraints("webhook_event_definitions")
    }
    if "ck_webhook_event_definition_schema_version_positive" not in definition_checks:
        op.create_check_constraint(
            "ck_webhook_event_definition_schema_version_positive",
            "webhook_event_definitions",
            "schema_version >= 1",
        )

    if not sa.inspect(bind).has_table("webhook_event_definition_versions"):
        op.create_table(
            "webhook_event_definition_versions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column(
                "event_def_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("webhook_event_definitions.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("schema_version", sa.Integer(), nullable=False),
            sa.Column("payload_schema", postgresql.JSONB(), nullable=True),
            sa.Column("change_summary", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(length=100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("schema_version >= 1", name="ck_webhook_event_def_version_positive"),
            sa.UniqueConstraint("event_def_id", "schema_version", name="uq_webhook_event_def_version"),
        )
    version_indexes = {index["name"] for index in sa.inspect(bind).get_indexes("webhook_event_definition_versions")}
    if "ix_webhook_event_definition_versions_event_def_id" not in version_indexes:
        op.create_index(
            "ix_webhook_event_definition_versions_event_def_id",
            "webhook_event_definition_versions",
            ["event_def_id"],
        )

    definitions = sa.table(
        "webhook_event_definitions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("schema_version", sa.Integer()),
        sa.column("payload_schema", postgresql.JSONB()),
    )
    versions = sa.table(
        "webhook_event_definition_versions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("event_def_id", postgresql.UUID(as_uuid=True)),
        sa.column("schema_version", sa.Integer()),
        sa.column("payload_schema", postgresql.JSONB()),
        sa.column("change_summary", sa.Text()),
    )
    connection = op.get_bind()
    existing_rows = connection.execute(
        sa.select(versions.c.event_def_id, versions.c.schema_version)
    ).all()
    existing_versions = {(row[0], row[1]) for row in existing_rows}
    for definition_id, schema_version, payload_schema in connection.execute(
        sa.select(definitions.c.id, definitions.c.schema_version, definitions.c.payload_schema)
    ):
        if (definition_id, schema_version) in existing_versions:
            continue
        connection.execute(
            versions.insert().values(
                id=uuid4(),
                event_def_id=definition_id,
                schema_version=schema_version,
                payload_schema=payload_schema,
                change_summary="Baseline snapshot migrated from the existing event definition",
            )
        )


def downgrade() -> None:
    op.drop_index(
        "ix_webhook_event_definition_versions_event_def_id",
        table_name="webhook_event_definition_versions",
    )
    op.drop_table("webhook_event_definition_versions")
    op.drop_constraint(
        "ck_webhook_event_definition_schema_version_positive",
        "webhook_event_definitions",
        type_="check",
    )
    op.drop_column("webhook_event_definitions", "schema_version")
