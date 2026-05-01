"""kanban_boards

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-05-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'e7f8a9b0c1d2'
down_revision = 'd6e7f8a9b0c1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'kanban_boards',
        sa.Column('board_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('board_code', sa.String(50), nullable=False),
        sa.Column('board_name', sa.String(200), nullable=False),
        sa.Column('module_type', sa.Enum(
            'crm', 'recruitment', 'tasks', 'approvals', 'custom', 'operations', 'projects',
            name='boardmoduletype'
        ), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.String(100), nullable=True),
        sa.Column('owner_name', sa.String(200), nullable=True),
        sa.Column('visibility', sa.Enum('private', 'team', 'global', name='boardvisibility'), nullable=False),
        sa.Column('active_flag', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('board_id'),
        sa.UniqueConstraint('board_code'),
    )

    op.create_table(
        'kanban_columns',
        sa.Column('column_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('board_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('column_name', sa.String(100), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('stage_type', sa.Enum('normal', 'final_success', 'final_failure', name='columnstagetype'), nullable=False),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('wip_limit', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['board_id'], ['kanban_boards.board_id']),
        sa.PrimaryKeyConstraint('column_id'),
        sa.UniqueConstraint('board_id', 'sequence', name='uq_kanban_col_board_seq'),
    )

    op.create_table(
        'kanban_cards',
        sa.Column('card_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('board_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('column_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('card_no', sa.String(30), nullable=True),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('reference_type', sa.String(100), nullable=True),
        sa.Column('reference_id', sa.String(200), nullable=True),
        sa.Column('assigned_user_id', sa.String(100), nullable=True),
        sa.Column('assigned_user_name', sa.String(200), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('priority', sa.Enum('low', 'normal', 'high', 'critical', name='cardpriority'), nullable=False),
        sa.Column('status', sa.Enum('active', 'blocked', 'done', 'archived', name='cardstatus'), nullable=False),
        sa.Column('tags', sa.String(500), nullable=True),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['board_id'], ['kanban_boards.board_id']),
        sa.ForeignKeyConstraint(['column_id'], ['kanban_columns.column_id']),
        sa.PrimaryKeyConstraint('card_id'),
    )
    op.create_index('ix_kanban_cards_board_id', 'kanban_cards', ['board_id'])
    op.create_index('ix_kanban_cards_column_id', 'kanban_cards', ['column_id'])

    op.create_table(
        'kanban_activities',
        sa.Column('activity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('card_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('board_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_type', sa.Enum(
            'created', 'moved', 'assigned', 'priority_changed', 'commented',
            'due_date_set', 'status_changed', 'archived',
            name='activityeventtype'
        ), nullable=False),
        sa.Column('actor_id', sa.String(100), nullable=True),
        sa.Column('actor_name', sa.String(200), nullable=True),
        sa.Column('from_value', sa.String(300), nullable=True),
        sa.Column('to_value', sa.String(300), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['card_id'], ['kanban_cards.card_id']),
        sa.PrimaryKeyConstraint('activity_id'),
    )

    op.create_table(
        'kanban_comments',
        sa.Column('comment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('card_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('author_id', sa.String(100), nullable=True),
        sa.Column('author_name', sa.String(200), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['card_id'], ['kanban_cards.card_id']),
        sa.PrimaryKeyConstraint('comment_id'),
    )

    op.create_table(
        'kb_ai_recommendations',
        sa.Column('rec_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_type', sa.Enum('workflow_optimizer', 'task_prioritizer', name='kbaiagentype'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'acknowledged', 'actioned', 'dismissed', name='kbairecstatus'), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('board_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('column_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('card_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('actioned_by', sa.String(200), nullable=True),
        sa.Column('actioned_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('rec_id'),
    )


def downgrade() -> None:
    op.drop_table('kb_ai_recommendations')
    op.drop_table('kanban_comments')
    op.drop_table('kanban_activities')
    op.drop_index('ix_kanban_cards_column_id', 'kanban_cards')
    op.drop_index('ix_kanban_cards_board_id', 'kanban_cards')
    op.drop_table('kanban_cards')
    op.drop_table('kanban_columns')
    op.drop_table('kanban_boards')
    op.execute("DROP TYPE IF EXISTS boardmoduletype")
    op.execute("DROP TYPE IF EXISTS boardvisibility")
    op.execute("DROP TYPE IF EXISTS columnstagetype")
    op.execute("DROP TYPE IF EXISTS cardpriority")
    op.execute("DROP TYPE IF EXISTS cardstatus")
    op.execute("DROP TYPE IF EXISTS activityeventtype")
    op.execute("DROP TYPE IF EXISTS kbaiagentype")
    op.execute("DROP TYPE IF EXISTS kbairecstatus")
