"""Add attributable append-only production transition history.

Revision ID: 20261104_0003
Revises: 20261104_0002
Create Date: 2026-11-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261104_0003"
down_revision = "20261104_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "production_transition_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_seq", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_entity_type", sa.String(length=40), nullable=False),
        sa.Column("parent_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=True),
        sa.Column("to_status", sa.String(length=30), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_label", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "entity_type IN ('PRODUCTION_ORDER', 'WORK_ORDER', 'EXEC_PRODUCTION_ORDER', 'EXEC_WORK_ORDER')",
            name="ck_production_transition_entity_type",
        ),
        sa.CheckConstraint(
            "parent_entity_type IN ('PRODUCTION_ORDER', 'EXEC_PRODUCTION_ORDER')",
            name="ck_production_transition_parent_type",
        ),
        sa.CheckConstraint("length(trim(action)) > 0", name="ck_production_transition_action_nonempty"),
        sa.CheckConstraint(
            "(actor_id IS NOT NULL) <> (actor_session_id IS NOT NULL)",
            name="ck_production_transition_single_actor",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name="fk_production_transition_actor_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_session_id"],
            ["sf_sessions.id"],
            name="fk_production_transition_actor_session",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_production_transition_events"),
        sa.UniqueConstraint("event_seq", name="uq_production_transition_events_event_seq"),
    )
    op.create_index(
        "ix_production_transition_entity_seq",
        "production_transition_events",
        ["entity_type", "entity_id", "event_seq"],
    )
    op.create_index(
        "ix_production_transition_parent_seq",
        "production_transition_events",
        ["parent_entity_type", "parent_entity_id", "event_seq"],
    )
    op.create_index(
        "ix_production_transition_actor_created",
        "production_transition_events",
        ["actor_id", "created_at"],
    )
    op.create_index(
        "ix_production_transition_session_created",
        "production_transition_events",
        ["actor_session_id", "created_at"],
    )
    op.execute(
        """
        CREATE FUNCTION public.prevent_production_transition_event_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Production transition history is append-only'
                USING ERRCODE = '23514',
                      CONSTRAINT = 'ck_production_transition_append_only';
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_production_transition_events_append_only
            BEFORE UPDATE OR DELETE ON public.production_transition_events
            FOR EACH ROW EXECUTE FUNCTION public.prevent_production_transition_event_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_production_transition_events_no_truncate
            BEFORE TRUNCATE ON public.production_transition_events
            FOR EACH STATEMENT EXECUTE FUNCTION public.prevent_production_transition_event_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_production_transition_events_no_truncate ON public.production_transition_events"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_production_transition_events_append_only ON public.production_transition_events"
    )
    op.execute("DROP FUNCTION IF EXISTS public.prevent_production_transition_event_mutation()")
    op.drop_index("ix_production_transition_actor_created", table_name="production_transition_events")
    op.drop_index("ix_production_transition_session_created", table_name="production_transition_events")
    op.drop_index("ix_production_transition_parent_seq", table_name="production_transition_events")
    op.drop_index("ix_production_transition_entity_seq", table_name="production_transition_events")
    op.drop_table("production_transition_events")
