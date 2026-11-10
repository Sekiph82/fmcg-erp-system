"""Reconcile tables left behind by stamp-based bootstraps.

``scripts/dev_migrate.py`` used to bring an untracked database forward with
``create_all`` + ``alembic stamp head``. That skips migrations, and ``create_all`` does
not touch existing tables, so such databases kept older shapes of a few tables
(missing columns, constraints and the RFQ quote table). This revision rebuilds each
listed table from the current model only when it is missing, or drifted and empty;
a drifted table that holds rows stops the upgrade with an explicit error instead of
guessing. On a correctly migrated database it is a no-op.
"""

from alembic import op
import sqlalchemy as sa

revision = "20261110_0030"
down_revision = "20261110_0029"
branch_labels = None
depends_on = None

# Order matters: dependencies first.
TABLES = (
    "rfq_response_line_quotes",
    "rfq_award_allocations",
    "production_transition_events",
    "sf_downtime_logs",
    "machine_skill_requirements",
)

_APPEND_ONLY_SQL = (
    """
    CREATE OR REPLACE FUNCTION public.prevent_production_transition_event_mutation() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'Production transition history is append-only'
            USING ERRCODE = '23514',
                  CONSTRAINT = 'ck_production_transition_append_only';
    END;
    $$;
    """,
    """
    CREATE TRIGGER trg_production_transition_events_append_only
        BEFORE UPDATE OR DELETE ON public.production_transition_events
        FOR EACH ROW EXECUTE FUNCTION public.prevent_production_transition_event_mutation()
    """,
    """
    CREATE TRIGGER trg_production_transition_events_no_truncate
        BEFORE TRUNCATE ON public.production_transition_events
        FOR EACH STATEMENT EXECUTE FUNCTION public.prevent_production_transition_event_mutation()
    """,
)


def _columns(bind, table):
    rows = bind.execute(sa.text(
        "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = :t"
    ), {"t": table}).scalars().all()
    return set(rows)


def upgrade() -> None:
    from app.db.base import Base
    import app.models  # noqa: F401

    bind = op.get_bind()
    for name in TABLES:
        model_table = Base.metadata.tables[name]
        existing = _columns(bind, name)
        if existing:
            missing = {c.name for c in model_table.columns} - existing
            if not missing:
                continue
            if bind.execute(sa.text(f'SELECT EXISTS (SELECT 1 FROM "{name}")')).scalar():
                raise RuntimeError(
                    f"{name} is missing columns {sorted(missing)} and holds rows; reconcile it manually "
                    "(it was bootstrapped by create_all + stamp instead of migrations)."
                )
            op.drop_table(name)
        Base.metadata.create_all(bind=bind, tables=[model_table], checkfirst=True)
        if name == "production_transition_events":
            for statement in _APPEND_ONLY_SQL:
                op.execute(statement)


def downgrade() -> None:
    # Rebuilt tables match the current models; there is no earlier shape to restore.
    pass
