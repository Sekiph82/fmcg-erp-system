"""M38 field review guards: one POD per trip stop; M-Pesa code unique only among live collections."""

import sqlalchemy as sa
from alembic import op

revision = "20261119_0047"
down_revision = "20261119_0046"
branch_labels = None
depends_on = None


def _indexes(table):
    return {i["name"] for i in sa.inspect(op.get_bind()).get_indexes(table)}


def upgrade() -> None:
    uqs = {c["name"] for c in sa.inspect(op.get_bind()).get_unique_constraints("cash_collections")}
    if "cash_collections_mpesa_code_key" in uqs:
        op.drop_constraint("cash_collections_mpesa_code_key", "cash_collections", type_="unique")
    if "uq_cash_collections_mpesa_code_live" not in _indexes("cash_collections"):
        op.create_index("uq_cash_collections_mpesa_code_live", "cash_collections", ["mpesa_code"], unique=True,
                        postgresql_where=sa.text("mpesa_code IS NOT NULL AND status <> 'CANCELLED'"))
    if "uq_pod_trip_order" not in _indexes("proof_of_deliveries"):
        op.create_index("uq_pod_trip_order", "proof_of_deliveries", ["trip_order_id"], unique=True,
                        postgresql_where=sa.text("trip_order_id IS NOT NULL"))


def downgrade() -> None:
    if "uq_pod_trip_order" in _indexes("proof_of_deliveries"):
        op.drop_index("uq_pod_trip_order", table_name="proof_of_deliveries")
    if "uq_cash_collections_mpesa_code_live" in _indexes("cash_collections"):
        op.drop_index("uq_cash_collections_mpesa_code_live", table_name="cash_collections")
        op.create_unique_constraint("cash_collections_mpesa_code_key", "cash_collections", ["mpesa_code"])
