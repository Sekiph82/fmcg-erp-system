"""Link a delivery attempt to its explicitly replayed successor."""

from alembic import op
import sqlalchemy as sa


revision = "20261030_0003"
down_revision = "20261030_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("webhook_delivery_attempts")}
    if "replay_of_id" not in columns:
        op.add_column(
            "webhook_delivery_attempts",
            sa.Column("replay_of_id", sa.UUID(), nullable=True),
        )

    foreign_keys = {
        key["name"] for key in sa.inspect(bind).get_foreign_keys("webhook_delivery_attempts")
    }
    if "fk_webhook_delivery_attempts_replay_of_id" not in foreign_keys:
        op.create_foreign_key(
            "fk_webhook_delivery_attempts_replay_of_id",
            "webhook_delivery_attempts",
            "webhook_delivery_attempts",
            ["replay_of_id"],
            ["id"],
            ondelete="SET NULL",
        )

    constraints = {
        constraint["name"]
        for constraint in sa.inspect(bind).get_unique_constraints("webhook_delivery_attempts")
    }
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("webhook_delivery_attempts")}
    if "uq_webhook_delivery_attempts_replay_of" not in constraints | indexes:
        op.create_unique_constraint(
            "uq_webhook_delivery_attempts_replay_of",
            "webhook_delivery_attempts",
            ["replay_of_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("webhook_delivery_attempts")
    }
    if "uq_webhook_delivery_attempts_replay_of" in constraints:
        op.drop_constraint(
            "uq_webhook_delivery_attempts_replay_of",
            "webhook_delivery_attempts",
            type_="unique",
        )
    foreign_keys = {
        key["name"] for key in sa.inspect(bind).get_foreign_keys("webhook_delivery_attempts")
    }
    if "fk_webhook_delivery_attempts_replay_of_id" in foreign_keys:
        op.drop_constraint(
            "fk_webhook_delivery_attempts_replay_of_id",
            "webhook_delivery_attempts",
            type_="foreignkey",
        )
    columns = {column["name"] for column in sa.inspect(bind).get_columns("webhook_delivery_attempts")}
    if "replay_of_id" in columns:
        op.drop_column("webhook_delivery_attempts", "replay_of_id")
