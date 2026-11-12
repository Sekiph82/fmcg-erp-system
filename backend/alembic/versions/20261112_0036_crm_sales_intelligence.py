"""M36.S02 sales intelligence: score rules + history, stage history, forecast snapshots."""

from alembic import op

revision = "20261112_0036"
down_revision = "20261112_0035"
branch_labels = None
depends_on = None

TABLES = ("crm_score_rules", "crm_score_history", "crm_stage_history", "crm_forecast_snapshots")


def _tables():
    from app.models.crm import CRMForecastSnapshot, CRMScoreHistory, CRMScoreRule, CRMStageHistory

    return [CRMScoreRule.__table__, CRMScoreHistory.__table__, CRMStageHistory.__table__, CRMForecastSnapshot.__table__]


def upgrade() -> None:
    bind = op.get_bind()
    for table in _tables():  # fresh databases already have them from the model-based baseline
        table.create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(_tables()):
        table.drop(bind, checkfirst=True)
