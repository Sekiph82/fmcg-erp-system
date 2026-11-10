"""Persist operation-scoped Shop Floor idempotency keys.

Revision ID: 20261104_0012
Revises: 20261104_0011
Create Date: 2026-11-04
"""
from alembic import op
import sqlalchemy as sa


revision = "20261104_0012"
down_revision = "20261104_0011"
branch_labels = None
depends_on = None


def _constraint_exists(table: str, name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(
        constraint.get("name") == name
        for getter in (inspector.get_unique_constraints, inspector.get_check_constraints)
        for constraint in getter(table)
    )


def _create_constraint_if_missing(name: str, table: str, kind: str, *args) -> None:
    if _constraint_exists(table, name):
        return
    if kind == "unique":
        op.create_unique_constraint(name, table, list(args))
    elif kind == "check":
        op.create_check_constraint(name, table, args[0])
    else:  # pragma: no cover - protects future edits to this migration helper.
        raise ValueError(f"Unsupported constraint kind: {kind}")


def _drop_constraint_if_present(name: str, table: str, kind: str) -> None:
    if _constraint_exists(table, name):
        op.drop_constraint(name, table, type_=kind)


def upgrade() -> None:
    op.add_column("sf_activity_logs", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.add_column("sf_activity_logs", sa.Column("idempotency_fingerprint", sa.String(length=64), nullable=True))
    _create_constraint_if_missing(
        "uq_sf_activity_logs_actor_idempotency",
        "sf_activity_logs",
        "unique",
        "work_order_id", "actor_user_id", "idempotency_key",
    )
    _create_constraint_if_missing(
        "ck_sf_activity_logs_idempotency_pair",
        "sf_activity_logs",
        "check",
        "(idempotency_key IS NULL AND idempotency_fingerprint IS NULL) OR "
        "(idempotency_key IS NOT NULL AND idempotency_fingerprint IS NOT NULL)",
    )

    downtime_columns = (
        ("start_idempotency_key", sa.String(length=128)),
        ("start_idempotency_fingerprint", sa.String(length=64)),
        ("stop_idempotency_key", sa.String(length=128)),
        ("stop_idempotency_fingerprint", sa.String(length=64)),
    )
    for name, column_type in downtime_columns:
        op.add_column("sf_downtime_logs", sa.Column(name, column_type, nullable=True))
    _create_constraint_if_missing(
        "uq_sf_downtime_logs_creator_start_idempotency",
        "sf_downtime_logs",
        "unique",
        "created_by_user_id", "start_idempotency_key",
    )
    _create_constraint_if_missing(
        "ck_sf_downtime_logs_start_idempotency_pair",
        "sf_downtime_logs",
        "check",
        "(start_idempotency_key IS NULL AND start_idempotency_fingerprint IS NULL) OR "
        "(start_idempotency_key IS NOT NULL AND start_idempotency_fingerprint IS NOT NULL)",
    )
    _create_constraint_if_missing(
        "ck_sf_downtime_logs_stop_idempotency_pair",
        "sf_downtime_logs",
        "check",
        "(stop_idempotency_key IS NULL AND stop_idempotency_fingerprint IS NULL) OR "
        "(stop_idempotency_key IS NOT NULL AND stop_idempotency_fingerprint IS NOT NULL)",
    )


def downgrade() -> None:
    _drop_constraint_if_present("ck_sf_downtime_logs_stop_idempotency_pair", "sf_downtime_logs", "check")
    _drop_constraint_if_present("ck_sf_downtime_logs_start_idempotency_pair", "sf_downtime_logs", "check")
    _drop_constraint_if_present("uq_sf_downtime_logs_creator_start_idempotency", "sf_downtime_logs", "unique")
    op.drop_column("sf_downtime_logs", "stop_idempotency_fingerprint")
    op.drop_column("sf_downtime_logs", "stop_idempotency_key")
    op.drop_column("sf_downtime_logs", "start_idempotency_fingerprint")
    op.drop_column("sf_downtime_logs", "start_idempotency_key")
    _drop_constraint_if_present("ck_sf_activity_logs_idempotency_pair", "sf_activity_logs", "check")
    _drop_constraint_if_present("uq_sf_activity_logs_actor_idempotency", "sf_activity_logs", "unique")
    op.drop_column("sf_activity_logs", "idempotency_fingerprint")
    op.drop_column("sf_activity_logs", "idempotency_key")
