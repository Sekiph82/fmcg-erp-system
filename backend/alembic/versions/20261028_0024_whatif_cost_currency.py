"""persist scenario cost currency for truthful API and UI labels

Revision ID: 20261028_0024
Revises: 20261028_0023
Create Date: 2026-10-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision = "20261028_0024"
down_revision = "20261028_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("mps_whatif_scenarios")}
    checks = {constraint["name"] for constraint in inspector.get_check_constraints("mps_whatif_scenarios")}
    if "impact_cost_currency" not in columns:
        op.add_column("mps_whatif_scenarios", sa.Column("impact_cost_currency", sa.String(length=3), nullable=True))
    if "ck_mps_whatif_cost_currency_iso3" not in checks:
        op.create_check_constraint(
            "ck_mps_whatif_cost_currency_iso3",
            "mps_whatif_scenarios",
            "impact_cost_currency IS NULL OR (length(impact_cost_currency) = 3 AND impact_cost_currency = upper(impact_cost_currency))",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    checks = {constraint["name"] for constraint in inspector.get_check_constraints("mps_whatif_scenarios")}
    columns = {column["name"] for column in inspector.get_columns("mps_whatif_scenarios")}
    if "ck_mps_whatif_cost_currency_iso3" in checks:
        op.drop_constraint("ck_mps_whatif_cost_currency_iso3", "mps_whatif_scenarios", type_="check")
    if "impact_cost_currency" in columns:
        op.drop_column("mps_whatif_scenarios", "impact_cost_currency")
