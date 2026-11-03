"""Link QMS corrective actions to supplier records and evaluations.

Revision ID: 20261104_0001
Revises: 20261030_0010
Create Date: 2026-11-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261104_0001"
down_revision = "20261030_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "corrective_actions",
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "corrective_actions",
        sa.Column("supplier_evaluation_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_corrective_actions_supplier_id_suppliers",
        "corrective_actions",
        "suppliers",
        ["supplier_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_corrective_actions_supplier_evaluation_id",
        "corrective_actions",
        "supplier_evaluations",
        ["supplier_evaluation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_corrective_actions_supplier_id", "corrective_actions", ["supplier_id"])
    op.create_index(
        "ix_corrective_actions_supplier_evaluation_id",
        "corrective_actions",
        ["supplier_evaluation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_corrective_actions_supplier_evaluation_id", table_name="corrective_actions")
    op.drop_index("ix_corrective_actions_supplier_id", table_name="corrective_actions")
    bind = op.get_bind()
    for column, target in (
        ("supplier_evaluation_id", "supplier_evaluations"),
        ("supplier_id", "suppliers"),
    ):
        names = bind.execute(
            sa.text(
                "SELECT c.conname "
                "FROM pg_constraint c "
                "WHERE c.contype = 'f' "
                "AND c.conrelid = 'public.corrective_actions'::regclass "
                "AND c.confrelid = (:target)::regclass "
                "AND c.conkey = ARRAY[(SELECT a.attnum FROM pg_attribute a "
                "WHERE a.attrelid = c.conrelid AND a.attname = :column)]::smallint[]"
            ),
            {"column": column, "target": f"public.{target}"},
        ).scalars().all()
        for name in names:
            op.drop_constraint(name, "corrective_actions", type_="foreignkey")
    op.drop_column("corrective_actions", "supplier_evaluation_id")
    op.drop_column("corrective_actions", "supplier_id")
