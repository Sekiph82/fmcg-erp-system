"""Add a shared, two-level downtime reason taxonomy and optional record links.

Existing incident text is preserved and is deliberately not backfilled to a
reason code because a text description is not reliable classification evidence.
"""

from alembic import op
import sqlalchemy as sa


revision = "20261108_0025"
down_revision = "20261108_0024"
branch_labels = None
depends_on = None


_ROOTS = (
    ("ASSET_FAILURE", "Asset failure", 10),
    ("MATERIAL_CONSTRAINT", "Material constraint", 20),
    ("PEOPLE_OR_QUALITY", "People or quality constraint", 30),
    ("PROCESS_LOSS", "Process loss", 40),
    ("STOP_CLASSIFICATION", "Stop classification", 50),
    ("UTILITY_FAILURE", "Utility failure", 60),
    ("UNCATEGORIZED", "Other or unclassified", 70),
)

_LEAVES = (
    ("MECHANICAL_BREAKDOWN", "Mechanical breakdown", "ASSET_FAILURE", 10),
    ("ELECTRICAL_ISSUE", "Electrical issue", "ASSET_FAILURE", 20),
    ("PNEUMATIC_ISSUE", "Pneumatic issue", "ASSET_FAILURE", 30),
    ("MAINTENANCE_INTERVENTION", "Maintenance intervention", "ASSET_FAILURE", 40),
    ("MATERIAL_SHORTAGE", "Material shortage", "MATERIAL_CONSTRAINT", 10),
    ("PACKAGING_SHORTAGE", "Packaging shortage", "MATERIAL_CONSTRAINT", 20),
    ("OPERATOR_UNAVAILABLE", "Operator unavailable", "PEOPLE_OR_QUALITY", 10),
    ("QC_WAITING", "Waiting for quality decision", "PEOPLE_OR_QUALITY", 20),
    ("CHANGEOVER_DELAY", "Changeover delay", "PROCESS_LOSS", 10),
    ("CLEANING_DELAY", "Cleaning delay", "PROCESS_LOSS", 20),
    ("SPEED_LOSS", "Speed loss", "PROCESS_LOSS", 30),
    ("MICRO_STOP", "Micro stop", "PROCESS_LOSS", 40),
    ("PLANNED_STOP", "Planned stop", "STOP_CLASSIFICATION", 10),
    ("UNPLANNED_STOP", "Unplanned stop", "STOP_CLASSIFICATION", 20),
    ("UTILITY_ISSUE", "Utility issue", "UTILITY_FAILURE", 10),
    ("OTHER", "Other reason", "UNCATEGORIZED", 10),
)


def _table_names(bind):
    return set(sa.inspect(bind).get_table_names())


def _create_reason_table(bind):
    if "maintenance_downtime_reason_codes" in _table_names(bind):
        return
    op.create_table(
        "maintenance_downtime_reason_codes",
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=150), nullable=False),
        sa.Column("parent_code", sa.String(length=100), nullable=True),
        sa.Column("is_selectable", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_code"],
            ["maintenance_downtime_reason_codes.code"],
            name="fk_maintenance_downtime_reason_codes_parent",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("code", name="pk_maintenance_downtime_reason_codes"),
    )
    op.create_index(
        "ix_maintenance_downtime_reason_codes_parent_code",
        "maintenance_downtime_reason_codes",
        ["parent_code"],
    )


def _seed_reason_codes():
    bind = op.get_bind()
    for code, label, order in _ROOTS:
        bind.execute(
            sa.text(
                """INSERT INTO maintenance_downtime_reason_codes
                   (code, label, parent_code, is_selectable, is_active, sort_order)
                   VALUES (:code, :label, NULL, FALSE, TRUE, :sort_order)
                   ON CONFLICT (code) DO NOTHING"""
            ),
            {"code": code, "label": label, "sort_order": order},
        )
    for code, label, parent_code, order in _LEAVES:
        bind.execute(
            sa.text(
                """INSERT INTO maintenance_downtime_reason_codes
                   (code, label, parent_code, is_selectable, is_active, sort_order)
                   VALUES (:code, :label, :parent_code, TRUE, TRUE, :sort_order)
                   ON CONFLICT (code) DO NOTHING"""
            ),
            {"code": code, "label": label, "parent_code": parent_code, "sort_order": order},
        )


def _add_optional_reason_link(bind, table_name):
    if table_name not in _table_names(bind):
        return
    columns = {column["name"] for column in sa.inspect(bind).get_columns(table_name)}
    if "reason_code" not in columns:
        op.add_column(table_name, sa.Column("reason_code", sa.String(length=100), nullable=True))
    inspector = sa.inspect(bind)
    foreign_keys = inspector.get_foreign_keys(table_name)
    if not any(
        fk.get("constrained_columns") == ["reason_code"]
        and fk.get("referred_table") == "maintenance_downtime_reason_codes"
        for fk in foreign_keys
    ):
        op.create_foreign_key(
            f"fk_{table_name}_downtime_reason_code",
            table_name,
            "maintenance_downtime_reason_codes",
            ["reason_code"],
            ["code"],
            ondelete="RESTRICT",
        )
    index_name = f"ix_{table_name}_reason_code"
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}
    if index_name not in indexes:
        op.create_index(index_name, table_name, ["reason_code"])


def upgrade() -> None:
    bind = op.get_bind()
    _create_reason_table(bind)
    _seed_reason_codes()
    for table_name in ("breakdown_records", "downtime_events", "downtime_intelligence"):
        _add_optional_reason_link(bind, table_name)


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in ("breakdown_records", "downtime_events", "downtime_intelligence"):
        if table_name not in _table_names(bind):
            continue
        columns = {column["name"] for column in sa.inspect(bind).get_columns(table_name)}
        if "reason_code" not in columns:
            continue
        foreign_keys = sa.inspect(bind).get_foreign_keys(table_name)
        for foreign_key in foreign_keys:
            if (
                foreign_key.get("constrained_columns") == ["reason_code"]
                and foreign_key.get("referred_table") == "maintenance_downtime_reason_codes"
            ):
                name = foreign_key.get("name")
                if name:
                    op.drop_constraint(name, table_name, type_="foreignkey")
        index_name = f"ix_{table_name}_reason_code"
        indexes = {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}
        if index_name in indexes:
            op.drop_index(index_name, table_name=table_name)
        op.drop_column(table_name, "reason_code")

    if "maintenance_downtime_reason_codes" in _table_names(bind):
        indexes = {index["name"] for index in sa.inspect(bind).get_indexes("maintenance_downtime_reason_codes")}
        if "ix_maintenance_downtime_reason_codes_parent_code" in indexes:
            op.drop_index(
                "ix_maintenance_downtime_reason_codes_parent_code",
                table_name="maintenance_downtime_reason_codes",
            )
        op.drop_table("maintenance_downtime_reason_codes")
