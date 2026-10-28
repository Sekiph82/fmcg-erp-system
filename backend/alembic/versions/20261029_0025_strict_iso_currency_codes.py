"""require alphabetic ISO currency codes for MPS costs

Revision ID: 20261029_0025
Revises: 20261028_0024
Create Date: 2026-10-29
"""
import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision = "20261029_0025"
down_revision = "20261028_0024"
branch_labels = None
depends_on = None


logger = logging.getLogger("alembic.runtime.migration")


def _replace_strict_currency_check(table: str, name: str, column: str) -> None:
    bind = op.get_bind()
    checks = {constraint["name"] for constraint in sa_inspect(bind).get_check_constraints(table)}
    if name in checks:
        op.drop_constraint(name, table, type_="check")
    op.execute(
        f'ALTER TABLE "{table}" ADD CONSTRAINT "{name}" '
        f'CHECK ("{column}" IS NULL OR "{column}" ~ \'^[A-Z]{{3}}$\') NOT VALID'
    )
    malformed_exists = bind.execute(sa.text(
        f'SELECT EXISTS (SELECT 1 FROM "{table}" '
        f'WHERE "{column}" IS NOT NULL AND "{column}" !~ \'^[A-Z]{{3}}$\')'
    )).scalar_one()
    if malformed_exists:
        # Keep existing owner rows untouched. NOT VALID preserves them while
        # PostgreSQL enforces the check for every new or updated row. The MPS
        # cost path treats malformed historical codes as unknown.
        logger.warning(
            "Preserved existing rows with malformed %s.%s; strict currency check remains NOT VALID",
            table, column,
        )
    else:
        op.execute(f'ALTER TABLE "{table}" VALIDATE CONSTRAINT "{name}"')


def _replace_legacy_check(table: str, name: str, expression: str) -> None:
    checks = {constraint["name"] for constraint in sa_inspect(op.get_bind()).get_check_constraints(table)}
    if name in checks:
        op.drop_constraint(name, table, type_="check")
    op.create_check_constraint(name, table, expression)


def upgrade() -> None:
    _replace_strict_currency_check(
        "products", "ck_products_standard_cost_currency_iso3", "standard_cost_currency",
    )
    _replace_strict_currency_check(
        "mps_whatif_scenarios", "ck_mps_whatif_cost_currency_iso3", "impact_cost_currency",
    )


def downgrade() -> None:
    _replace_legacy_check(
        "mps_whatif_scenarios", "ck_mps_whatif_cost_currency_iso3",
        "impact_cost_currency IS NULL OR (length(impact_cost_currency) = 3 AND impact_cost_currency = upper(impact_cost_currency))",
    )
    _replace_legacy_check(
        "products", "ck_products_standard_cost_currency_iso3",
        "standard_cost_currency IS NULL OR (length(standard_cost_currency) = 3 AND standard_cost_currency = upper(standard_cost_currency))",
    )
