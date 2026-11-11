"""Shopify connector: one mapping per platform order (idempotent imports)."""

from alembic import op
import sqlalchemy as sa

revision = "20261111_0033"
down_revision = "20261111_0032"
branch_labels = None
depends_on = None


NAME = "uq_ecommerce_order_mappings_platform_order"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if any(c.get("name") == NAME for c in inspector.get_unique_constraints("ecommerce_order_mappings")):
        return  # fresh databases get it from the model-based baseline
    duplicates = op.get_bind().execute(sa.text(
        "SELECT source_platform, external_order_id, count(*) FROM ecommerce_order_mappings "
        "GROUP BY source_platform, external_order_id HAVING count(*) > 1 LIMIT 5"
    )).all()
    if duplicates:
        raise RuntimeError(
            f"ecommerce_order_mappings has duplicate platform orders {duplicates}; "
            "remove the extra rows (they came from the former placeholder sync) and rerun."
        )
    op.create_unique_constraint(
        NAME, "ecommerce_order_mappings", ["source_platform", "external_order_id"])


def downgrade() -> None:
    op.drop_constraint(NAME, "ecommerce_order_mappings", type_="unique")
