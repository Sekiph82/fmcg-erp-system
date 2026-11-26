"""M36.S02.T005 segment e-mail campaigns."""

from alembic import op

revision = "20261119_0043"
down_revision = "20261119_0042"
branch_labels = None
depends_on = None


# Columns added by later migrations (0073 track_engagement, 0074 design/A-B/approval). They are left out here so a
# database downgraded below 0043 can be upgraded again: 0074's FKs point at tables that do not exist yet at 0043.
LATER = {"track_engagement", "design_id", "ab_split_pct", "variant_b_subject", "variant_b_body", "variant_b_design_id",
         "send_time_optimize", "approval_status", "approval_requested_by", "approved_by", "approved_at"}


def _table():
    import sqlalchemy as sa

    from app.models.crm import CRMEmailCampaign

    src = CRMEmailCampaign.__table__
    return sa.Table(src.name, sa.MetaData(), *[c._copy() for c in src.columns if c.name not in LATER])


def upgrade() -> None:
    _table().create(op.get_bind(), checkfirst=True)  # fresh databases get it from the model-based baseline


def downgrade() -> None:
    _table().drop(op.get_bind(), checkfirst=True)
