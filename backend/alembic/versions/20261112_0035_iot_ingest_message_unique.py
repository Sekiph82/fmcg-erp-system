"""MQTT bridge: an accepted device message is stored once (redelivery to two workers)."""

from alembic import op
import sqlalchemy as sa

revision = "20261112_0035"
down_revision = "20261111_0034"
branch_labels = None
depends_on = None

NAME = "uq_iot_ingest_messages_accepted"
TABLE = "iot_ingest_messages"
WHERE = "status = 'ACCEPTED' AND message_id IS NOT NULL"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if any(i.get("name") == NAME for i in inspector.get_indexes(TABLE)):
        return  # fresh databases get it from the model-based baseline
    duplicates = op.get_bind().execute(sa.text(
        f"SELECT source, message_id, count(*) FROM {TABLE} WHERE {WHERE} "
        "GROUP BY source, message_id HAVING count(*) > 1 LIMIT 5")).all()
    if duplicates:
        raise RuntimeError(f"{TABLE} has repeated accepted messages {duplicates}; mark extras DUPLICATE and rerun.")
    op.create_index(NAME, TABLE, ["source", "message_id"], unique=True, postgresql_where=sa.text(WHERE))


def downgrade() -> None:
    op.drop_index(NAME, table_name=TABLE)
