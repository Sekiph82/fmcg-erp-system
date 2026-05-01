"""chatter_activity_timeline

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
Create Date: 2026-05-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b0c1d2e3f4a5'
down_revision = 'a9b0c1d2e3f4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'chatter_activities',
        sa.Column('activity_id', sa.String(36), primary_key=True),
        sa.Column('reference_type', sa.String(30), nullable=False),
        sa.Column('reference_id', sa.String(36), nullable=False),
        sa.Column('activity_type', sa.String(30), default='comment'),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('message', sa.Text()),
        sa.Column('created_by', sa.String(100), default='system'),
        sa.Column('visibility', sa.String(20), default='global'),
        sa.Column('is_pinned', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )
    op.create_index('ix_chatter_activities_ref', 'chatter_activities',
                    ['reference_type', 'reference_id'])
    op.create_index('ix_chatter_activities_created', 'chatter_activities', ['created_at'])

    op.create_table(
        'chatter_comments',
        sa.Column('comment_id', sa.String(36), primary_key=True),
        sa.Column('activity_id', sa.String(36),
                  sa.ForeignKey('chatter_activities.activity_id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('user_id', sa.String(36)),
        sa.Column('user_name', sa.String(100)),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('edited_at', sa.DateTime()),
        sa.Column('deleted_flag', sa.Boolean(), default=False),
    )
    op.create_index('ix_chatter_comments_activity', 'chatter_comments', ['activity_id'])

    op.create_table(
        'chatter_attachments',
        sa.Column('attachment_id', sa.String(36), primary_key=True),
        sa.Column('activity_id', sa.String(36),
                  sa.ForeignKey('chatter_activities.activity_id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('file_name', sa.String(300), nullable=False),
        sa.Column('file_path', sa.String(500)),
        sa.Column('file_size', sa.String(20)),
        sa.Column('content_type', sa.String(100)),
        sa.Column('uploaded_by', sa.String(100)),
        sa.Column('uploaded_at', sa.DateTime()),
    )
    op.create_index('ix_chatter_attachments_activity', 'chatter_attachments', ['activity_id'])

    op.create_table(
        'chatter_mentions',
        sa.Column('mention_id', sa.String(36), primary_key=True),
        sa.Column('activity_id', sa.String(36),
                  sa.ForeignKey('chatter_activities.activity_id', ondelete='CASCADE')),
        sa.Column('comment_id', sa.String(36),
                  sa.ForeignKey('chatter_comments.comment_id', ondelete='CASCADE')),
        sa.Column('mentioned_user', sa.String(100), nullable=False),
        sa.Column('notified_flag', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_chatter_mentions_user', 'chatter_mentions', ['mentioned_user'])

    op.create_table(
        'chatter_ai_recommendations',
        sa.Column('rec_id', sa.String(36), primary_key=True),
        sa.Column('agent_type', sa.String(30), nullable=False),
        sa.Column('reference_type', sa.String(50)),
        sa.Column('reference_id', sa.String(36)),
        sa.Column('title', sa.String(300)),
        sa.Column('body', sa.Text()),
        sa.Column('score', sa.Float()),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('rec_metadata', sa.JSON()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )


def downgrade():
    op.drop_table('chatter_ai_recommendations')
    op.drop_index('ix_chatter_mentions_user', 'chatter_mentions')
    op.drop_table('chatter_mentions')
    op.drop_index('ix_chatter_attachments_activity', 'chatter_attachments')
    op.drop_table('chatter_attachments')
    op.drop_index('ix_chatter_comments_activity', 'chatter_comments')
    op.drop_table('chatter_comments')
    op.drop_index('ix_chatter_activities_created', 'chatter_activities')
    op.drop_index('ix_chatter_activities_ref', 'chatter_activities')
    op.drop_table('chatter_activities')
