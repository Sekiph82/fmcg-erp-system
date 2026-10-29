"""Persist event idempotency keys and request fingerprints."""

from alembic import op
import sqlalchemy as sa


revision = "20261030_0002"
down_revision = "20261030_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("webhook_event_logs")}
    if "idempotency_key" not in columns:
        op.add_column("webhook_event_logs", sa.Column("idempotency_key", sa.String(length=255), nullable=True))
    if "idempotency_fingerprint" not in columns:
        op.add_column(
            "webhook_event_logs",
            sa.Column("idempotency_fingerprint", sa.String(length=64), nullable=True),
        )

    unique_constraints = {
        constraint["name"] for constraint in sa.inspect(bind).get_unique_constraints("webhook_event_logs")
    }
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("webhook_event_logs")}
    if "uq_webhook_event_idempotency" not in unique_constraints | indexes:
        op.create_unique_constraint(
            "uq_webhook_event_idempotency",
            "webhook_event_logs",
            ["event_code", "idempotency_key"],
        )

    checks = {constraint["name"] for constraint in sa.inspect(bind).get_check_constraints("webhook_event_logs")}
    if "ck_webhook_event_idempotency_pair" not in checks:
        op.create_check_constraint(
            "ck_webhook_event_idempotency_pair",
            "webhook_event_logs",
            "(idempotency_key IS NULL AND idempotency_fingerprint IS NULL) OR "
            "(idempotency_key IS NOT NULL AND idempotency_fingerprint IS NOT NULL)",
        )


def downgrade() -> None:
    op.drop_constraint("ck_webhook_event_idempotency_pair", "webhook_event_logs", type_="check")
    op.drop_constraint("uq_webhook_event_idempotency", "webhook_event_logs", type_="unique")
    op.drop_column("webhook_event_logs", "idempotency_fingerprint")
    op.drop_column("webhook_event_logs", "idempotency_key")
