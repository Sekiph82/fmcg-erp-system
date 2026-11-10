"""Link reviewed predictive-maintenance actions to planned PM work orders."""

from alembic import op
import sqlalchemy as sa


revision = "20261108_0026"
down_revision = "20261108_0025"
branch_labels = None
depends_on = None

_TABLE = "maintenance_predictions"
_TARGET = "pm_work_orders"
_LINKS = (
    (
        "work_order_id",
        sa.Uuid(as_uuid=True),
        "pm_work_orders",
        "fk_maintenance_predictions_work_order_id_pm_work_orders",
        "ix_maintenance_predictions_work_order_id",
    ),
    (
        "work_order_created_by_id",
        sa.Uuid(as_uuid=True),
        "users",
        "fk_maintenance_predictions_work_order_created_by_id_users",
        "ix_maintenance_predictions_work_order_created_by_id",
    ),
)
_TIMESTAMP_COLUMN = "work_order_created_at"


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if _TABLE not in tables:
        return
    columns = {column["name"] for column in sa.inspect(bind).get_columns(_TABLE)}
    if _TARGET not in tables or "users" not in tables:
        raise RuntimeError("pm_work_orders and users must exist before linking maintenance predictions")

    for column_name, column_type, target, fk_name, index_name in _LINKS:
        if column_name not in columns:
            op.add_column(_TABLE, sa.Column(column_name, column_type, nullable=True))

        foreign_keys = sa.inspect(bind).get_foreign_keys(_TABLE)
        if not any(
            fk.get("constrained_columns") == [column_name]
            and fk.get("referred_table") == target
            for fk in foreign_keys
        ):
            op.create_foreign_key(
                fk_name,
                _TABLE,
                target,
                [column_name],
                ["id"],
                ondelete="SET NULL",
            )

        indexes = {index["name"] for index in sa.inspect(bind).get_indexes(_TABLE)}
        if index_name not in indexes:
            op.create_index(index_name, _TABLE, [column_name])

    if _TIMESTAMP_COLUMN not in columns:
        op.add_column(_TABLE, sa.Column(_TIMESTAMP_COLUMN, sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if _TABLE not in set(sa.inspect(bind).get_table_names()):
        return

    columns = {column["name"] for column in sa.inspect(bind).get_columns(_TABLE)}
    if _TIMESTAMP_COLUMN in columns:
        op.drop_column(_TABLE, _TIMESTAMP_COLUMN)

    for column_name, _column_type, target, _fk_name, index_name in reversed(_LINKS):
        indexes = {index["name"] for index in sa.inspect(bind).get_indexes(_TABLE)}
        if index_name in indexes:
            op.drop_index(index_name, table_name=_TABLE)

        foreign_keys = sa.inspect(bind).get_foreign_keys(_TABLE)
        for foreign_key in foreign_keys:
            if (
                foreign_key.get("constrained_columns") == [column_name]
                and foreign_key.get("referred_table") == target
                and foreign_key.get("name")
            ):
                op.drop_constraint(foreign_key["name"], _TABLE, type_="foreignkey")

        columns = {column["name"] for column in sa.inspect(bind).get_columns(_TABLE)}
        if column_name in columns:
            op.drop_column(_TABLE, column_name)
