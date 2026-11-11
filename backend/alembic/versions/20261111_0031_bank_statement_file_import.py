"""Bank statement file import: widen import_source for MT940 / CAMT053 sources."""

from alembic import op
import sqlalchemy as sa

revision = "20261111_0031"
down_revision = "20261110_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("br_statements", "import_source", type_=sa.String(20), existing_nullable=False)


def downgrade() -> None:
    op.execute("UPDATE br_statements SET import_source = 'API' WHERE import_source IN ('MT940', 'CAMT053')")
    op.alter_column("br_statements", "import_source", type_=sa.String(6), existing_nullable=False)
