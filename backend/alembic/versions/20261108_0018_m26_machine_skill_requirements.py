"""Add canonical machine/operator skill qualification links.

The squashed baseline calls ``Base.metadata.create_all``. This migration is
therefore idempotent with respect to the new metadata: it also upgrades
databases that already passed that baseline before the M26 model existed.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261108_0018"
down_revision = "20261108_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    cert_columns = {column["name"] for column in inspector.get_columns("operator_skill_certs")}
    if "skill_id" not in cert_columns:
        op.add_column(
            "operator_skill_certs",
            sa.Column("skill_id", postgresql.UUID(as_uuid=True), nullable=True),
        )

    inspector = sa.inspect(bind)
    cert_foreign_keys = {foreign_key.get("name") for foreign_key in inspector.get_foreign_keys("operator_skill_certs")}
    if "fk_operator_skill_certs_skill_id_training_skills" not in cert_foreign_keys:
        op.create_foreign_key(
            "fk_operator_skill_certs_skill_id_training_skills",
            "operator_skill_certs",
            "training_skills",
            ["skill_id"],
            ["skill_id"],
            ondelete="RESTRICT",
        )

    cert_indexes = {index["name"] for index in inspector.get_indexes("operator_skill_certs")}
    if "ix_operator_skill_certs_skill_id" not in cert_indexes:
        op.create_index("ix_operator_skill_certs_skill_id", "operator_skill_certs", ["skill_id"])

    if not sa.inspect(bind).has_table("machine_skill_requirements"):
        op.create_table(
            "machine_skill_requirements",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("machine_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("work_center_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("skill_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("minimum_skill_level", sa.String(length=20), server_default="basic", nullable=False),
            sa.Column("certification_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("active_flag", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint(
                "(machine_id IS NOT NULL AND work_center_id IS NULL) OR "
                "(machine_id IS NULL AND work_center_id IS NOT NULL)",
                name="ck_machine_skill_requirements_exactly_one_resource",
            ),
            sa.CheckConstraint(
                "minimum_skill_level IN ('basic', 'intermediate', 'advanced', 'expert')",
                name="ck_machine_skill_requirements_minimum_level",
            ),
            sa.ForeignKeyConstraint(
                ["machine_id"], ["machines.id"],
                name="fk_machine_skill_requirements_machine_id_machines",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["work_center_id"], ["work_centers.id"],
                name="fk_machine_skill_requirements_work_center_id_work_centers",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["skill_id"], ["training_skills.skill_id"],
                name="fk_machine_skill_requirements_skill_id_training_skills",
                ondelete="RESTRICT",
            ),
            sa.ForeignKeyConstraint(
                ["created_by"], ["users.id"],
                name="fk_machine_skill_requirements_created_by_users",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["updated_by"], ["users.id"],
                name="fk_machine_skill_requirements_updated_by_users",
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id", name="pk_machine_skill_requirements"),
        )
        op.create_index("ix_machine_skill_requirements_machine_id", "machine_skill_requirements", ["machine_id"])
        op.create_index("ix_machine_skill_requirements_work_center_id", "machine_skill_requirements", ["work_center_id"])
        op.create_index("ix_machine_skill_requirements_skill_id", "machine_skill_requirements", ["skill_id"])
        op.create_index("ix_machine_skill_requirements_created_by", "machine_skill_requirements", ["created_by"])
        op.create_index("ix_machine_skill_requirements_updated_by", "machine_skill_requirements", ["updated_by"])
        op.create_index(
            "uq_machine_skill_requirements_machine_skill",
            "machine_skill_requirements",
            ["machine_id", "skill_id"],
            unique=True,
            postgresql_where=sa.text("machine_id IS NOT NULL"),
        )
        op.create_index(
            "uq_machine_skill_requirements_work_center_skill",
            "machine_skill_requirements",
            ["work_center_id", "skill_id"],
            unique=True,
            postgresql_where=sa.text("work_center_id IS NOT NULL"),
        )

    inspector = sa.inspect(bind)
    requirement_columns = {column["name"] for column in inspector.get_columns("machine_skill_requirements")}
    for column_name in ("created_by", "updated_by"):
        if column_name not in requirement_columns:
            op.add_column(
                "machine_skill_requirements",
                sa.Column(column_name, postgresql.UUID(as_uuid=True), nullable=True),
            )

    inspector = sa.inspect(bind)
    requirement_foreign_keys = {
        foreign_key.get("name") for foreign_key in inspector.get_foreign_keys("machine_skill_requirements")
    }
    for column_name in ("created_by", "updated_by"):
        constraint_name = f"fk_machine_skill_requirements_{column_name}_users"
        if constraint_name not in requirement_foreign_keys:
            op.create_foreign_key(
                constraint_name,
                "machine_skill_requirements",
                "users",
                [column_name],
                ["id"],
                ondelete="SET NULL",
            )

    requirement_indexes = {index["name"] for index in sa.inspect(bind).get_indexes("machine_skill_requirements")}
    for column_name in ("created_by", "updated_by"):
        index_name = f"ix_machine_skill_requirements_{column_name}"
        if index_name not in requirement_indexes:
            op.create_index(index_name, "machine_skill_requirements", [column_name])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("machine_skill_requirements"):
        op.drop_table("machine_skill_requirements")

    inspector = sa.inspect(bind)
    if inspector.has_table("operator_skill_certs"):
        indexes = {index["name"] for index in inspector.get_indexes("operator_skill_certs")}
        if "ix_operator_skill_certs_skill_id" in indexes:
            op.drop_index("ix_operator_skill_certs_skill_id", table_name="operator_skill_certs")

        foreign_keys = {foreign_key.get("name") for foreign_key in inspector.get_foreign_keys("operator_skill_certs")}
        if "fk_operator_skill_certs_skill_id_training_skills" in foreign_keys:
            op.drop_constraint(
                "fk_operator_skill_certs_skill_id_training_skills",
                "operator_skill_certs",
                type_="foreignkey",
            )

        columns = {column["name"] for column in sa.inspect(bind).get_columns("operator_skill_certs")}
        if "skill_id" in columns:
            op.drop_column("operator_skill_certs", "skill_id")
