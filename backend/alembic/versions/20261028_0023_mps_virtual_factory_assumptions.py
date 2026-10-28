"""add MPS minimum-run and CIP transition inputs

Revision ID: 20261028_0023
Revises: 20261028_0022
Create Date: 2026-10-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision = "20261028_0023"
down_revision = "20261028_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    product_columns = {column["name"] for column in inspector.get_columns("products")}
    product_checks = {constraint["name"] for constraint in inspector.get_check_constraints("products")}
    if "minimum_run_qty" not in product_columns:
        op.add_column("products", sa.Column("minimum_run_qty", sa.Numeric(12, 3), nullable=True))
    if "ck_products_minimum_run_qty_positive" not in product_checks:
        op.create_check_constraint(
            "ck_products_minimum_run_qty_positive",
            "products",
            "minimum_run_qty IS NULL OR minimum_run_qty > 0",
        )
    if "standard_cost_currency" not in product_columns:
        op.add_column("products", sa.Column("standard_cost_currency", sa.String(length=3), nullable=True))
    if "ck_products_standard_cost_currency_iso3" not in product_checks:
        op.create_check_constraint(
            "ck_products_standard_cost_currency_iso3",
            "products",
            "standard_cost_currency IS NULL OR (length(standard_cost_currency) = 3 AND standard_cost_currency = upper(standard_cost_currency))",
        )

    transition_columns = {column["name"] for column in inspector.get_columns("changeover_matrix")}
    transition_checks = {constraint["name"] for constraint in inspector.get_check_constraints("changeover_matrix")}
    if "cip_minutes" not in transition_columns:
        op.add_column("changeover_matrix", sa.Column("cip_minutes", sa.Integer(), nullable=True))
    if "ck_changeover_cip_minutes_nonnegative" not in transition_checks:
        op.create_check_constraint(
            "ck_changeover_cip_minutes_nonnegative",
            "changeover_matrix",
            "cip_minutes IS NULL OR cip_minutes >= 0",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    transition_columns = {column["name"] for column in inspector.get_columns("changeover_matrix")}
    transition_checks = {constraint["name"] for constraint in inspector.get_check_constraints("changeover_matrix")}
    if "ck_changeover_cip_minutes_nonnegative" in transition_checks:
        op.drop_constraint("ck_changeover_cip_minutes_nonnegative", "changeover_matrix", type_="check")
    if "cip_minutes" in transition_columns:
        op.drop_column("changeover_matrix", "cip_minutes")

    inspector = sa_inspect(bind)
    product_columns = {column["name"] for column in inspector.get_columns("products")}
    product_checks = {constraint["name"] for constraint in inspector.get_check_constraints("products")}
    if "ck_products_standard_cost_currency_iso3" in product_checks:
        op.drop_constraint("ck_products_standard_cost_currency_iso3", "products", type_="check")
    if "standard_cost_currency" in product_columns:
        op.drop_column("products", "standard_cost_currency")
    if "ck_products_minimum_run_qty_positive" in product_checks:
        op.drop_constraint("ck_products_minimum_run_qty_positive", "products", type_="check")
    if "minimum_run_qty" in product_columns:
        op.drop_column("products", "minimum_run_qty")
