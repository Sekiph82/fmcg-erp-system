"""production_costing

Adds cost-tracking columns to the production module:

  production_orders:
    - total_material_cost   – actual raw-material cost (Σ consumed_qty × standard_cost)
    - total_labor_cost      – computed from LaborLog hours × work-center labor rate
    - total_machine_cost    – computed from work-order duration × machine cost/hr
    - total_energy_cost     – pulled from utility_transactions linked to the order
    - total_cost            – sum of all above
    - cost_per_unit         – total_cost / actual_quantity
    - standard_cost_per_unit – from product.standard_cost at time of order release
    - cost_variance_pct     – (actual - standard) / standard × 100
    - costing_finalized_at  – timestamp when cost was last computed / locked

  work_centers:
    - labor_rate_per_hour   – KES/hr for operator labor on this work center
    - machine_cost_per_hour – KES/hr fixed + variable machine cost

Revision ID: c8d9e0f1a2b3
Revises:     b7c8d9e0f1a2
"""
from alembic import op
import sqlalchemy as sa

revision       = "c8d9e0f1a2b3"
down_revision  = "b7c8d9e0f1a2"
branch_labels  = None
depends_on     = None


def upgrade() -> None:
    # ── production_orders costing columns ────────────────────────────────────
    op.add_column("production_orders",
        sa.Column("total_material_cost",    sa.Numeric(18, 4), nullable=True))
    op.add_column("production_orders",
        sa.Column("total_labor_cost",       sa.Numeric(18, 4), nullable=True))
    op.add_column("production_orders",
        sa.Column("total_machine_cost",     sa.Numeric(18, 4), nullable=True))
    op.add_column("production_orders",
        sa.Column("total_energy_cost",      sa.Numeric(18, 4), nullable=True))
    op.add_column("production_orders",
        sa.Column("total_cost",             sa.Numeric(18, 4), nullable=True))
    op.add_column("production_orders",
        sa.Column("cost_per_unit",          sa.Numeric(18, 6), nullable=True))
    op.add_column("production_orders",
        sa.Column("standard_cost_per_unit", sa.Numeric(18, 6), nullable=True))
    op.add_column("production_orders",
        sa.Column("cost_variance_pct",      sa.Numeric(10, 4), nullable=True))
    op.add_column("production_orders",
        sa.Column("costing_finalized_at",   sa.DateTime(timezone=True), nullable=True))

    # ── work_centers rate columns ─────────────────────────────────────────────
    op.add_column("work_centers",
        sa.Column("labor_rate_per_hour",   sa.Numeric(14, 4), nullable=True))
    op.add_column("work_centers",
        sa.Column("machine_cost_per_hour", sa.Numeric(14, 4), nullable=True))


def downgrade() -> None:
    op.drop_column("production_orders", "costing_finalized_at")
    op.drop_column("production_orders", "cost_variance_pct")
    op.drop_column("production_orders", "standard_cost_per_unit")
    op.drop_column("production_orders", "cost_per_unit")
    op.drop_column("production_orders", "total_cost")
    op.drop_column("production_orders", "total_energy_cost")
    op.drop_column("production_orders", "total_machine_cost")
    op.drop_column("production_orders", "total_labor_cost")
    op.drop_column("production_orders", "total_material_cost")

    op.drop_column("work_centers", "machine_cost_per_hour")
    op.drop_column("work_centers", "labor_rate_per_hour")
