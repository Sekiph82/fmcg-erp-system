"""require alphabetic ISO currency codes for MPS costs

Revision ID: 20261029_0025
Revises: 20261028_0024
Create Date: 2026-10-29
"""
from alembic import op
from sqlalchemy import inspect as sa_inspect


revision = "20261029_0025"
down_revision = "20261028_0024"
branch_labels = None
depends_on = None


def _replace_check(table: str, name: str, expression: str) -> None:
    checks = {constraint["name"] for constraint in sa_inspect(op.get_bind()).get_check_constraints(table)}
    if name in checks:
        op.drop_constraint(name, table, type_="check")
    op.create_check_constraint(name, table, expression)


def upgrade() -> None:
    _replace_check(
        "products", "ck_products_standard_cost_currency_iso3",
        "standard_cost_currency IS NULL OR standard_cost_currency ~ '^[A-Z]{3}$'",
    )
    _replace_check(
        "mps_whatif_scenarios", "ck_mps_whatif_cost_currency_iso3",
        "impact_cost_currency IS NULL OR impact_cost_currency ~ '^[A-Z]{3}$'",
    )


def downgrade() -> None:
    _replace_check(
        "mps_whatif_scenarios", "ck_mps_whatif_cost_currency_iso3",
        "impact_cost_currency IS NULL OR (length(impact_cost_currency) = 3 AND impact_cost_currency = upper(impact_cost_currency))",
    )
    _replace_check(
        "products", "ck_products_standard_cost_currency_iso3",
        "standard_cost_currency IS NULL OR (length(standard_cost_currency) = 3 AND standard_cost_currency = upper(standard_cost_currency))",
    )
