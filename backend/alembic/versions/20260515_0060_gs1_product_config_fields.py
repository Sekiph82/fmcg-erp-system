"""gs1 product config fields

Revision ID: 20260515_0060
Revises: 20260515_0050
Create Date: 2026-05-15 15:00:00.000000
"""
from __future__ import annotations

from alembic import context, op
import sqlalchemy as sa


revision = "20260515_0060"
down_revision = "20260515_0050"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    if context.is_offline_mode():
        return True
    return table_name in _inspector().get_table_names()


def _columns(table_name: str) -> set[str]:
    if context.is_offline_mode() or not _has_table(table_name):
        return set()
    return {column["name"] for column in _inspector().get_columns(table_name)}


def _add_column_once(table_name: str, column: sa.Column) -> None:
    if context.is_offline_mode() or (_has_table(table_name) and column.name not in _columns(table_name)):
        op.add_column(table_name, column)


def upgrade() -> None:
    # Fix runtime bug: endpoints reference these fields but they don't exist on the model
    _add_column_once(
        "product_gs1_configs",
        sa.Column("product_sku_code", sa.String(100), nullable=True),
    )
    _add_column_once(
        "product_gs1_configs",
        sa.Column("net_weight_g", sa.Numeric(12, 4), nullable=True),
    )
    _add_column_once(
        "product_gs1_configs",
        sa.Column("net_volume_ml", sa.Numeric(12, 4), nullable=True),
    )


def downgrade() -> None:
    if _has_table("product_gs1_configs"):
        cols = _columns("product_gs1_configs")
        for col in ("net_volume_ml", "net_weight_g", "product_sku_code"):
            if col in cols:
                op.drop_column("product_gs1_configs", col)
