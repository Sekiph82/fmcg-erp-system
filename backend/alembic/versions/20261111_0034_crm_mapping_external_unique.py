"""One ERP customer per external customer id (Shopify buyers link to native customers)."""

from alembic import op
import sqlalchemy as sa

revision = "20261111_0034"
down_revision = "20261111_0033"
branch_labels = None
depends_on = None

NAME = "uq_crm_customer_mappings_provider_external"
TABLE = "crm_customer_mappings"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if any(c.get("name") == NAME for c in inspector.get_unique_constraints(TABLE)):
        return  # fresh databases get it from the model-based baseline
    duplicates = op.get_bind().execute(sa.text(
        f"SELECT crm_provider, external_crm_id, count(*) FROM {TABLE} "
        "GROUP BY crm_provider, external_crm_id HAVING count(*) > 1 LIMIT 5"
    )).all()
    if duplicates:
        raise RuntimeError(f"{TABLE} links one external customer to several ERP customers {duplicates}; "
                           "keep one row per external id and rerun.")
    op.create_unique_constraint(NAME, TABLE, ["crm_provider", "external_crm_id"])


def downgrade() -> None:
    op.drop_constraint(NAME, TABLE, type_="unique")
