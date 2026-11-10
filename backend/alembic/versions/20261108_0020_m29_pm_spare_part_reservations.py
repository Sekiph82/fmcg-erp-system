"""Add explicit PM spare-part requirements and scheduling reservations."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261108_0020"
down_revision = "20261108_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "pm_plan_spare_part_requirements" not in tables:
        op.create_table(
            "pm_plan_spare_part_requirements",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("spare_part_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("quantity_required", sa.Numeric(16, 4), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["plan_id"], ["pm_plans.id"], name="fk_pm_plan_spare_req_plan", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["spare_part_id"], ["spare_parts.id"], name="fk_pm_plan_spare_req_part", ondelete="RESTRICT"),
            sa.UniqueConstraint("plan_id", "spare_part_id", name="uq_pm_plan_spare_part_requirement"),
            sa.CheckConstraint("quantity_required > 0", name="ck_pm_plan_spare_part_requirement_quantity_positive"),
        )

    if "pm_work_order_spare_part_reservations" not in tables:
        op.create_table(
            "pm_work_order_spare_part_reservations",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("work_order_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("spare_part_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("quantity_reserved", sa.Numeric(16, 4), nullable=False),
            sa.Column("quantity_consumed", sa.Numeric(16, 4), server_default="0", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["work_order_id"], ["pm_work_orders.id"], name="fk_pm_wo_spare_reservation_work_order", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["spare_part_id"], ["spare_parts.id"], name="fk_pm_wo_spare_reservation_part", ondelete="RESTRICT"),
            sa.UniqueConstraint("work_order_id", "spare_part_id", name="uq_pm_work_order_spare_part_reservation"),
            sa.CheckConstraint("quantity_reserved > 0", name="ck_pm_wo_spare_reservation_quantity_positive"),
            sa.CheckConstraint(
                "quantity_consumed >= 0 AND quantity_consumed <= quantity_reserved",
                name="ck_pm_wo_spare_reservation_consumed_range",
            ),
        )

    for table_name, column_name in (
        ("pm_plan_spare_part_requirements", "plan_id"),
        ("pm_plan_spare_part_requirements", "spare_part_id"),
        ("pm_work_order_spare_part_reservations", "work_order_id"),
        ("pm_work_order_spare_part_reservations", "spare_part_id"),
    ):
        indexes = {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}
        index_name = f"ix_{table_name}_{column_name}"
        if index_name not in indexes:
            op.create_index(index_name, table_name, [column_name])


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "pm_work_order_spare_part_reservations" in tables:
        op.drop_table("pm_work_order_spare_part_reservations")
    if "pm_plan_spare_part_requirements" in tables:
        op.drop_table("pm_plan_spare_part_requirements")
