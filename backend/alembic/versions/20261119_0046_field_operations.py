"""M38 field operations: collections, outlet audits, driver/visit/POD links, supplier document scan status."""

import sqlalchemy as sa
from alembic import op

revision = "20261119_0046"
down_revision = "20261119_0045"
branch_labels = None
depends_on = None

# fresh databases already get these from the model-based baseline, so every step checks first
COLUMNS = (
    ("visit_logs", lambda: sa.Column("client_ref", sa.String(64), nullable=True)),
    ("visit_logs", lambda: sa.Column("photo_key", sa.String(64), nullable=True)),
    ("delivery_trips", lambda: sa.Column("driver_user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)),
    ("proof_of_deliveries", lambda: sa.Column("signature_key", sa.String(64), nullable=True)),
    ("sp_documents", lambda: sa.Column("scan_status", sa.String(20), nullable=False, server_default="NOT_SCANNED")),
)


def _insp():
    return sa.inspect(op.get_bind())


def _cols(table):
    return {c["name"] for c in _insp().get_columns(table)}


def _visit_uniques():
    return {c["name"] for c in _insp().get_unique_constraints("visit_logs")}


def upgrade() -> None:
    from app.models.field_ops import CashCollection, FieldAudit

    for table, make in COLUMNS:
        col = make()
        if col.name not in _cols(table):
            op.add_column(table, col)
    if not _visit_uniques() & {"uq_visit_logs_client_ref", "visit_logs_client_ref_key"}:
        op.create_unique_constraint("uq_visit_logs_client_ref", "visit_logs", ["client_ref"])
    if "ix_delivery_trips_driver_user_id" not in {i["name"] for i in _insp().get_indexes("delivery_trips")}:
        op.create_index("ix_delivery_trips_driver_user_id", "delivery_trips", ["driver_user_id"])
    for table in (CashCollection.__table__, FieldAudit.__table__):
        table.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    from app.models.field_ops import CashCollection, FieldAudit

    for table in (FieldAudit.__table__, CashCollection.__table__):
        table.drop(op.get_bind(), checkfirst=True)
    for name in _visit_uniques() & {"uq_visit_logs_client_ref", "visit_logs_client_ref_key"}:
        op.drop_constraint(name, "visit_logs", type_="unique")
    if "ix_delivery_trips_driver_user_id" in {i["name"] for i in _insp().get_indexes("delivery_trips")}:
        op.drop_index("ix_delivery_trips_driver_user_id", table_name="delivery_trips")
    for table, make in reversed(COLUMNS):
        name = make().name
        if name in _cols(table):
            op.drop_column(table, name)
